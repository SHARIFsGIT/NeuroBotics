"""Calculate reproducible mission metrics, PNG figures and LaTeX tables.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

from eira_evaluation.records import finite_number

JSON_COLUMNS = ('action_results', 'perception_latencies_ms', 'grasp_outcomes', 'recovery_events')


def percentage(successes: int, total: int) -> dict[str, Any]:
    """Compute a binomial rate with a Wilson 95% confidence interval.

    Args:
        successes: Observed successes.
        total: Eligible observations, excluding unobserved physical outcomes.
    Returns:
        Counts, percentage, and Wilson interval; null estimates without observations.
    Raises:
        ValueError: If the counts are inconsistent.
    """
    if not 0 <= successes <= total:
        raise ValueError('invalid binomial counts')
    if total == 0:
        return {'successes': 0, 'n': 0, 'percent': None, 'ci95_percent': [None, None]}
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z*z/total
    centre = (p + z*z/(2*total)) / denominator
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return {'successes': successes, 'n': total, 'percent': 100*p,
            'ci95_percent': [100*max(0.0, min(p, centre-half)),
                             100*min(1.0, max(p, centre+half))]}


def distribution(values: list[float]) -> dict[str, Any]:
    """Summarize observed values without substituting zeros for missing data.

    Args:
        values: Finite metric samples.
    Returns:
        Sample count, mean, population standard deviation, median and p95.
    """
    data = sorted(value for value in values if math.isfinite(value) and value >= 0)
    if not data:
        return {'n': 0, 'mean': None, 'std': None, 'median': None, 'p95': None}
    index = (len(data)-1)*0.95
    lower, upper = math.floor(index), math.ceil(index)
    p95 = data[lower] + (data[upper]-data[lower])*(index-lower)
    return {'n': len(data), 'mean': mean(data), 'std': pstdev(data),
            'median': median(data), 'p95': p95}


def read_records(path: Path) -> list[dict[str, Any]]:
    """Read the published CSV schema or detailed JSON archive.

    Args:
        path: CSV/JSON input filename.
    Returns:
        Detailed or normalized mission dictionaries.
    Raises:
        OSError: If input cannot be read.
        ValueError: If required columns or values are malformed.
    """
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not isinstance(data.get('missions'), list):
            raise ValueError('JSON input requires a missions array')
        return data['missions']
    with path.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        if not {'mission_id', 'success', 'terminal_state', 'action_results'} <= set(
                reader.fieldnames or []):
            raise ValueError('CSV is missing mission evaluation headers')
        records = []
        for row in reader:
            for key in JSON_COLUMNS:
                try:
                    row[key] = json.loads(row.get(key) or '[]')
                except json.JSONDecodeError as exc:
                    raise ValueError(f'invalid JSON column {key}') from exc
                if not isinstance(row[key], list):
                    raise ValueError(f'{key} must contain a JSON array')
            for key in ('success', 'evaluation_eligible', 'benchmark_timed_out'):
                value = str(row.get(key) or '').lower()
                if value not in ('true', 'false', ''):
                    raise ValueError(f'invalid boolean in {key}')
                row[key] = None if not value else value == 'true'
            for key in ('start_time', 'end_time', 'duration_s', 'planning_latency_ms',
                        'llm_response_ms'):
                raw = row.get(key)
                value = float(raw) if raw not in ('', None) else None
                if value is not None and not math.isfinite(value):
                    raise ValueError(f'nonfinite {key}')
                row[key] = value
            for key in ('total_actions', 'completed_actions', 'llm_attempts'):
                value = row.get(key)
                row[key] = int(value) if value not in ('', None) else None
            records.append(row)
        return records


def calculate(records: list[dict[str, Any]], environment: str | None = None) -> dict[str, Any]:
    """Calculate mission, action, latency, recovery and verified-contact metrics.

    Args:
        records: Parsed mission records.
        environment: Explicit hardware/simulation selection when archives are mixed.
    Returns:
        JSON-compatible summary with denominators and metric definitions.
    Raises:
        ValueError: If duplicate IDs conflict or simulation/hardware evidence is pooled.
    """
    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        identity = str(record.get('mission_id') or '')
        if not identity:
            raise ValueError('records require mission IDs')
        if identity in unique and unique[identity] != record:
            raise ValueError(f'conflicting duplicate mission: {identity}')
        unique[identity] = record
    records = list(unique.values())
    modes = {str(item.get('environment', 'unspecified')) for item in records}
    if environment:
        records = [item for item in records if item.get('environment') == environment]
    elif len(modes - {'unspecified', ''}) > 1:
        raise ValueError('hardware and simulation results must be analyzed separately')
    eligible = [item for item in records if item.get('evaluation_eligible') is not False and
                item.get('phase') not in ('reset', 'control')]
    terminal = [item for item in eligible if item.get('terminal_state') in ('DONE', 'FAILED')]
    unfinished = len(eligible)-len(terminal)

    def task_complete(item: dict[str, Any]) -> bool:
        """Require observed completion of every planned logical step."""
        planned = int(item.get('total_actions') or 0)
        successful = {action.get('step') for action in item.get('action_results', [])
                      if action.get('success') is True}
        return (item.get('success') is True and item.get('terminal_state') == 'DONE'
                and planned > 0 and set(range(planned)) <= successful
                and not item.get('benchmark_timed_out'))
    successful_tasks = sum(task_complete(item) for item in terminal)
    task_success = percentage(successful_tasks, len(terminal))
    action_counts: dict[str, list[int]] = {}
    attempt_counts: dict[str, list[int]] = {}
    perception = []
    grasp = []
    recovered, recovery_total = 0, 0
    for record in terminal:
        attempts = record.get('action_results', [])
        logical: dict[Any, list[dict]] = {}
        for attempt in attempts:
            kind = str(attempt.get('action', 'unknown'))
            if attempt.get('success') is not None:
                counts = attempt_counts.setdefault(kind, [0, 0])
                counts[0] += attempt.get('success') is True
                counts[1] += 1
            logical.setdefault(attempt.get('step', attempt.get('action_id')), []).append(attempt)
        for group in logical.values():
            kind = str(group[-1].get('action', 'unknown'))
            counts = action_counts.setdefault(kind, [0, 0])
            counts[0] += any(attempt.get('success') is True for attempt in group)
            counts[1] += 1
        for item in record.get('perception_latencies_ms', []):
            value = finite_number(item.get('latency_ms'))
            if value is not None:
                perception.append(value)
        grasp.extend(record.get('grasp_outcomes', []))
        groups: dict[Any, list[dict]] = {}
        for recovery in record.get('recovery_events', []):
            step = recovery.get('step')
            if step is None:
                try:
                    step = int(str(recovery.get('action_id', '')).split(':')[0])
                except ValueError:
                    step = recovery.get('action_id')
            groups.setdefault(step, []).append(recovery)
        for step, events in groups.items():
            recovery_total += 1
            first = min(event['time'] for event in events)
            recovered += any(attempt.get('success') is True and attempt.get('end_time') is not None
                             and attempt['end_time'] >= first
                             for attempt in logical.get(step, []))
    verified = [outcome for outcome in grasp if outcome.get('verified') is True
                and isinstance(outcome.get('object_held'), bool)]
    failures = len(terminal)-successful_tasks
    active_s = sum(value for item in terminal
                   if (value := finite_number(item.get('duration_s'))) is not None and value >= 0)
    llm = [value for item in terminal
           if item.get('llm_attempts') != 0
           if (value := finite_number(item.get('llm_response_ms'))) is not None]
    selected_llm = [value for item in terminal if item.get('planner') == 'llm'
                    if (value := finite_number(item.get('llm_response_ms'))) is not None]
    planning = [value for item in terminal
                if (value := finite_number(item.get('planning_latency_ms'))) is not None]
    return {
        'schema_version': 1, 'mission_count': len(records), 'eligible_terminal_missions': len(
            terminal), 'unfinished_missions': unfinished, 'excluded_missions': len(records)-len(
                eligible), 'environments': sorted(modes) if not environment else [environment],
        'task_success_rate': task_success,
        'action_success_rate': {key: percentage(*counts) for key, counts in sorted(
            action_counts.items())},
        'action_attempt_success_rate': {key: percentage(*counts) for key, counts in sorted(
            attempt_counts.items())},
        'llm_response_latency_ms': distribution(llm),
        'selected_llm_response_latency_ms': distribution(selected_llm),
        'planner_counts': {source: sum(item.get('planner') == source for item in terminal)
                           for source in sorted({str(item.get('planner')) for item in terminal})},
        'planning_latency_ms': distribution(planning),
        'perception_latency_ms': distribution(perception),
        'grasp_accuracy': percentage(sum(item['object_held'] for item in verified), len(verified)),
        'grasp_unverified_count': len(grasp)-len(verified),
        'active_operation_mtbf_s': active_s/failures if failures else None,
        'observed_active_s': active_s, 'failure_count': failures,
        'mtbf_censored_lower_bound_s': active_s if not failures else None,
        'recovery_success_rate': percentage(recovered, recovery_total),
        'definitions': {
            'task_success': 'Terminal eligible mission with every planned step successful.',
            'unfinished': 'Right-censored pending missions excluded from terminal denominators.',
            'action_success': 'Logical step success; retries grouped by step.',
            'grasp_accuracy': 'Verified held/not-held contact labels; unknown excluded.',
            'mtbf': 'Active mission time divided by failed missions; idle time excluded.',
            'recovery': 'Recovered logical steps divided by steps with any retry/scan episode.',
            'confidence_interval': 'Wilson interval, 95%; no independence claim for repeats.',
        },
    }


def latex_escape(text: str) -> str:
    """Escape a value for a LaTeX text table cell.

    Args:
        text: Untrusted label or command fragment.
    Returns:
        Escaped LaTeX text.
    """
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
                    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(character, character) for character in text)


def summary_rows(summary: dict[str, Any]) -> list[tuple[str, str, int | str]]:
    """Produce a shared table representation for text and LaTeX exports.

    Args:
        summary: Calculated metrics.
    Returns:
        Metric name, formatted value, denominator/sample-count rows.
    """
    rows = []
    for label, key in (('Task success (%)', 'task_success_rate'),
                       ('Verified grasp accuracy (%)', 'grasp_accuracy'),
                       ('Recovery success (%)', 'recovery_success_rate')):
        metric = summary[key]
        value = 'NA' if metric['percent'] is None else f"{metric['percent']:.2f}"
        rows.append((label, value, metric['n']))
    for label, key in (('LLM response latency (ms)', 'llm_response_latency_ms'),
                       ('Planning latency (ms)', 'planning_latency_ms'),
                       ('Perception latency (ms)', 'perception_latency_ms')):
        metric = summary[key]
        value = 'NA' if metric['mean'] is None else f"{metric['mean']:.2f}"
        rows.append((label, value, metric['n']))
    value = summary['active_operation_mtbf_s']
    rows.append(('Active-operation MTBF (s)', 'NA (censored)' if value is None else
                 f'{value:.2f}', summary['failure_count']))
    for action, metric in summary['action_success_rate'].items():
        value = 'NA' if metric['percent'] is None else f"{metric['percent']:.2f}"
        rows.append((f'{action} success (%)', value, metric['n']))
    return rows


def export_report(summary: dict[str, Any], directory: Path) -> list[Path]:
    """Save text/JSON/LaTeX summaries and labelled matplotlib PNG charts.

    Args:
        summary: Calculated metrics; no synthetic observations are added.
        directory: Report destination.
    Returns:
        List of generated artifacts.
    Raises:
        OSError: If files cannot be written.
        ImportError: If matplotlib is absent.
    """
    directory.mkdir(parents=True, exist_ok=True)
    rows = summary_rows(summary)
    text = '\n'.join(f'{label:<38} {value:>16}   n={count}' for label, value, count in rows)
    text += f"\nUnverified grasps: {summary['grasp_unverified_count']}\n"
    text += f"Unfinished missions (censored): {summary['unfinished_missions']}\n"
    text += f"Excluded reset/control missions: {summary['excluded_missions']}\n"
    text += '\nDefinitions:\n' + '\n'.join(f'{key}: {value}' for key, value in summary[
        'definitions'].items()) + '\n'
    outputs = [directory/'summary.txt', directory/'summary.json', directory/'summary.tex']
    outputs[0].write_text(text, encoding='utf-8')
    outputs[1].write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    lines = [r'\begin{tabular}{lrr}', r'\toprule', r'Metric & Estimate & $n$ \\', r'\midrule']
    lines.extend(' & '.join(latex_escape(str(cell)) for cell in row) + r' \\' for row in rows)
    lines.extend([r'\bottomrule', r'\end{tabular}'])
    outputs[2].write_text('\n'.join(lines)+'\n', encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rate_keys = [('Task', 'task_success_rate'), ('Verified grasp', 'grasp_accuracy'),
                 ('Recovery', 'recovery_success_rate')]
    fig, axis = plt.subplots(figsize=(7, 4))
    for index, (label, key) in enumerate(rate_keys):
        metric = summary[key]
        if metric['percent'] is None:
            axis.text(index, 3, 'NA (n=0)', ha='center')
        else:
            value = metric['percent']
            lo, hi = metric['ci95_percent']
            axis.bar(index, value, color='steelblue')
            axis.errorbar(index, value, yerr=[[value-lo], [hi-value]], color='black',
                          capsize=4, fmt='none')
            axis.text(index, min(103, value+4), f"n={metric['n']}", ha='center')
    axis.set(xticks=range(len(rate_keys)), xticklabels=[item[0] for item in rate_keys],
             ylabel='Success rate (%)', xlabel='Metric', ylim=(0, 112),
             title='Mission outcomes with Wilson 95% intervals')
    axis.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    path = directory/'success_rates.png'
    fig.savefig(path, dpi=180)
    plt.close(fig)
    outputs.append(path)
    fig, axis = plt.subplots(figsize=(7, 4))
    latency_keys = [('LLM response', 'llm_response_latency_ms'),
                    ('Planning', 'planning_latency_ms'), ('Perception', 'perception_latency_ms')]
    for index, (_, key) in enumerate(latency_keys):
        metric = summary[key]
        if metric['mean'] is None:
            axis.text(index, 0, 'NA (n=0)', ha='center')
        else:
            axis.bar(index, metric['mean'], color='darkorange', yerr=metric['std'], capsize=4)
    axis.set(xticks=range(3), xticklabels=[item[0] for item in latency_keys],
             xlabel='Pipeline stage', ylabel='Latency (ms)',
             title='Observed latency: mean and population standard deviation')
    axis.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    path = directory/'latencies.png'
    fig.savefig(path, dpi=180)
    plt.close(fig)
    outputs.append(path)
    fig, axis = plt.subplots(figsize=(7, 4))
    actions = summary['action_success_rate']
    labels = list(actions)
    if labels:
        axis.bar(labels, [actions[key]['percent'] or 0 for key in labels], color='seagreen')
    else:
        axis.text(0.5, 0.5, 'No observed action outcomes', ha='center', transform=axis.transAxes)
    axis.set(xlabel='Action type', ylabel='Logical action success (%)', ylim=(0, 105),
             title='Action success after bounded recovery')
    axis.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    path = directory/'action_success.png'
    fig.savefig(path, dpi=180)
    plt.close(fig)
    outputs.append(path)
    return outputs


def main(args: list[str] | None = None) -> int:
    """Generate an analysis report from existing evidence without running ROS.

    Args:
        args: Optional command-line arguments.
    Returns:
        Zero after a successful report, two for invalid/unreadable evidence.
    """
    parser = argparse.ArgumentParser(description='Analyze E-AIRA CSV or JSON mission evidence')
    parser.add_argument('input', nargs='+', type=Path)
    parser.add_argument('--output-dir', type=Path, default=Path('evaluation_report'))
    parser.add_argument('--environment', choices=('hardware', 'simulation', 'simulation_oracle'))
    options = parser.parse_args(args)
    try:
        records = [record for path in options.input for record in read_records(path.expanduser())]
        summary = calculate(records, options.environment)
        export_report(summary, options.output_dir.expanduser())
        for label, value, count in summary_rows(summary):
            print(f'{label:<38} {value:>16}   n={count}')
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        parser.exit(2, f'evaluation failed: {exc}\n')
    return 0
