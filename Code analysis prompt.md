# MASTER PROMPT — COMPLETE CODE ANALYSIS + SURGICAL UI/UX REFINEMENT

> This file intentionally preserves the complete contents of both supplied master prompts. The second prompt is retained in full as the surgical refinement layer, followed by the additional execution/full-width requirements requested in this revision.

## SOURCE PROMPT A — CODE ANALYSIS HTML — MASTER PROMPT

**# CODE ANALYSIS HTML — MASTER PROMPT**

**## Claude Code / GLM-5.3 Edition**

You are an expert **\*\*Software Engineer, Code Reviewer, Technical Educator, UI/UX Designer, Professional Animator, Data Visualizer, and Mathematics Explainer\*\***.

Your task is to transform the source code provided at [path that pasted in terminal] into **\*\*one polished, self-contained, interactive HTML code-analysis application\*\***.

The final deliverable must be a **\*\*complete HTML document\*\*** and nothing else.

Do not give me a plan.\\

Do not give me a partial implementation.\\

Do not use placeholders.\\

Do not omit sections because the source code is long.\\

Do not summarize the source code instead of analyzing it.

Analyze the actual source code and generate the complete interactive HTML.

\---

**# 0. CORE OBJECTIVE**

Create an interactive **\*\*Line-by-Line Code Analysis HTML\*\*** that teaches the user:

1\. What the code does.

2\. How each  line/block works with an in-depth explanation.

3\. Why the implementation is structured this way.

4\. What mathematical concepts are involved, including basic formulas with in-depth application.

5\. What would happen in the real-world system when the code executes.

6\. What could go wrong if a value, formula, coordinate, transformation, or assumption is incorrect.

7\. How the mathematical model maps to the actual implementation.

The result should feel like a **\*\*professional interactive technical documentation/engineering learning interface\*\***, not a generic HTML page.

\---

**# 1. OUTPUT CONTRACT — NON-NEGOTIABLE**

Requirements:

\- Single file for each folder.

\- Self-contained.

\- External JavaScript libraries also fine for a professional result.

\- External CSS libraries also fine for a professional outcome.

\- External CDN is accepted.

\- External beautiful fonts also allowed.

\- Fonts should be well structured; Bangla words must be in Bengali, but English words must be in English format.

\- External images are also allowed.

\- SVG animations must be reduce overlapping, understandable and make smoother.

\- If needed use Z-index to visualize the animation and words/sentences.

\- Everything required to run the application must exist inside this one HTML file.

The HTML must work when opened directly in a browser.

\---

**# 2. SOURCE-CODE FIDELITY**

The source code supplied as a path in this directory [path that pasted in terminal].

You MUST:

\- Analyze the actual code.

\- Preserve code snippets exactly.

\- Never invent functions, variables, formulas, behavior, or system components that do not exist.

\- Never silently rewrite source code.

\- Never "correct" the source code while presenting it.

\- Clearly distinguish between:

  \- what the code actually does,

  \- what the code appears intended to do,

  \- and what could happen if the implementation is incorrect.

If the source code contains a bug, explain the bug instead of silently fixing it.

If the source code contains no meaningful mathematics, do not manufacture mathematics merely to create a Math section.

If a concept is mathematical but the implementation only indirectly uses it, explain the actual mathematical relationship accurately.

Never replace the original command or source expression with an altered "clean" version in the code card. Any normalized form may appear only as a clearly labeled mathematical or explanatory representation outside the original-code display.

\---

**# 3. SECTIONING**

Divide the source code into approximately **\*\*5-15 logical Parts/Sections\*\***.

Do NOT split the code arbitrarily.

Create boundaries around meaningful concepts such as:

\- imports/dependencies

\- configuration

\- constants

\- initialization

\- classes/functions

\- data processing

\- coordinate transformations

\- mathematical calculations

\- control logic

\- hardware interaction

\- main execution

\- cleanup/error handling

The exact number may vary when necessary for the source code, but target **\*\*5–15 Parts\*\***.

Every Part must have:

\`\`\`javascript

{

  id,

  fname,

  enTitle,

  code,

  explain,

  mathFormula,

  mathExplain,

  robot,

  flags,

  hasAnim,

  animType

}

\`\`\`

Optional properties may be omitted when genuinely unnecessary.

\---

**# 4. PAGE ARCHITECTURE**

**## Desktop Layout**

Use a two-column application layout:

\`\`\`text

┌──────────────────┬─────────────────────────────────────────────┐

│                  │                                             │

│    NEUROBOTICS   │               MAIN CONTENT                  │

│                  │                                             │

│                  │                                             │

│ filename         │ PART 01 / N · filename                      │

│ N Parts          │ English Title                               │

│                  │                                             │

│ 01 Introduction  │ Code Card                                   │

│ 02 Config        │ Explanation                                 │

│ 03 Function      │ Math                                        │

│ ...              │ Real System                                 │

│                  │ Animation                                   │

│                  │                                             │

│                  │ ← Previous                          Next →  │

└──────────────────┴─────────────────────────────────────────────┘

\`\`\`

**## Sidebar**

The sidebar must be fixed.

Top area:

\- filename

\- total number of Parts

Example:

\`\`\`text

01\. arm calibration

4 files

10 Parts

\`\`\`

Navigation items:

\`\`\`text

01  Imports

02  Configuration

03  Camera Model

04  Coordinate Transform

...

\`\`\`

**### Important**

The Sidebar MUST NOT contain:

\- Bangla subtitles

\- "লাইন-বাই-লাইন"

\- explanatory text

\- flag labels

\- emojis

\- decorative glyphs

Only:

**\*\*number + English title\*\***

Active Part must be visually highlighted.

Clicking a navigation item must smoothly navigate to the corresponding Part.

\---

**# 5. RESPONSIVE DESIGN**

The page must work well on:

\- large desktop screens

\- laptops

\- tablets

\- mobile screens

On smaller screens:

\- Sidebar should transform into a compact top navigation/drawer.

\- Content should remain readable.

\- Code blocks must horizontally scroll rather than break the layout.

\- Animation must scale responsively.

\- Navigation must remain usable.

\---

**# 6. PART STRUCTURE**

Every Part must follow this exact conceptual order.

**## A. Section Header**

Display:

\`\`\`text

PART 01 / 10 · arm\_offset.py

Camera Coordinate Setup

\`\`\`

Use:

\- small uppercase eyebrow

\- large English title

\- subtle metadata

The title itself must remain English.

\---

**## B. CODE CARD**

Create a terminal-style, VS Code-inspired code card.

Header:

```text
● ● ●    arm_offset.py
```

The three dots should be implemented with CSS.

Do NOT use emoji characters.

The source code must appear inside:

```html
<pre><code>...</code></pre>
```

**VS Code-style line-number gutter**

Every displayed source-code line must have a visible line number in a dedicated left gutter, visually similar to VS Code.

Line numbers must be generated from the **actual source-code line positions**, not manually typed into the source.

Preserve the original line numbering relative to the complete source file. If a Part contains lines 41–58 of the source, the gutter must show 41–58 rather than restarting at 1.

Blank source lines must still receive line numbers.

Line numbers must be visually separate from the code so that they are **not part of the code text**.

Copying the code must copy the original source code only, without line numbers.

Scrolling horizontally must keep the line-number gutter usable and prevent line numbers from becoming part of the source-code content.

Do not use fake line numbers such as `1`, `2`, `3` when the displayed snippet comes from later lines of the original file.

**Original source fidelity**

Keep the original code exactly as supplied.

Preserve:

- indentation
- line breaks
- blank lines
- punctuation
- variable names
- comments
- string contents
- syntax
- commands
- command arguments
- shell commands
- paths
- flags/options
- ordering

Do not rewrite, simplify, normalize, translate, or "clean up" the original commands merely for presentation.

If the source contains a command such as a terminal command, display that command exactly as provided.

The generated explanation may reference a command, but the displayed command itself must remain unchanged.

Use readable syntax-oriented colors where practical, but do not require a syntax-highlighting library.

The code gutter, syntax highlighting, selection state, copy button, and surrounding UI must never modify the underlying source-code string.

If syntax highlighting is applied, it must be presentation-only and must preserve the exact source text.

\---


**# 7. LINE-BY-LINE EXPLANATION**

Every Part must contain:

Badge:

\`\`\`text

EX

\`\`\`

Accent:

\`\`\`text

\#4fc3f7

\`\`\`

Each important line or logical block must have:

\`\`\`text

CODE SNIPPET + ORIGINAL SOURCE LINE NUMBER

↓

বাংলা explanation

\`\`\`

The line number shown in an explanation must refer to the original source file, not a renumbered copy.

If multiple consecutive lines form one logical operation, show the exact contiguous source range and explain the relationship between those lines.

For example:

\`\`\`text

fx = camera\_matrix[0, 0]

\`\`\`

Then explain in Bangla:

\- এই line-টি কী করছে

\- কোন Variable থেকে value নেওয়া হচ্ছে

\- value-টির অর্থ কী

\- পরবর্তী calculation-এ এটি কেন দরকার

\- implementation-level behavior কী

\- mathmatics behind it starting from basic to advanced formula

Do not merely translate the code.

Teach the reasoning.

\---

**# 8. LANGUAGE RULES**

All explanatory prose MUST be written in **\*\*Bangla\*\***.

However, common technical terminology and English words MUST remain in English.

Never transliterate common technical terms into Bangla script.

Example:

\`\`\`text

Camera-র Coordinate System-এ এই Point-টি Transform করা হচ্ছে।

\`\`\`

Incorrect:

\`\`\`text

ক্যামেরার কোঅর্ডিনেট সিস্টেমে এই পয়েন্টটি...

\`\`\`

Bangla suffixes may be attached with hyphens:

\`\`\`text

Camera-র

Function-টি

Matrix-এর

Pixel-এ

Variable-টি

\`\`\`

\---

**# 9. CODE MUST NEVER BE TRANSLATED**

Source code must remain exactly as provided.

For inline references, use:

\`\`\`html

\<code>variable\_name\</code>

\`\`\`

Never translate identifiers.

Never rename variables.

Never alter formulas.

Never modify code simply to make the explanation easier.

\---

**# 10. MATH SECTION**

Only include this section when the Part genuinely involves mathematics.

Title:

**## "Math Behind This Code"**

Badge:

```text
Σ
```

Accent:

```text
#7ee787
```

This section must teach the **mathematics behind the implementation as a progressive derivation**, beginning with the simplest relevant equations and building toward the exact or advanced form used by the code.

Do **not** jump directly to the final formula.

Use the following progression whenever the mathematics supports it:

**Level 1 — Symbols, units, and basic quantities**

Identify the physical or numerical quantities first.

Explain what each variable represents, its unit where meaningful, its sign convention, and whether it is scalar, vector, matrix, angle, probability, coordinate, or another quantity.

**Level 2 — Basic equation**

Start with the simplest relevant relationship.

Example:

```text
distance = speed × time
```

Explain the equation in plain Bangla and connect every term to the source code.

**Level 3 — Algebraic transformation**

Show how rearrangement, substitution, normalization, or simplification produces the next form.

Do not skip important algebraic steps when those steps are necessary to understand the final implementation.

**Level 4 — Geometric / physical interpretation**

Explain why the equation is true using the relevant first principles.

Depending on the code, this may involve:

- similar triangles
- trigonometry
- vector geometry
- coordinate systems
- conservation relationships
- probability/statistics
- physical laws
- other directly relevant principles

**Level 5 — General mathematical form**

Derive the more general form used by the implementation.

For example, move from a scalar equation to vector or matrix notation when the code actually uses vectors or matrices.

**Level 6 — Advanced form**

Only when genuinely required by the source code, continue into advanced concepts such as:

- homogeneous coordinates
- rotation matrices
- Euler angles
- quaternions
- Jacobians
- optimization
- probability distributions
- filtering
- control laws
- numerical methods
- differential equations
- other relevant advanced mathematics

Never introduce advanced mathematics just to make the section look sophisticated.

**For every important formula:**

**Step 1 — State the formula in LaTeX format**

Render equations using proper LaTeX/MathJax notation where available.

Example:

```text
X = \frac{(p_x-c_x)Z}{f_x}
```

**Step 2 — Define every symbol**

Explain:

- `p_x`
- `c_x`
- `Z`
- `f_x`
- `X`

Also state units and dimensions when they matter.

**Step 3 — Derive it from the simplest relevant equation**

Show the intermediate equations needed to reach the implementation formula.

For example, if the code uses perspective projection:

- start from the pinhole-camera relationship
- explain similar triangles
- introduce focal length
- introduce principal point
- derive pixel-coordinate scaling
- rearrange to obtain the inverse projection
- connect each algebraic term to the exact code variable

**Step 4 — Numerical Example**

Use a small concrete example and calculate it step by step.

For example:

```text
p_x = 420
c_x = 320
Z   = 2.0 m
f_x = 500
```

Then calculate:

```text
X = ((420 - 320) × 2.0) / 500
  = 0.40 m
```

**Step 5 — Dimensional / unit check**

Where applicable, verify that the units on both sides of the equation are consistent.

**Step 6 — Code-to-equation mapping**

Explicitly show which source-code expression corresponds to which mathematical term.

Example:

```text
Code: X = (px - cx) * depth / fx
Math: X = (p_x - c_x) Z / f_x
```

**Step 7 — Failure intuition**

Explain what changes if:

- `f_x` is wrong
- `c_x` is wrong
- depth is wrong
- sign is reversed
- units are inconsistent
- coordinate convention is incorrect
- a matrix/vector dimension is incorrect

The reader should understand the **derivation, assumptions, numerical meaning, and implementation mapping**, not merely memorize the final formula.

When a derivation is not mathematically justified by the source code, explicitly say that the source does not provide enough information rather than inventing a derivation.

\---


**# 11. MATHEMATICAL DEPTH RULE**

Whenever mathematics exists, explain it at the appropriate depth.

Possible topics include:

\- algebra

\- geometry

\- trigonometry

\- vectors

\- matrices

\- linear transformations

\- coordinate systems

\- homogeneous coordinates

\- rotations

\- Euler angles

\- quaternions

\- perspective projection

\- camera calibration

\- interpolation

\- probability

\- filtering

\- optimization

\- control theory

\- kinematics

\- dynamics

\- PID

\- statistics

\- numerical methods

Do not introduce unrelated theory.

Only explain mathematics that is actually relevant to the source code.

\---

**# 12. REAL-WORLD SYSTEM BLOCK**

Every Part must contain:

**## "Real Robot/System এই code অনুযায়ী কী করবে"**

Badge:

\`\`\`text

RB

\`\`\`

Accent:

\`\`\`text

\#ffb454

\`\`\`

Explain the practical consequence.

Depending on the domain, describe what happens to:

\- Camera

\- Robot

\- Motor

\- Joint

\- Sensor

\- Vehicle

\- UI

\- Network

\- File system

\- Data pipeline

\- Control system

Explain both:

**### Correct behavior**

and, where relevant:

**### Incorrect behavior**

Example:

\`\`\`text

যদি depth value ভুল হয়, তাহলে calculated 3D Position-ও ভুল হবে।

এর ফলে Robot Controller ভুল target position পেতে পারে।

\`\`\`

Do not claim hardware behavior that is not supported by the code.

\---

**# 13. ANIMATION SYSTEM**

For mathematical Parts, create an optional interactive Animation Block when the concept can be clearly learned from visualization.

Use:

\- &#x20;JavaScript

\- Inline SVG

\- CSS

\- &#x20;animation libraries

Each animation must have:

\`\`\`text

Play, Slow (makes 50% slow), Fast (makes 50% faster), Pause, Stop buttons 

\`\`\`

Do not use proper icons for this buttons.

\---

**# 14. SVG QUALITY RULES**

Do NOT create simplistic flat animations such as:

\`\`\`text

\<circle>

\<line>

\`\`\`

unless those primitives are genuinely appropriate, perfect, and professional.

Instead, create domain-aware visualizations.

Examples:

**### Camera**

Show:

\- camera body

\- lens

\- optical axis

\- image plane

\- 3D point

\- projected point

\- depth indicator

**### Robot Arm**

Show:

\- base

\- joints

\- segments

\- end effector

\- coordinate frames

**### Vehicle**

Show:

\- chassis

\- wheels

\- direction vector

\- sensor field

**### Coordinate Transform**

Show:

\- coordinate axes

\- origin

\- vector

\- transformed vector

\- rotation

Use gradients and subtle visual depth.

\---

**# 15. SHARED SVG DEFINITIONS**

Create one shared SVG \`\<defs>\` section where practical.

Include reusable:

\- gradients

\- metallic gradients

\- lens gradients

\- point glow

\- Gaussian blur

\- drop shadow

\- glow effects

Example conceptual structure:

\`\`\`html

<*defs*>

  <*linearGradient* ...>

  <*radialGradient* ...>

  <*filter* ...>

\</*defs*>

\`\`\`

Reuse these definitions across animations.

\---

**# 16. ANIMATION MOTION**

Animations must feel polished, smooth, perfect.

Use easing such as:

\`\`\`javascript

easeInOutCubic

easeOutCubic

and others if needed

\`\`\`

Avoid mechanical linear movement wherever possible.

If useful, include:

\- fading motion trails

\- glow

\- subtle scale changes

\- progressive drawing

\- state transitions

\- labels appearing at the appropriate step

Animations should teach, not merely decorate.

\---

**# 17. LIVE FORMULA DISPLAY**

Mathematical animations must show the actual mathematical relationship on screen.

Example:

\`\`\`text

X = (px − cx) × Z / fx but in Latex format

\`\`\`

During animation, update the formula as the visual state changes.

For example:

\`\`\`text

px = 420

cx = 320

Z  = 2.0

fx = 500

X = 0.40 m

\`\`\`

The user should be able to visually connect:

\`\`\`text

formula → calculation → geometry → result

\`\`\`

\---

**# 18. LIVE CAPTION**

Every animation should have a live caption.

Example:

\`\`\`text

Camera থেকে 3D Point-এর ray বের করা হচ্ছে।

\`\`\`

Then:

\`\`\`text

Pixel coordinate থেকে Camera Coordinate-এ conversion করা হচ্ছে।

\`\`\`

Then:

\`\`\`text

Depth ব্যবহার করে X position calculate করা হচ্ছে।

\`\`\`

Captions must be Bangla with technical English terms preserved.

\---

**# 19. ANIMATION ARCHITECTURE**

Use separate functions:

\`\`\`javascript

async function animCameraProjection(wrap, id) {

  ...

}

async function animCoordinateTransform(wrap, id) {

  ...

}

\`\`\`

Route them through:

\`\`\`javascript

function runAnimation(type, id) {

  ...

}

\`\`\`

The animation type must be stored in \`PARTS\`.

Example:

\`\`\`javascript

{

  id: "part-04",

  ...

  hasAnim: true,

  animType: "cameraProjection"

}

\`\`\`

\---

**# 20. SINGLE SOURCE OF TRUTH — PARTS ARRAY**

All content must live inside one JavaScript array:

\`\`\`javascript

const PARTS = [

  {

    id: "part-01",

    fname: "example.py",

    enTitle: "Initialization",

    code: "...",

    explain: [

      {

        snippet: "...",

        text: "..."

      }

    ],

    mathExplain: "...",

    robot: "...",

    flags: [],

    hasAnim: false,

    animType: null

  }

];

\`\`\`

Sidebar must be generated from \`PARTS\`.

Sections must be generated from \`PARTS\`.

Navigation must be generated from \`PARTS\`.

Do NOT duplicate the same Part information in hardcoded HTML.

\---

**# 21. RENDERING ARCHITECTURE**

Use template literals where appropriate.

Conceptually:

\`\`\`javascript

function renderSidebar() {

  ...

}

function renderParts() {

  ...

}

function renderPart(part, index) {

  ...

}

\`\`\`

Recommended structure:

\`\`\`javascript

const PARTS = [...];

renderSidebar();

renderParts();

setupNavigation();

setupAnimations();

\`\`\`

Keep the JavaScript organized and maintainable.

\---

**# 22. NAVIGATION**

Each Part must have:

\- unique \`id\`

\- sidebar navigation item

\- Previous button

\- Next button

Example:

\`\`\`text

← Previous

Next →

\`\`\`

Use normal arrow characters only.

Do not use emoji arrows.

Navigation should use smooth scrolling.

The currently visible Part should automatically update the active Sidebar item.

Use \`IntersectionObserver\` when appropriate.

\---

**# 23. VISUAL DESIGN SYSTEM**

Use a dark professional engineering aesthetic.

**### Background**

Approximately:

\`\`\`css

*#0a0a0a*

*#111111*

\`\`\`

**### Cards**

Approximately:

\`\`\`css

*#151515*

*#181818*

\`\`\`

**### Borders**

Subtle dark-gray borders.

**### Explain Accent**

\`\`\`css

*#4fc3f7*

\`\`\`

**### Math Accent**

\`\`\`css

*#7ee787*

\`\`\`

**### Robot / Impact Accent**

\`\`\`css

\#ffb454

\`\`\`

Cards should have:

\- rounded corners

\- subtle border

\- restrained shadows

\- generous spacing

\- clear hierarchy

Avoid excessive decoration.

\---

**# 24. TYPOGRAPHY**

Use a strong, readable hierarchy.

Code:

\`\`\`text

JetBrains Mono / Fira Code style or the best suited one

\`\`\`

Since external fonts are forbidden, use a robust system fallback stack such as:

\`\`\`css

font-family:

  "JetBrains Mono",

  "Fira Code",

  Consolas,

  monospace;

\`\`\`

Body text should prioritize readability.

Bangla text must have sufficient:

\- line height

\- letter spacing

\- paragraph spacing

Do not make Bangla text too small.

\---

**# 25. NO EMOJIS**

Absolutely no emoji characters anywhere.

Forbidden examples include:

\`\`\`text

🎯

▶

✓

😀

🚀

🤖

\`\`\`

Use:

\- CSS shapes

\- text labels

\- borders

\- normal arrows

\- badges

instead.

\---

**# 26. CODE SAFETY / HTML ESCAPING**

**CONTROL-CHARACTER / ARTIFACT REMOVAL RULE**

The final HTML must contain **no invisible control-character artifacts** accidentally introduced by copying, formatting, or generation.

In particular, remove stray control characters such as `U+0000` through `U+0008`, `U+000B`, `U+000C`, and `U+000E` through `U+001F` wherever they are not legitimate source-code characters.

Never display replacement artifacts such as ``U+0001` followed by `0``, ``U+0001` followed by `1``, or similar invisible-character sequences.

This cleanup rule applies to the generated UI, explanatory text, badges, labels, metadata, and rendered code presentation.

**Important:** Do NOT alter legitimate characters that are actually part of the original source code. Preserve the original source code exactly; only remove accidental encoding/copy-paste artifacts introduced outside the source.

Because source code is inserted into HTML:

\- properly escape \`<\`

\- properly escape \`>\`

\- properly escape \`&\`

\- safely render quotes where required

\- preserve source formatting

Source code must not accidentally become HTML.

Use a safe escaping function where appropriate.

\---

**# 27. LARGE SOURCE FILE HANDLING**

If the source code is long:

\- Do NOT omit important code.

\- Do NOT replace sections with \`...\`.

\- Do NOT use "same as above".

\- Do NOT summarize a large function instead of showing it.

\- Split the code logically across Parts.
- Preserve the original source line numbers across all Parts.

The complete relevant source code must remain represented in the generated analysis.

If necessary, make each Part's code card scrollable.

\---

**# 28. ANALYSIS QUALITY STANDARD**

For every explanation, answer these questions where applicable:

**### WHAT?**

এই line/block কী করছে?

**### HOW?**

কীভাবে করছে?

**### WHY?**

কেন এভাবে করা হয়েছে?

**### \*\*WHEN?\*\***

কখন active হচ্ছে?

**### INPUT?**

কী input নিচ্ছে?

**### OUTPUT?**

কী output তৈরি করছে?

**### DEPENDENCY?**

কোন Variable/Function/Parameter-এর উপর নির্ভর করছে?

**### CONSEQUENCE?**

পরবর্তী system behavior-এ এর প্রভাব কী?

**### FAILURE?**

ভুল হলে কী হতে পারে?

This should be reflected naturally in the Bangla explanation rather than as repetitive headings for every line.

\---

**# 29. DO NOT OVER-EXPLAIN TRIVIAL SYNTAX**

Do not waste large amounts of space explaining obvious syntax such as:

\`\`\`python

import math

\`\`\`

with an entire paragraph if the meaning is obvious.

Instead, prioritize:

\- algorithms

\- data flow

\- transformations

\- formulas

\- assumptions

\- control flow

\- system behavior

\- important implementation decisions

The objective is **\*\*deep understanding\*\***, not maximum word count.

\---

**# 30. CODE-TO-THEORY CONNECTION**

Whenever possible, explicitly connect the code to the theory.

Example:

\`\`\`text

Code:

X = (px - cx) \* depth / fx

Math:

X = (px - cx)Z / fx

Meaning:

এই code-টি আসলে perspective projection-এর inverse relationship ব্যবহার করছে।

\`\`\`

The reader should be able to move naturally between:

\`\`\`text

Source Code

↓

Variable Meaning

↓

Mathematical Model

↓

Physical Meaning

↓

Real System Behavior

\`\`\`

\---

**# 31. FINAL VALIDATION BEFORE OUTPUT**

Before returning the HTML, internally verify all of the following:

\- [ ] Complete \`\<!DOCTYPE html>\` document exists.

\- [ ] HTML is self-contained.

\- [ ] External dependencies.

\- [ ] External CDN.

\- [ ] External assets.

\- [ ] \`PARTS\` exists.

\- [ ] Sidebar is generated from \`PARTS\`.

\- [ ] Sections are generated from \`PARTS\`.

\- [ ] Every Part has a unique \`id\`.

\- [ ] Every Part has navigation.

\- [ ] Code is preserved.

\- [ ] Code is safely HTML-escaped.

\- [ ] Bangla explanations use English technical terminology correctly.

\- [ ] No technical terms are unnecessarily transliterated into Bangla script.

\- [ ] Math sections appear only where appropriate.

\- [ ] Math explanations include first-principles reasoning.

\- [ ] A real-world impact section exists for every Part.

\- [ ] Animations use inline SVG.

\- [ ] Animation libraries are not used.

\- [ ] Animation functions use the router architecture.

\- [ ] Formula values appear during mathematical animations.

\- [ ] Captions update during animations.

\- [ ] Responsive behavior exists.

\- [ ] Active navigation state works.

\- [ ] Previous/Next navigation works.

\- [ ] No emoji characters exist.

\- [ ] No placeholder text remains.

\- [ ] No \`"..."\` is used to represent omitted source code.

\- [ ] No fabricated source-code behavior exists.

\---

**# 32. IMPORTANT EXECUTION RULE**

Do not stop after generating the first few Parts.

Do not reduce the amount of analysis because the source code is large.

Do not replace detailed explanations with generic statements such as:

\`\`\`text

এই অংশটি data process করে।

\`\`\`

Instead explain the actual mechanism.

The final HTML must be **\*\*complete, polished, functional, visually coherent, technically accurate, and ready to open in a browser\*\***.

---

## SOURCE PROMPT B — MASTER PROMPT — SURGICAL UI/UX & INTERACTIVE ANIMATION REFINEMENT

# MASTER PROMPT — SURGICAL UI/UX & INTERACTIVE ANIMATION REFINEMENT

## Claude Code CLI + GLM-5.3

You are working inside an existing code-analysis HTML project that has ALREADY been generated.

Your task is **NOT to regenerate the project from scratch**.

Your task is to **inspect the existing implementation, identify the existing HTML/CSS/JavaScript architecture, and surgically improve the generated HTML application according to the requirements below.**

Act as a senior:

- Frontend Engineer
- UI/UX Engineer
- Interactive Visualization Engineer
- SVG Animation Engineer
- Technical Documentation Engineer
- Robotics Visualization Engineer
- Accessibility Engineer
- QA Engineer

The final result must feel like a **premium professional engineering/code-analysis learning application**, not a generic AI-generated webpage.

---

# 1. CRITICAL SCOPE — DO NOT MODIFY THE SOURCE CODE

This is the most important rule.

## DO NOT CHANGE THE ORIGINAL ANALYZED SOURCE CODE.

The source code being analyzed must remain **100% unchanged**.

Do NOT:

- rewrite source code
- refactor source code
- rename variables
- rename functions
- change commands
- change parameters
- change formulas
- change paths
- change comments
- change whitespace inside the represented original source
- "fix" bugs in the analyzed source
- simplify source code
- normalize source code
- replace source code with cleaner code
- invent missing source code

The existing HTML is an **analysis/visualization layer around the original source**.

You are allowed to modify:

- HTML structure
- CSS
- UI components
- layout
- responsive behavior
- SVG animation implementation
- animation controls
- animation layering
- JavaScript used by the HTML application
- rendering logic
- navigation logic
- visual presentation
- debug visualization
- interactive educational components

You are NOT allowed to modify the actual source code represented inside the analysis.

### Important distinction

If the existing HTML contains:

```javascript
const PARTS = [...]
```

and the `code` property contains the original source code, preserve that source content exactly.

You may improve how that content is rendered.

You may improve the explanation around it.

You may improve the animation demonstrating it.

You may improve the debugging visualization.

But **never modify the analyzed source itself**.

---

# 2. FIRST: INSPECT BEFORE EDITING

Before making changes:

1. Locate the existing generated HTML.
2. Read the complete HTML.
3. Understand its existing architecture.
4. Identify:
   - `PARTS`
   - rendering functions
   - sidebar generation
   - Part rendering
   - animation system
   - animation controls
   - SVG structure
   - CSS layout
   - responsive behavior
   - code rendering
   - mathematical rendering
   - navigation
5. Determine how the existing application currently works.
6. Make the smallest architectural changes necessary.

Do NOT blindly regenerate the entire HTML.

Do NOT discard working functionality simply because you can implement it differently.

This is a **refinement task**, not a rewrite task.

---

# 3. PRIMARY FIX #1 — TITLE

The current page title contains something similar to:

```text
01. arm calibration — ক্যালিব্রেশন সিস্টেমের সম্পূর্ণ বিশ্লেষণ
```

This must be changed.

## Required final title:

```text
01. arm calibration
```

Remove:

```text
— ক্যালিব্রেশন সিস্টেমের সম্পূর্ণ বিশ্লেষণ
```

Do NOT display the Bangla subtitle after the title.

The title should be visually strong and clean.

### Required appearance

```text
01. arm calibration
```

No:

```text
01. arm calibration — ক্যালিব্রেশন সিস্টেমের সম্পূর্ণ বিশ্লেষণ
```

The English title remains the primary title.

Do not replace it with Bangla.

---

# 4. PRIMARY FIX #2 — HERO / INTRODUCTORY PARAGRAPH WIDTH

The introductory paragraph below the main title currently does not use the available content width effectively.

It appears constrained/narrower than the title and surrounding hero container.

Fix the layout.

## Required behavior

The introductory paragraph should use the **full available width of the main hero/content container**.

It should visually span from the left content boundary to the right content boundary.

Do NOT create an unnecessarily narrow text column.

Do NOT make the paragraph full browser width outside the main container.

Instead:

```text
┌──────────────────────────────────────────────────────────────┐
│ TITLE                                                        │
│                                                              │
│ Full-width introductory paragraph                            │
│ extending across the available hero/content width.          │
│                                                              │
│ metadata / badges                                            │
└──────────────────────────────────────────────────────────────┘
```

Maintain comfortable readable line length.

Do not make the text touch the edges.

Use appropriate:

- width
- max-width
- padding
- line-height
- spacing

The result should feel intentional and balanced.

---

# 5. PRIMARY FIX #3 — ANIMATION OVERLAPPING

The current Interactive Animation section has visual elements and text overlapping each other.

This must be fixed professionally.

## Main objective

Every visual element must occupy a predictable visual layer.

Text must remain readable.

Labels must not disappear behind SVG objects.

SVG objects must not unexpectedly cover:

- captions
- formulas
- labels
- debug information
- controls
- status information

Do NOT simply reduce the animation size to hide the problem.

Fix the underlying layering/layout system.

---

# 6. PROPER Z-INDEX / LAYER ARCHITECTURE

Use an intentional layering architecture.

For example:

```text
Animation container
│
├── Background layer
│
├── SVG visualization
│
├── SVG effects / trails
│
├── SVG objects
│
├── SVG labels
│
├── Formula overlay
│
├── Debug overlay
│
├── Caption layer
│
└── Controls layer
```

Use CSS positioning and `z-index` where appropriate.

Example conceptual structure:

```css
.animation-stage {
    position: relative;
}

.animation-svg {
    position: relative;
    z-index: 1;
}

.animation-labels {
    position: absolute;
    z-index: 10;
}

.animation-formula {
    position: absolute;
    z-index: 20;
}

.animation-debug {
    position: absolute;
    z-index: 30;
}

.animation-caption {
    position: relative;
    z-index: 40;
}

.animation-controls {
    position: relative;
    z-index: 50;
}
```

Do not blindly copy this exact implementation.

Use the architecture that best fits the existing application.

### Critical rule

Text should never become unreadable merely because an SVG object passes through the same region.

If necessary:

- move labels dynamically
- use label backgrounds
- use subtle backdrop blur
- use semi-transparent panels
- adjust SVG layer ordering
- use `pointer-events`
- use `z-index`
- use collision-aware positioning

The final result must remain readable during the entire animation.

---

# 7. MULTI-LINE ANIMATION IS ALLOWED AND ENCOURAGED

Do NOT force everything into one horizontal animation line.

If a concept is easier to understand using multiple visual rows/lines, use them.

For example:

```text
Code execution
      ↓
Variable calculation
      ↓
Mathematical transformation
      ↓
Coordinate transformation
      ↓
Robot state
```

or:

```text
Source Code        Mathematical Model
     │                    │
     └──────────┬─────────┘
                ↓
          System State
                ↓
          Robot Behavior
```

Multi-line animation is completely acceptable.

In fact, use multiple visual regions when it improves understanding.

The objective is:

**clarity > compactness**

---

# 8. ANIMATION MUST TEACH, NOT DECORATE

Every animation should communicate an actual concept from the analyzed code.

Do not create animation merely because the page has an animation section.

The user should understand:

```text
Source Code
     ↓
Variable
     ↓
Calculation
     ↓
Mathematical Meaning
     ↓
System State
     ↓
Robot Behavior
```

Whenever possible, animate this causal relationship.

---

# 9. PLAY / SLOW / FAST / PAUSE / STOP CONTROLS

The animation controls currently need improvement.

Use proper professional icons.

Required controls:

- Play
- Slow
- Fast
- Pause
- Stop

## IMPORTANT

Use actual iconography.

Do NOT use emoji characters.

Do NOT use textual substitutes such as:

```text
▶ Play
⏸ Pause
■ Stop
```

when a proper icon can be used.

Use one of:

- inline SVG icons
- an existing icon library already available in the project
- a lightweight icon implementation
- professionally designed CSS/SVG icons

If using external icon resources is appropriate and safe, use them.

However, prefer self-contained inline SVG icons where practical.

### Icon requirements

Icons must:

- be visually consistent
- have consistent dimensions
- align properly
- have hover states
- have active states
- have disabled states where appropriate
- include accessible labels/tooltips
- remain usable on mobile
- not introduce emojis

Suggested semantic icon appearance:

```text
[ Play ] [ Slow ] [ Fast ] [ Pause ] [ Stop ]
```

but visually represented primarily through icons.

Do not make the buttons oversized.

---

# 10. ANIMATION SPEED BEHAVIOR

The speed controls must actually work.

## Slow

Slow the animation to approximately:

```text
50% of normal speed
```

## Fast

Increase the animation speed by approximately:

```text
50%
```

## Play

Resume/start animation.

## Pause

Freeze the current animation state.

## Stop

Return the animation to its initial state.

The state must reset consistently.

Avoid creating separate duplicated animation engines for each button.

Use one coherent animation state machine.

---

# 11. ANIMATION STATE MACHINE

Where practical, structure animation around a clear state model.

For example:

```javascript
{
    isPlaying,
    isPaused,
    speed,
    currentStep,
    progress
}
```

The exact implementation may differ.

The important requirement is that:

- Play
- Pause
- Stop
- Slow
- Fast

all operate on the same animation state.

Do not create inconsistent timers that fight each other.

Avoid:

- duplicate `requestAnimationFrame` loops
- runaway intervals
- multiple simultaneous animation loops
- memory leaks
- controls becoming desynchronized

---

# 12. NEW MAJOR FEATURE — FINAL COMPLETE EXECUTION ANIMATION

Add a **final comprehensive animation at the bottom of the page**.

This is an important educational feature.

The purpose is to show the **entire code execution from beginning to end**.

The user should be able to watch:

```text
Complete Source Code
        ↓
Line 1
        ↓
Line 2
        ↓
Line 3
        ↓
...
        ↓
Final line
        ↓
Final system state
```

while simultaneously seeing what happens inside the real system/robot.

---

# 13. FINAL ANIMATION — COMPLETE CODE + EXECUTION + ROBOT

At the bottom of the analysis page, create a dedicated section such as:

```text
Complete Execution — Code → Debug → Robot
```

or another professional English title.

Do NOT use a Bangla subtitle in the title.

The final animation should combine three major views.

## VIEW A — COMPLETE SOURCE CODE

Show the relevant complete source code in a code panel.

Use the existing source code exactly.

Do not alter it.

The current executing line should be visually highlighted.

Example:

```text
01 | import ...
02 | import ...
03 |
04 | offset = ...
05 | ...
```

When execution reaches line 4:

```text
04 | offset = ...
```

highlight line 4.

Then move to:

```text
05 | ...
```

and so on.

The code highlight must correspond to the actual source line numbers.

---

# 14. FINAL ANIMATION — LINE-BY-LINE EXECUTION

The animation must execute conceptually **line by line**.

For each important line:

1. Highlight the original source line.
2. Show the relevant variables.
3. Show their current values.
4. Show the mathematical calculation if applicable.
5. Show the resulting state.
6. Show what happens in the robot/system visualization.
7. Update the explanation/caption.

Example:

```text
SOURCE

Line 42
offset = calculate_offset(...)
```

Then:

```text
DEBUG

offset
0.023 rad
```

Then:

```text
SYSTEM

Joint 2 offset updated
```

Then visually show the robot state changing.

---

# 15. LIVE DEBUG PANEL

The final execution animation must include a live debugging panel.

Show values that are actually meaningful for the analyzed code.

Examples:

```text
DEBUG

currentLine: 42
joint: 2
angle: 1.247 rad
offset: 0.023 rad
position.x: 0.412 m
position.y: 0.182 m
position.z: 0.305 m
status: updating
```

These are examples only.

DO NOT invent variables that do not exist in the source.

Use values derived from the actual code whenever possible.

If the source code does not expose a runtime value, clearly label the value as:

```text
Conceptual / illustrative
```

rather than pretending it is actual runtime output.

---

# 16. DEBUG VALUES MUST BE EDUCATIONAL

Do not merely display random numbers.

Every displayed value should answer:

**What value is this?**

**Where did it come from?**

**Why does it matter?**

**What does changing it affect?**

For example:

```text
camera_x
      ↓
coordinate transform
      ↓
robot_x
      ↓
joint/control calculation
      ↓
robot movement
```

The user should understand the data flow.

---

# 17. LIVE CODE → DEBUG → ROBOT CONNECTION

This is one of the most important requirements.

When a source-code line executes:

### The code panel changes

↓

### The debug values change

↓

### The mathematical representation changes

↓

### The visual system/robot changes

↓

### The caption explains the consequence

These should happen as one coherent event.

The animation should visually demonstrate causality.

---

# 18. FINAL ANIMATION TIMELINE

Build the final animation as a sequence of meaningful execution steps.

Conceptually:

```text
STEP 01
Initialize system
       ↓
STEP 02
Load configuration
       ↓
STEP 03
Read calibration values
       ↓
STEP 04
Calculate transformation
       ↓
STEP 05
Apply offset
       ↓
STEP 06
Update robot state
       ↓
STEP 07
Final result
```

The exact steps must be determined from the actual analyzed source code.

Do NOT invent execution steps that do not correspond to the source.

---

# 19. FINAL ANIMATION — ROBOT VISUALIZATION

Because this is a robotics-oriented analysis, the final animation should show the physical/system consequence wherever the source code supports it.

For example, if the source affects:

- robot joints
- arm position
- calibration offset
- camera position
- coordinate frames
- motor commands
- sensors

show those changes visually.

Possible visualization:

```text
                 End Effector
                      ●
                     /
                    /
               Joint 2
                  ●
                 /
                /
           Joint 1
             ●
             |
             |
           Base
```

But create a polished domain-aware visualization rather than a crude diagram.

Use:

- SVG
- gradients
- subtle depth
- coordinate frames
- labels
- motion
- state indicators
- smooth transitions

where appropriate.

---

# 20. FINAL RESULT STATE

At the end of the final animation, show:

```text
EXECUTION COMPLETE
```

Then present the final state.

For example:

```text
Final Variables
Final Position
Final Joint State
Final Calibration State
Final System State
```

Only show values that are supported by the source.

---

# 21. FINAL ANIMATION CONTROLS

The final complete-execution animation must also have:

- Play
- Slow
- Fast
- Pause
- Stop

Use the same professional icon system.

The controls should operate correctly.

The user must be able to:

1. Play from the beginning.
2. Pause at any execution line.
3. Continue.
4. Slow the execution.
5. Speed it up.
6. Stop and reset.
7. Replay the entire execution.

---

# 22. STEP INDICATOR

Add a compact execution progress indicator.

For example:

```text
STEP 07 / 24
```

or:

```text
LINE 42 / 87
```

or both.

The user should know where they are in the execution.

Do not make this visually overwhelming.

---

# 23. EXECUTION CAPTION

The final animation should have a live Bangla caption.

Example:

```text
এই line-এ calibration offset calculate করা হচ্ছে।
```

Then:

```text
এই value-টি পরবর্তী transformation-এর input হিসেবে ব্যবহৃত হবে।
```

Then:

```text
Calculated offset ব্যবহার করে Robot Joint-এর target state update হচ্ছে।
```

Use Bangla explanatory prose.

Keep technical terminology in English.

---

# 24. FORMULA SYNCHRONIZATION

If a code step involves mathematics, synchronize the mathematical representation with execution.

For example:

```text
CODE
X = ...

DEBUG
px = ...
cx = ...
Z  = ...
fx = ...

MATH
X = ((px - cx) × Z) / fx

RESULT
X = ...
```

Then show the corresponding physical transformation.

The user should see:

```text
CODE
  ↓
VALUES
  ↓
FORMULA
  ↓
RESULT
  ↓
ROBOT
```

---

# 25. DO NOT FABRICATE RUNTIME EXECUTION

This is critical.

If the HTML is only a static educational visualization and cannot truly execute the source code:

**DO NOT pretend that it is executing the real source code.**

Instead clearly communicate that the final animation is a:

```text
Conceptual execution visualization
```

or:

```text
Step-by-step execution simulation
```

when appropriate.

Use real values from the source/configuration where available.

If values are illustrative, label them accordingly.

Never create fake runtime logs and present them as actual execution output.

---

# 26. PRESERVE EXISTING ANALYSIS CONTENT

Do NOT remove existing:

- Parts
- explanations
- mathematical explanations
- real-world system explanations
- animations
- source code
- navigation
- metadata
- educational content

unless a change is absolutely necessary to implement the requested fixes.

Improve rather than destroy.

If an existing animation already works, preserve its educational content while fixing:

- layering
- overlap
- readability
- controls
- timing
- responsiveness

---

# 27. DO NOT REDUCE ANALYSIS DEPTH

Do NOT solve layout problems by deleting content.

Do NOT:

- shorten explanations
- remove code
- remove math
- remove animations
- remove debug information
- reduce Parts
- replace detailed content with summaries

The existing educational depth must remain intact.

---

# 28. RESPONSIVE ANIMATION

The animation must work on:

- large desktop
- laptop
- tablet
- mobile

On smaller screens:

- avoid text collisions
- stack visual regions where appropriate
- allow multi-line layouts
- make the SVG responsive
- keep controls accessible
- allow code panels to scroll horizontally
- prevent debug panels from covering important content

If the desktop animation uses:

```text
Code | Robot | Debug
```

a mobile layout may use:

```text
Code
↓
Debug
↓
Robot
```

This is acceptable and preferred over overlap.

---

# 29. PROFESSIONAL Z-INDEX POLICY

Do not randomly increase z-index values until things appear correct.

Establish a coherent stacking context.

Use a documented hierarchy such as:

```text
0   background
10  SVG
20  SVG objects
30  SVG labels
40  overlays
50  formulas
60  debug
70  captions
80  controls
90  modal/tooltips
```

The exact values can differ.

The important point is intentional layering.

Avoid unnecessary extreme values such as:

```css
z-index: 999999999;
```

unless genuinely necessary.

---

# 30. TEXT READABILITY DURING ANIMATION

Text must remain readable even while objects move underneath or nearby.

If an annotation sits over the SVG:

Use appropriate techniques such as:

- background panel
- translucent backdrop
- backdrop blur
- text shadow
- dynamic positioning
- SVG text background
- HTML overlay

Do not allow:

```text
Robot arm
   ↓
[arm visually covers the text]
```

The explanatory text always wins in readability.

---

# 31. ICON SYSTEM — NO EMOJIS

Absolutely no emoji characters.

Do not use:

- emoji Play icons
- emoji Stop icons
- emoji Robot icons
- emoji arrows
- emoji status indicators

Use professional SVG icons.

The interface should look like an engineering application.

---

# 32. MAINTAIN EXISTING VISUAL LANGUAGE

The existing page already has a dark engineering aesthetic.

Preserve the overall visual identity.

Improve:

- spacing
- hierarchy
- alignment
- typography
- animation clarity
- control design
- layering

Do not completely redesign the visual identity unless required.

Avoid excessive gradients, glowing effects, or decorative elements.

Professional > flashy.

---

# 33. BANGla / ENGLISH LANGUAGE RULE

Keep the established language architecture.

### Explanatory prose

Bangla.

### Technical terminology

English.

Examples:

```text
Camera-র Coordinate System
```

```text
Function-টি এই value return করছে।
```

```text
Matrix-এর এই elementটি transformation-এর জন্য ব্যবহৃত হচ্ছে।
```

Do not transliterate common technical terms into Bangla script.

### Titles

Keep major UI titles in English unless the existing design explicitly requires otherwise.

In particular:

```text
01. arm calibration
```

must remain English.

---

# 34. CODE DISPLAY FIDELITY

The source code displayed in the HTML must remain exactly as originally represented.

Preserve:

- indentation
- line breaks
- comments
- punctuation
- commands
- paths
- flags
- variable names
- function names
- formulas
- ordering
- blank lines

If you need to highlight the currently executing line, do it through presentation-layer CSS.

Do NOT insert HTML markup into the source-code string itself.

---

# 35. LINE NUMBERS

Line numbers must correspond to the actual source.

Do not renumber code simply because it is displayed inside a Part.

The final execution animation must also reference actual source line numbers.

Example:

```text
Line 42
```

must actually correspond to source line 42.

---

# 36. ANIMATION PERFORMANCE

Use efficient animation techniques.

Prefer:

- `requestAnimationFrame`
- CSS transforms
- SVG transforms
- opacity
- GPU-friendly properties

Avoid excessive:

- DOM creation/destruction
- layout thrashing
- forced synchronous layout
- repeated expensive calculations
- unnecessary timers

The animation should remain smooth.

---

# 37. ACCESSIBILITY

Controls must have:

- accessible labels
- title/tooltips where appropriate
- keyboard accessibility
- visible focus state

For example:

```html
<button aria-label="Play animation">
```

Do not rely only on visual icons.

---

# 38. ERROR RESILIENCE

If one animation fails, the rest of the application should remain functional.

Avoid a single animation exception breaking:

- navigation
- sidebar
- other Parts
- other animations
- final execution animation

Use defensive JavaScript where appropriate.

---

# 39. BROWSER COMPATIBILITY

The resulting HTML must work when opened directly in a modern browser.

Verify:

- no JavaScript syntax errors
- no broken DOM references
- no missing animation handlers
- no broken buttons
- no broken navigation
- no overlapping UI
- no console errors caused by your changes

---

# 40. VALIDATION — MANDATORY

After editing the HTML, inspect the result carefully.

Perform a complete QA pass.

Check:

### Title

```text
01. arm calibration
```

Correct.

No Bangla subtitle after the title.

### Hero paragraph

Uses the full available hero/content width.

### Existing Parts

Still present.

### Sidebar

Still functional.

### Navigation

Still functional.

### Code

Unchanged.

### Line numbers

Correct.

### Explanations

Still present.

### Math

Still present where applicable.

### Robot/System sections

Still present.

### Existing animations

Still functional.

### Animation controls

Play works.

Slow works.

Fast works.

Pause works.

Stop works.

### Icons

Professional SVG/iconography.

No emoji.

### Animation layering

No text/object collisions.

### Multi-line layouts

Work correctly.

### Final animation

Exists at the bottom.

### Final animation

Shows:

```text
Source Code
+
Current Line
+
Debug Values
+
Mathematical State
+
Robot/System State
+
Live Caption
```

### Final animation controls

Play / Slow / Fast / Pause / Stop all work.

### Reset

Stop returns everything to the initial state.

### Responsive

Desktop works.

Mobile works.

### Console

No new JavaScript errors.

---

# 41. VISUAL QA — IMPORTANT

Do not rely only on reading the HTML source.

Actually inspect/render the page if the available environment supports browser-based testing.

Pay special attention to:

1. Hero title.
2. Intro paragraph width.
3. First animation.
4. Animation labels.
5. Formula overlays.
6. Debug overlays.
7. Animation controls.
8. Multi-line animation.
9. Final execution animation.
10. Mobile layout.

If browser automation is available, use it.

Take screenshots at useful viewport sizes if necessary.

Inspect the screenshots for:

- clipping
- overflow
- overlap
- unreadable text
- incorrect z-index
- misaligned controls
- excessive empty space
- broken responsive behavior

Fix problems you discover.

---

# 42. DO NOT STOP AT THE FIRST SUCCESSFUL BUILD

A technically valid HTML file is not enough.

The goal is:

**functionally correct + visually polished + educationally clear.**

If something technically works but looks poor, improve it.

If an animation runs but text overlaps, fix it.

If controls work but icons look amateurish, improve them.

If the final animation exists but does not clearly connect code → debug → robot, improve it.

---

# 43. DO NOT REGENERATE CONTENT UNNECESSARILY

This is a refinement task.

Do not regenerate all analysis text.

Do not rewrite the entire `PARTS` array.

Do not rewrite source code.

Do not rebuild the application from scratch.

Preserve the existing content and architecture wherever practical.

Make targeted, high-quality changes.

---

# 44. FINAL QUALITY BAR

The final HTML should feel like something produced by a senior engineering/product team.

It should communicate:

```text
Professional
Precise
Technical
Educational
Interactive
Polished
Readable
Robotics-focused
```

It must NOT feel:

```text
AI-generated
Overdecorated
Cluttered
Toy-like
Randomly animated
Visually overlapping
```

---

# 45. FINAL EXECUTION MODEL

The final experience should conceptually allow the user to understand:

```text
                    SOURCE CODE
                         │
                         ▼
                  CURRENT LINE
                         │
                         ▼
                  DEBUG VALUES
                         │
                         ▼
                 MATHEMATICAL STEP
                         │
                         ▼
                  SYSTEM STATE
                         │
                         ▼
                  ROBOT BEHAVIOR
                         │
                         ▼
                    FINAL RESULT
```

This is the central educational objective of the new final animation.

---

# 46. HARD CONSTRAINTS

NEVER:

- modify the analyzed source code
- invent source-code behavior
- fabricate runtime values as real execution
- remove existing analysis content
- remove existing Parts
- remove useful existing animations
- use emoji icons
- allow text to disappear behind SVG elements
- leave animation controls non-functional
- create overlapping animation layers
- replace detailed analysis with generic text
- introduce placeholder content
- use `...` to represent omitted source code
- silently change formulas
- silently correct the original implementation

---

# 47. FINAL INSTRUCTION TO CLAUDE CODE

Do the work directly in the existing project.

Do not merely tell me what should be changed.

Do not give me a proposed solution without implementing it.

Do not stop after analysis.

Do not provide a plan instead of making the changes.

Inspect the existing HTML, modify it carefully, validate it, and leave the improved HTML ready to open in a browser.

Again:

**THE ANALYZED SOURCE CODE MUST NOT CHANGE.**

Only the visualization/application layer may be improved.

The final result must include all requested fixes:

1. Remove the Bangla subtitle from:

```text
01. arm calibration
```

2. Make the introductory paragraph use the full available hero/content width.

3. Fix animation overlap.

4. Implement a proper animation stacking/layering system.

5. Use Z-index and/or appropriate SVG/HTML layering so explanatory text remains readable.

6. Support professional multi-line animation layouts where useful.

7. Replace Play / Slow / Fast / Pause / Stop text/emoji representations with professional icons.

8. Ensure all five controls actually work.

9. Add a final comprehensive animation at the bottom.

10. The final animation must connect:

```text
complete source code
→ current executing line
→ debug values
→ mathematical calculation
→ system/robot behavior
→ final state
```

11. Highlight the actual source-code line currently being simulated.

12. Show meaningful live debug values derived from the actual analyzed code whenever possible.

13. Clearly label conceptual/illustrative values if true runtime execution is not possible.

14. Synchronize code, debug, formula, robot visualization, and Bangla caption.

15. Make the final animation replayable and controllable.

16. Validate the complete page after making the changes.

17. Preserve all existing educational content and source-code fidelity.

**Do not change the analyzed source code under any circumstances.**

Now inspect the existing implementation and perform the refinement.

---

# 48. ADDITIONAL FIX — COMPLETE EXECUTION MUST EXPLAIN AND EXECUTE LINE BY LINE

This is a mandatory refinement to the **Complete Execution — Code → Debug → Robot** experience.

The final execution animation must NOT merely highlight a sequence of lines while showing a general debug panel and robot animation.

It must teach and simulate the execution **properly, line by line**.

## 48.1 LINE-BY-LINE EXECUTION IS THE PRIMARY MODEL

For every executable or educationally meaningful source line:

1. Identify the exact original source line number.
2. Highlight that exact line in the complete source-code panel.
3. Explain what that line is doing in Bangla.
4. Identify the variables affected by that line.
5. Show the value of each relevant variable **before** execution when useful.
6. Show the operation/calculation performed by the line.
7. Show the value **after** execution.
8. Explain where the value came from.
9. Explain why the value matters.
10. Show the resulting system/robot state.
11. Update the mathematical representation when mathematics is involved.
12. Update the live Bangla caption.
13. Move to the next source line only after the current line's effect has been clearly represented.

The experience must feel like a debugger combined with a technical teacher.

Do not jump from:

```text
Line 41
↓
Line 47
↓
Line 52
```

without explaining what happened at lines 42–46 when those lines are relevant to execution.

Do not compress several meaningful executable lines into one generic animation step merely to make the animation shorter.

If several consecutive lines genuinely form one indivisible operation, they may be presented as one logical group, but the individual source lines and their values must still be identifiable.

---

# 49. COMPLETE EXECUTION — FIRST ROW MUST BE CODE + DEBUG

The layout of the **Complete Execution — Code → Debug → Robot** section must prioritize execution clarity.

The first visual row should contain:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ COMPLETE SOURCE CODE              │ LIVE DEBUG                      │
│                                   │                                 │
│ 41 | value = ...                  │ value        = ...              │
│ 42 | result = ...                 │ result       = ...              │
│ 43 | ...                          │ currentLine = 42                │
│                                   │ status       = executing        │
└─────────────────────────────────────────────────────────────────────┘
```

The source-code panel and debug panel are therefore the primary execution row.

The currently executing source line must be visibly highlighted.

The debug panel must update in synchronization with that highlighted line.

The debug panel must show only variables/values that are meaningful for the current source line and the analyzed source.

Do NOT fill the debug panel with arbitrary variables merely to make the interface look rich.

---

# 50. COMPLETE EXECUTION — ANIMATION MAY APPEAR IN A ROW BELOW CODE + DEBUG

The robot/system visualization and related animation do NOT need to occupy the same row as the source code and debug panel.

In fact, when this improves clarity, the preferred layout is:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    SOURCE CODE + DEBUG ROW                          │
│                                                                     │
│  Complete source code              Current variables / values       │
│  Current line highlighted          Calculation / state              │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    ANIMATION / SYSTEM ROW                            │
│                                                                     │
│              Robot / Camera / Coordinate / System Visualization     │
│                                                                     │
│              Visual state changes caused by current line            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    EXPLANATION / FORMULA ROW                         │
│                                                                     │
│ Bangla explanation     Mathematical relationship / result            │
└─────────────────────────────────────────────────────────────────────┘
```

This multi-row architecture is explicitly preferred over forcing Code, Debug, Robot, Formula, Caption, and Controls into one cramped horizontal row.

The exact arrangement may vary according to the source code and available screen width, but the priority order is:

```text
Code
+
Debug
↓
Animation / System State
↓
Explanation / Formula / Result
```

The animation being placed in the row below the code/debug row is fully acceptable and should be used whenever it improves readability.

---

# 51. COMPLETE EXECUTION — CODE AND DEBUG MUST STAY SYNCHRONIZED

At every execution step, these elements must represent the same moment in the conceptual execution:

```text
CURRENT SOURCE LINE
        ↓
CURRENT VARIABLES / VALUES
        ↓
CURRENT CALCULATION
        ↓
CURRENT SYSTEM STATE
        ↓
CURRENT ROBOT / VISUAL STATE
        ↓
CURRENT EXPLANATION
```

Never show a source line from one execution step while the debug panel or robot visualization still represents a previous or later step.

The transition should happen as one coherent state update.

For example:

```text
Line 42 highlighted
        ↓
debug values for line 42
        ↓
line 42 calculation shown
        ↓
result of line 42 shown
        ↓
robot/system state changes because of line 42
        ↓
Bangla explanation describes line 42
```

Then, and only then:

```text
Line 43 highlighted
```

---

# 52. COMPLETE EXECUTION — BEFORE / OPERATION / AFTER DEBUG

When a line changes a meaningful variable, make the state transition educationally visible.

Use a structure such as:

```text
BEFORE

offset = 0.000 rad

        ↓

LINE 42
offset = calculate_offset(...)

        ↓

CALCULATION

calculate_offset(...) → 0.023 rad

        ↓

AFTER

offset = 0.023 rad
```

For mathematical operations, use:

```text
INPUT VALUES
        ↓
FORMULA
        ↓
SUBSTITUTION
        ↓
CALCULATION
        ↓
RESULT
```

This should be shown only when supported by the actual source code.

If the source does not expose enough information to calculate a real value, clearly mark the state as:

```text
Conceptual / illustrative
```

Never present invented values as real runtime values.

---

# 53. COMPLETE EXECUTION — LINE-BY-LINE EXPLANATION MUST BE VISIBLE

The final execution animation must not depend on the user remembering information from earlier Part explanations.

At each meaningful execution step, show a concise but technically accurate Bangla explanation connected directly to the current line.

The explanation should answer, where applicable:

- এই line-টি কী করছে?
- কোন Variable read/write হচ্ছে?
- বর্তমান value কোথা থেকে এসেছে?
- calculation কীভাবে হচ্ছে?
- এই value কেন দরকার?
- পরের line বা operation-এর উপর এর প্রভাব কী?
- Robot/System-এর কোন state পরিবর্তিত হচ্ছে?
- ভুল value হলে কী consequence হতে পারে?

Do not merely display:

```text
এই line-এ calculation করা হচ্ছে।
```

Instead explain the actual calculation and data flow supported by the source.

The objective is **line-by-line teaching + line-by-line execution simulation**, not merely animated code highlighting.

---

# 54. COMPLETE EXECUTION — SKIP NON-EXECUTABLE LINES INTELLIGENTLY, NEVER HIDE THEM

Not every source line necessarily performs a runtime operation.

For imports, comments, blank lines, declarations, function definitions, or other non-executing structural lines:

- Keep them visible in the complete source code.
- Preserve their real source line numbers.
- Do not pretend they perform runtime calculations if they do not.
- Explain their role when educationally meaningful.
- Move efficiently through genuinely non-executable/structural lines without falsely inventing state changes.

The animation must distinguish between:

```text
Structural / declarative line
```

and:

```text
Executable state-changing line
```

without altering the original source code.

---

# 55. COMPLETE EXECUTION — ACTUAL SOURCE ORDER IS MANDATORY

Execution order must follow the actual source and actual control flow as far as the visualization can faithfully determine it.

Do not create an aesthetically pleasing sequence that contradicts the source.

Respect:

- sequential execution
- conditions
- loops
- function calls
- return flow
- variable dependencies
- calculations
- state updates
- relevant branches

If true runtime control flow cannot be determined without actually executing the source, present the result explicitly as a:

```text
Step-by-step execution simulation
```

rather than claiming real runtime execution.

---

# 56. FULL-WIDTH HTML / CONTENT CONTAINER FIX

The complete HTML application should use the available browser width much more effectively.

The main application content must not appear unnecessarily narrow inside a large empty browser area.

## Required behavior

Use a full-width application shell with a professional maximum-width strategy.

The layout should behave conceptually like:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │                         MAIN CONTENT                              │
│         │                                                                   │
│         │ TITLE                                                             │
│         │                                                                   │
│         │ FULL-WIDTH INTRODUCTORY CONTENT                                   │
│         │                                                                   │
│         │ CODE                                                              │
│         │                                                                   │
│         │ EXPLANATION                                                       │
│         │                                                                   │
│         │ MATH                                                              │
│         │                                                                   │
│         │ ROBOT / ANIMATION                                                 │
│         │                                                                   │
│         │ COMPLETE EXECUTION — CODE → DEBUG → ROBOT                         │
│         │                                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

The content should fill the available main-content region rather than being constrained to a small centered column.

## Full-width requirements

- The main content area should use the full width available beside the sidebar.
- Major cards should expand to the available content width.
- The hero/title container should use the available width.
- The introductory paragraph should use the full available hero/content width.
- Code cards should use the available width.
- Explanation cards should use the available width.
- Math sections should use the available width.
- Robot/animation sections should use the available width.
- The final Complete Execution section should use the available width.
- Avoid arbitrary narrow `max-width` values that leave large unused horizontal space.
- Do not make text touch the viewport edges; preserve sensible internal padding.
- A reasonable global page gutter is preferred over an unnecessarily narrow content column.

Use responsive sizing so that the application feels full-width on large desktop displays while remaining readable on smaller screens.

---

# 57. FULL-WIDTH DOES NOT MEAN UNREADABLE

Using the full available width does NOT mean stretching individual paragraphs into extremely long unreadable lines.

Use the available width for the application/card/container architecture while applying sensible internal readability rules.

For example:

```text
Browser width
    ↓
Sidebar + Main Content
    ↓
Full-width cards
    ↓
Readable internal text blocks
```

Do not solve the previous narrow-layout problem by creating excessively long prose lines.

Use:

- internal padding
- responsive grid/flex layouts
- sensible text measure where necessary
- full-width cards
- full-width code/visualization regions
- responsive stacking

The application should feel spacious rather than either cramped or excessively narrow.

---

# 58. FINAL EXECUTION — PREFERRED DESKTOP LAYOUT

For large screens, prefer a layout similar to:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE EXECUTION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  COMPLETE SOURCE CODE                    LIVE DEBUG                         │
│  ┌───────────────────────────────┐      ┌───────────────────────────────┐  │
│  │ 01 | ...                      │      │ currentLine: 42                │  │
│  │ 02 | ...                      │      │ variableA: ...                 │  │
│  │ 03 | ...                      │      │ variableB: ...                 │  │
│  │ 42 | CURRENT LINE             │      │ result: ...                    │  │
│  │ 43 | ...                      │      │ status: executing              │  │
│  └───────────────────────────────┘      └───────────────────────────────┘  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         ROBOT / SYSTEM ANIMATION                            │
│                                                                             │
│                    [visual state changes here]                              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         FORMULA / RESULT                                    │
│                                                                             │
│                         X = ...                                              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         LIVE EXPLANATION                                    │
│                                                                             │
│                  বর্তমান line-এ ...                                          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         CONTROLS                                             │
│                    Play Slow Fast Pause Stop                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

This is a preferred structure, not a requirement to copy the exact visual implementation.

The central rule is:

**Code + Debug first; Animation below.**

---

# 59. FINAL EXECUTION — MOBILE LAYOUT

On mobile, stack the same educational flow vertically:

```text
Complete Source Code
        ↓
Live Debug
        ↓
Animation / Robot
        ↓
Formula / Result
        ↓
Live Explanation
        ↓
Controls
```

Never force the desktop Code + Debug + Robot layout into a narrow mobile viewport.

Avoid overlap at all costs.

---

# 60. FINAL QA — ADDITIONAL EXECUTION CHECKS

Before final output, verify all of the following:

### Complete Execution

- [ ] Complete Execution exists at the bottom.
- [ ] The complete relevant source code is represented.
- [ ] Original source text is unchanged.
- [ ] Actual source line numbers are used.
- [ ] Current executing line is highlighted.
- [ ] Execution proceeds line by line.
- [ ] Every meaningful executable line has an educational explanation.
- [ ] Relevant variables are identified.
- [ ] Current values are shown.
- [ ] Before/operation/after state is shown when meaningful.
- [ ] Mathematical calculations are synchronized when applicable.
- [ ] Robot/System visualization reflects the current execution state.
- [ ] Bangla caption reflects the current execution state.
- [ ] Code and Debug occupy the primary first row on desktop.
- [ ] Animation may appear in the row below Code + Debug.
- [ ] Multi-row layout is used whenever it improves clarity.
- [ ] No unnecessary horizontal crowding exists.
- [ ] No SVG object covers the source code, debug values, formulas, captions, or controls.
- [ ] No fabricated runtime values are presented as real.
- [ ] Conceptual/illustrative values are explicitly labeled.
- [ ] Actual control flow is respected where determinable.
- [ ] Structural/non-executable lines are not falsely presented as state-changing operations.

### Full-width layout

- [ ] Main content uses the available width beside the sidebar.
- [ ] Hero content uses the available width.
- [ ] Introductory paragraph spans the full available hero/content container.
- [ ] Major cards are not unnecessarily narrow.
- [ ] Code cards use the available width.
- [ ] Animation uses the available width.
- [ ] Complete Execution uses the available width.
- [ ] Internal padding remains comfortable.
- [ ] Desktop does not leave excessive unused horizontal space.
- [ ] Mobile remains readable and stacked appropriately.

---

# 61. FINAL NON-NEGOTIABLE PRIORITY ORDER

When making implementation decisions, prioritize:

```text
SOURCE-CODE FIDELITY
        ↓
TECHNICAL ACCURACY
        ↓
LINE-BY-LINE EXECUTION CLARITY
        ↓
CODE + DEBUG SYNCHRONIZATION
        ↓
SYSTEM / ROBOT CAUSAL VISUALIZATION
        ↓
READABILITY
        ↓
RESPONSIVE FULL-WIDTH LAYOUT
        ↓
ANIMATION POLISH
        ↓
DECORATION
```

Never sacrifice source-code fidelity or educational clarity for visual effects.

The final application must make it immediately understandable:

```text
THIS LINE EXECUTES
        ↓
THESE VARIABLES HAVE THESE VALUES
        ↓
THIS CALCULATION HAPPENS
        ↓
THIS RESULT IS PRODUCED
        ↓
THIS SYSTEM/ROBOT STATE CHANGES
        ↓
THIS IS WHY IT MATTERS
```

That is the required behavior of the final **Complete Execution — Code → Debug → Robot** experience.

---

# 62. FINAL MASTER INSTRUCTION

Implement all requirements from this merged master prompt.

Do not omit any requirement from either source prompt.

Preserve the original analyzed source code exactly.

Preserve all existing educational content.

Perform surgical UI/UX and animation refinement rather than unnecessary regeneration.

Ensure the final Complete Execution animation genuinely teaches the code **line by line**, with **Code + Debug as the first row** and the **Robot/System animation allowed and encouraged in the row below**.

Ensure the complete HTML application uses the available browser width professionally, with the main content, cards, hero, code, animations, and Complete Execution section using the full available main-content region while retaining readable internal text widths.

The final result must be:

```text
Complete
Accurate
Line-by-Line
Synchronized
Interactive
Responsive
Full-Width
Readable
Professional
Robotics-Focused
```
