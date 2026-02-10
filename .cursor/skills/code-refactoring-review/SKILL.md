---
name: code-refactoring-review
description: Review code for refactoring opportunities focused on complexity simplification, code reduction, and clean code separation of responsibilities. Use when the user asks for a code review, refactoring suggestions, complexity analysis, or clean code recommendations.
---

# Code Refactoring Review

Analyze code and produce actionable refactoring recommendations across three pillars: complexity simplification, code reduction, and separation of responsibilities.

## Workflow

### Step 1: Scope Identification

Determine which files to review:

1. If the user specifies files or directories, use those.
2. Otherwise, check recent git changes: `git diff --name-only HEAD~5` or `git diff --stat`.
3. Prioritize files with the most churn or the largest size.
4. List the files you will review and confirm scope with the user if it exceeds 10 files.

### Step 2: Complexity Analysis

Read each file and evaluate against the three-pillar checklists below. Track every finding.

### Step 3: Refactoring Recommendations

For each finding:
1. Identify the specific refactoring technique from [REFACTORING-CATALOG.md](references/REFACTORING-CATALOG.md).
2. Assign a priority (CRITICAL / IMPORTANT / MINOR).
3. Estimate effort (Low / Medium / High).

### Step 4: Report Output

Present findings using the report template below, followed by the summary table.

---

## Three-Pillar Checklists

### Pillar 1: Complexity Simplification

Scan for these smells:

- [ ] **Deep nesting**: more than 3 levels of indentation (if/for/try stacked)
- [ ] **Long functions**: more than 30 lines of logic (exclude blank lines and comments)
- [ ] **Complex conditionals**: more than 3 boolean operators in a single expression
- [ ] **High cyclomatic complexity**: many branching paths through a function
- [ ] **Callback/promise chains**: deeply chained async operations without extraction
- [ ] **Overly generic abstractions**: parameterized code solving only one concrete case

### Pillar 2: Code Reduction

Scan for these smells:

- [ ] **Duplicated logic**: similar code blocks appearing in multiple locations
- [ ] **Dead code**: unused functions, imports, variables, or unreachable branches
- [ ] **Over-engineering**: interfaces/abstractions with a single implementation
- [ ] **Verbose idioms**: patterns replaceable by built-in language constructs
- [ ] **Redundant checks**: repeated null/error/type checks already guaranteed by context
- [ ] **Extractable boilerplate**: repeated setup/teardown/logging that belongs in a helper

### Pillar 3: Separation of Responsibilities

Scan for these smells:

- [ ] **God class/module**: file handles more than one clear responsibility
- [ ] **Mixed abstraction levels**: high-level orchestration mixed with low-level detail in one function
- [ ] **Interleaved concerns**: business logic mixed with I/O, formatting, or infrastructure
- [ ] **Tight coupling**: module depends on internal details of an unrelated module
- [ ] **Missing domain boundaries**: no clear separation between layers (e.g., API, service, data)
- [ ] **Misplaced utilities**: helper/utility functions embedded inside domain classes

---

## Finding Template

Use this format for each finding:

```
### [PRIORITY] Finding Title

- **Location**: path/to/file.ext:line_range
- **Pillar**: Complexity | Reduction | Separation
- **Smell**: Name of the specific smell detected
- **Current**: Brief description of the problem (2-3 sentences max)
- **Suggested Refactoring**: Specific technique (reference the catalog)
- **Impact**: What improves -- readability, testability, maintainability, or performance
- **Effort**: Low / Medium / High
```

Priority levels:

| Priority | Meaning | Criteria |
|----------|---------|----------|
| CRITICAL | Structural issue blocking maintainability | God classes, high coupling, duplicated core logic |
| IMPORTANT | Significant improvement opportunity | Long methods, mixed concerns, verbose patterns |
| MINOR | Nice-to-have cleanup | Small dead code, minor idiom improvements |

---

## Summary Table

After all findings, output this summary:

```
## Refactoring Summary

| # | Priority | Pillar | Finding | File | Effort |
|---|----------|--------|---------|------|--------|
| 1 | CRITICAL | Separation | God class detected | path/file.ext | High |
| 2 | IMPORTANT | Complexity | Deep nesting in handler | path/file.ext | Medium |
| ... | ... | ... | ... | ... | ... |

### Health Score: [A-F]

- A: 0 critical, 0-1 important findings -- clean codebase
- B: 0 critical, 2-3 important findings -- minor improvements needed
- C: 0-1 critical, 4+ important findings -- refactoring recommended
- D: 2-3 critical findings -- refactoring strongly recommended
- F: 4+ critical findings -- significant restructuring needed

### Top 3 Recommended Actions
1. [Most impactful refactoring to start with]
2. [Second priority]
3. [Third priority]
```

---

## Guidelines

- Be specific: always reference exact file paths, line numbers, and function/class names.
- Be actionable: every finding must include a concrete refactoring technique, not just "this is bad."
- Be proportional: do not flag single-line functions or trivial code. Focus on meaningful improvements.
- Respect existing patterns: if the codebase consistently uses a pattern, note it but do not flag it as a smell unless it causes real problems.
- Suggest incremental changes: prefer small, safe refactorings over large rewrites.
- For detailed refactoring techniques and before/after examples, see [references/REFACTORING-CATALOG.md](references/REFACTORING-CATALOG.md).
