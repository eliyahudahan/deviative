# Deviative — Engineering Insights

A record of what I learned building Deviative v1.1.
Written for future me, and for anyone reading the repo.

---

## 1. The Sign Convention Bug (v1.0 → v1.1)

### What happened

In v1.0, `compute_dcpa_tcpa` used:

    v_rel = v1 - v2

while positions were computed as:

    r = r2 - r1

### Why it was wrong

For approaching vessels, `r · v_rel` was positive → TCPA negative.
But the documented convention says: **TCPA > 0 means approaching.**

So the filter was selecting **receding** pairs that happened to be close —
not approaching pairs at risk of collision.

### The fix

    v_rel = v2 - v1   # consistent with r = r2 - r1

### Impact

| Metric            | Before (v1.0) | After (v1.1) |
|-------------------|---------------|--------------|
| Total anomalies   | 4,372         | 2,221        |
| Train rate        | 1.45%         | 1.38%        |
| Test rate         | 0.91%         | 0.95%        |
| Train/Test diff   | 0.54%         | 0.43%        |

Anomaly count dropped ~49% because the filter now correctly selects
**approaching** pairs.

### Lesson

A sign convention bug can hide in plain sight. The code ran, produced
results, and passed 37 tests. But the physics was inverted.

**Tests don't catch physics errors unless you write physics tests.**

---

## 2. Single Source of Truth

### What happened

Before v1.1, three functions defined "anomaly" differently:

| Function                    | Anomalies returned |
|-----------------------------|--------------------|
| `flag_anomalies_per_state`  | 4,372              |
| `sanity_check`              | 96,326             |
| `manual_inspection`         | (inconsistent)     |

Same question — three different answers.

### The fix

Created `get_anomaly_mask` as the **single source of truth**.
All other functions now delegate to it.

### Impact

After v1.1, all functions return the same count.

### Lesson

When the same business rule is implemented in multiple places,
**they will diverge.** Centralize the rule. Test it once.

---

## 3. The Anomaly Definition — 4 Conditions

An anomaly is a `moving` vessel pair that satisfies **all four**:

1. `DCPA < 0.1982 km` (198 m) — close closest-point-of-approach
2. `TCPA >= 0` — approaching (CPA in future)
3. `TCPA < 0.0293 h` (1.76 min) — imminent
4. `distance_km < 1.0` — currently close (guard)

### Why 4 conditions?

- **DCPA alone** → too permissive (96,326 anomalies)
- **+ TCPA range** → filters by time-to-CPA
- **+ distance_km** → filters by current proximity

The `distance_km` guard is a **documented heuristic**, not data-derived.
Without it: 96,326 anomalies. With it: 2,221. Ratio: **43×**.

### Lesson

Guard conditions are not "nice-to-have" — they turn a noisy signal
into an operational one.

---

## 4. row-wise vs vectorized

### The pattern

Every physics function exists in two versions:

- **row-wise** — clear, readable, slow
- **vectorized** — fast, less readable

### The test

`test_vectorized_matches_rowwise` runs both on the same data and compares
**row by row**. If they diverge, the test fails.

### Why this matters

Vectorized code is ~100× faster, but easy to get wrong (index math,
boundary conditions, NaN handling). **The comparison test is the safety net.**

### Lesson

When you optimize for speed, write a test that proves the fast version
produces the same result as the slow version.

---

## 5. Test Organization — unit/ vs integration/

### Structure

    tests/
    ├── unit/                    # isolated function tests
    │   ├── test_config.py       # constants
    │   ├── test_helpers.py      # haversine, pdist, merge
    │   ├── test_data_io.py      # COG/SOG diffs, radians
    │   ├── test_physics.py      # DCPA/TCPA, movement
    │   └── test_anomaly.py      # mask, flagging
    └── integration/             # end-to-end invariants
        └── test_pipeline.py     # 4 invariants

### Why split

- **Unit** — when something breaks, you know which function.
- **Integration** — when something breaks, you know it's the wiring.

### Lesson

The industry standard is `unit/` + `integration/`. It's not cosmetic —
it changes how you debug.

---

## 6. Test Count — Truth, Not Assumptions

### What happened

README said "41 unit tests". Actual count: 45.

### Why

The count was stale. 4 new tests were added but README was not updated.

### Fix

- Fixed `test_pipeline_reproducibility`: expected 3, not 2.
- Updated README to 45.
- Added a changelog entry (v1.2) documenting the split.

### Lesson

**Every number in the README must be computed, not assumed.**
If you change the test count, update the README in the same commit.

---

## 7. Fixtures — Dead Code

### What happened

`tests/conftest.py` defined 3 fixtures:

- `moving_anomaly`
- `moving_not_anomaly`
- `anchored_pair`

None were used. Tests build data inline via `_df()` helper methods.

### Decision

Deleted `conftest.py`. Dead code is technical debt.

### Lesson

"Keep it for later" is not a strategy. If it's not used, delete it.
If you need it later, write it later.

---

## 8. The pythonpath Issue

### What happened

`pytest` failed with `ModuleNotFoundError: No module named 'models'`.

### Why

pytest does not add the project root to `sys.path` automatically.

### Fix

Added to `pytest.ini`:

    [pytest]
    pythonpath = .

### Lesson

The official solution (`pythonpath = .`) is one line. A `conftest.py`
with `sys.path.insert` is a workaround. **Use the official solution.**

---

## 9. The 30-Minute Rule

### The rule

If stuck on a problem for more than 30 minutes, ask AI.

### Why

- After 30 minutes, frustration replaces thinking.
- AI provides a fresh perspective.
- But **AI gives a draft, not an answer** — you still verify.

### Lesson

Persistence is valuable only up to a point. Then it becomes stubbornness.

---

## 10. Documentation Standards

### What a good README contains

- **Intended Use** — what this is, and what it is not
- **Problem** — what question it answers
- **Method** — how
- **Data** — sources, counts, limitations
- **Results** — with computed numbers
- **Validation** — how we know it works
- **Known Uncertainties** — what we do not know
- **Changelog** — what changed, when, why

### Lesson

A README is not decoration. **It is the interface between you and the
reviewer.** If the README is wrong, the reviewer assumes the code is wrong.

---

## 11. Third-Party Privacy

### The rule

Default: publish nothing about third-party communications.

- No ticket numbers
- No names
- No status ("pending query")
- No mention in README, changelog, or social media

### Why

Attribution is public. Communication is private.

### Lesson

Attribution: "Data source: Energinet (Danish TSO)" — that's it.
Everything else stays private.

---

## 12. The Learning Framework (Nir Etzion's 3 Questions)

Before every task, answer three questions:

1. **What is the problem?**
2. **What are the principles of the solution?**
3. **How will I measure success?**

### Why

- Forces clarity before code.
- Prevents scope creep.
- Makes success measurable.

### Lesson

Three questions, five minutes. **Saves hours of rework.**

---

## Summary — 12 Lessons

1. Sign convention bugs hide in plain sight — write physics tests.
2. Single source of truth prevents divergence.
3. Guard conditions turn noise into signal.
4. Vectorized code needs a comparison test.
5. Unit vs integration is a debugging tool, not decoration.
6. Every number in the README must be computed.
7. Dead code is debt — delete it.
8. Use the official solution first, workaround second.
9. The 30-minute rule: persistence becomes stubbornness.
10. A README is the interface between you and the reviewer.
11. Third-party privacy: publish nothing.
12. Three questions before every task.

---

*Last updated: 2026-10-20*
