"""Validate daily durability and research metric denominators/artifacts.

Author: E-AIRA maintainers.
Hardware target: hardware-free ROSMASTER M3 Pro / Jetson Orin NX evaluation tests.
"""

from copy import deepcopy
import csv
import json
from pathlib import Path

import pytest

from eira_evaluation.metrics_calculator import (
    calculate, distribution, export_report, latex_escape, percentage, read_records,
)
from eira_evaluation.records import CSV_FIELDS
from eira_evaluation.storage import DailyArchive
from test_records import completed_mission


def test_archive_roundtrip_csv_json_and_stable_headers(tmp_path: Path) -> None:
    """CSV headers and detailed JSON survive a fresh archive reader."""
    archive = DailyArchive(tmp_path)
    record = completed_mission()
    paths = archive.save([record])
    assert len(paths) == 1
    with paths[0].open(newline='') as handle:
        assert tuple(next(csv.reader(handle))) == CSV_FIELDS
    assert read_records(paths[0])[0]['success'] is True
    assert read_records(paths[0].with_suffix('.json')) == [record]
    archive.close()
    restored = DailyArchive(tmp_path)
    assert restored.load() == [record]
    restored.close()


def test_second_writer_cannot_clobber_results(tmp_path: Path) -> None:
    """Two logger processes cannot replace the same daily snapshot concurrently."""
    archive = DailyArchive(tmp_path)
    with pytest.raises(RuntimeError):
        DailyArchive(tmp_path)
    archive.close()


def test_json_recovers_missing_or_corrupt_csv(tmp_path: Path) -> None:
    """An interrupted JSON-before-CSV transaction is repaired on startup."""
    archive = DailyArchive(tmp_path)
    csv_path = archive.save([completed_mission()])[0]
    archive.close()
    csv_path.write_text('partial\n')
    restored = DailyArchive(tmp_path)
    restored.load()
    assert read_records(csv_path)[0]['mission_id'] == 'm1'
    restored.close()


def test_unmatched_commands_are_durable(tmp_path: Path) -> None:
    """A command observed without a running Brain is retained as unassigned evidence."""
    archive = DailyArchive(tmp_path)
    archive.save([], [{'command': 'find cup', 'received_at': 100.0}])
    archive.close()
    restored = DailyArchive(tmp_path)
    assert restored.load() == []
    assert restored.unmatched_commands[0]['command'] == 'find cup'
    restored.close()


def test_metrics_do_not_infer_physical_grasp_from_grasped() -> None:
    """Successful manipulation with no contact evidence yields an NA grasp metric."""
    summary = calculate([completed_mission()])
    assert summary['task_success_rate']['percent'] == 100
    assert summary['grasp_accuracy']['percent'] is None
    assert summary['grasp_unverified_count'] == 1
    assert summary['active_operation_mtbf_s'] is None
    assert summary['mtbf_censored_lower_bound_s'] == pytest.approx(3.1)


def test_failure_rates_and_active_mtbf_have_explicit_denominators() -> None:
    """MTBF uses active exposure and failures; pending/reset records are not pooled."""
    good = completed_mission()
    bad = deepcopy(good)
    bad.update(mission_id='m2', success=False, terminal_state='FAILED', duration_s=6.9)
    bad['action_results'][1]['success'] = False
    setup = deepcopy(good)
    setup.update(mission_id='reset', phase='reset', evaluation_eligible=False)
    pending = deepcopy(good)
    pending.update(mission_id='pending', terminal_state='', success=None)
    summary = calculate([good, bad, setup, pending])
    assert summary['task_success_rate']['percent'] == 50
    assert summary['eligible_terminal_missions'] == 2
    assert summary['unfinished_missions'] == 1
    assert summary['excluded_missions'] == 1
    assert summary['active_operation_mtbf_s'] == pytest.approx(10)
    assert summary['action_success_rate']['grasp']['percent'] == 50


def test_recovery_is_step_based_and_requires_later_success() -> None:
    """Repeated scans of one step form one recovery denominator."""
    record = completed_mission()
    record['recovery_events'] = [
        {'step': 0, 'action_id': '0:1', 'kind': 'retry', 'time': 100.5},
        {'step': 0, 'action_id': '0:1', 'kind': 'scan', 'time': 101.0}]
    summary = calculate([record])
    assert summary['recovery_success_rate']['n'] == 1
    assert summary['recovery_success_rate']['percent'] == 100


def test_verified_false_contact_is_a_real_failure() -> None:
    """Explicit verified not-held labels belong in the grasp accuracy denominator."""
    record = completed_mission()
    record['grasp_outcomes'][0].update(verified=True, object_held=False)
    summary = calculate([record])
    assert summary['grasp_accuracy']['percent'] == 0
    assert summary['grasp_accuracy']['n'] == 1


def test_mixed_simulation_hardware_requires_filter() -> None:
    """Simulation and hardware outcomes cannot silently inflate one combined result."""
    hardware = completed_mission()
    hardware['environment'] = 'hardware'
    simulation = deepcopy(hardware)
    simulation.update(mission_id='sim', environment='simulation')
    with pytest.raises(ValueError):
        calculate([hardware, simulation])
    assert calculate([hardware, simulation], 'hardware')['mission_count'] == 1


def test_wilson_interval_and_missing_distributions() -> None:
    """Confidence intervals remain bounded and unavailable latencies stay null."""
    estimate = percentage(20, 20)
    assert estimate['ci95_percent'][0] < 100
    assert estimate['ci95_percent'][1] == pytest.approx(100)
    assert percentage(0, 0)['percent'] is None
    assert distribution([])['mean'] is None
    assert distribution([1, 2, 3])['median'] == 2


def test_report_produces_labeled_png_and_escaped_latex(tmp_path: Path) -> None:
    """Research exports are standalone artifacts, including a booktabs LaTeX table."""
    paths = export_report(calculate([completed_mission()]), tmp_path)
    assert {path.suffix for path in paths} == {'.txt', '.json', '.tex', '.png'}
    for path in paths:
        assert path.stat().st_size > 0
    for path in paths:
        if path.suffix == '.png':
            assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert '\\begin{tabular}' in (tmp_path/'summary.tex').read_text()
    assert latex_escape('a_b&50%') == r'a\_b\&50\%'
    assert json.loads((tmp_path/'summary.json').read_text())['task_success_rate']['n'] == 1


def test_archive_rollover_clears_previously_unmatched_commands(tmp_path: Path) -> None:
    """Cross-midnight identity assignment must not resurrect an old pending command."""
    archive = DailyArchive(tmp_path)
    archive.save([], [{'command': 'find cup', 'received_at': 86399.0}])
    record = completed_mission()
    record['start_time'] = 86401.0
    archive.save([record], [])
    archive.close()
    restored = DailyArchive(tmp_path)
    assert len(restored.load()) == 1
    assert restored.unmatched_commands == []
    restored.close()


def test_malformed_csv_headers_fail_explicitly(tmp_path: Path) -> None:
    """Unrelated CSV data cannot accidentally be treated as mission results."""
    path = tmp_path/'unrelated.csv'
    path.write_text('name,value\ncup,1\n')
    with pytest.raises(ValueError):
        read_records(path)


def test_conflicting_duplicate_missions_are_not_double_counted() -> None:
    """Combining overlapping archives requires matching evidence, not duplicate samples."""
    record = completed_mission()
    changed = deepcopy(record)
    changed['success'] = False
    with pytest.raises(ValueError):
        calculate([record, changed])
    assert calculate([record, record])['eligible_terminal_missions'] == 1


def test_oracle_results_remain_separate_from_learned_perception() -> None:
    """Ground-truth simulation is not pooled with learned-vision simulation evidence."""
    learned = completed_mission()
    learned['environment'] = 'simulation'
    oracle = deepcopy(learned)
    oracle.update(mission_id='oracle', environment='simulation_oracle')
    with pytest.raises(ValueError):
        calculate([learned, oracle])
    assert calculate([learned, oracle], 'simulation_oracle')['mission_count'] == 1


def test_perfect_ten_trial_rate_has_nonnegative_chart_error_bars(tmp_path: Path) -> None:
    """Floating-point Wilson endpoints must not break a 100-percent PNG export."""
    estimate = percentage(10, 10)
    assert estimate['ci95_percent'][1] >= estimate['percent']
    records = []
    for number in range(10):
        record = completed_mission()
        record['mission_id'] = f'm{number}'
        records.append(record)
    assert all(path.is_file() for path in export_report(calculate(records), tmp_path))
