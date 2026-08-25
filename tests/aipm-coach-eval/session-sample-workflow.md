# Real Session To Eval Sample Workflow

This workflow closes the gap between a real AIPM Coach conversation and strict eval samples.

## 1. Record A Real Session

After AIPM Coach completes the full workflow through step 11, create a session draft JSON with the required fields documented in:

```text
coach-data/session-runs/README.md
```

Then run the required closing command:

```powershell
python plugins\aipm-coach\scripts\record_session_run.py --latest-draft --run-eval
```

This command validates and saves the session, converts it to an eval sample when possible, and refreshes strict eval. Every complete coach workflow should run it once.

The saved session lands in:

```text
coach-data/session-runs/<run_id>.json
```

If a sample for the same `eval_case_id` already exists, the command keeps the new session record and skips overwriting the existing sample unless `--force-sample` is passed.

## 2. Manual Fallback: Save A Session

If the closing command fails and you need to debug the individual step, validate and save directly:

```powershell
python plugins\aipm-coach\scripts\save_session_run.py --input path\to\draft-session.json
```

## 3. Manual Fallback: Convert Session To Eval Sample

Convert a saved session into the strict eval sample file:

```powershell
python tests\aipm-coach-eval\scripts\session_to_sample.py --session coach-data\session-runs\<run_id>.json
```

Or convert the newest saved session:

```powershell
python tests\aipm-coach-eval\scripts\session_to_sample.py --latest
```

The script writes:

```text
tests/aipm-coach-eval/samples/<eval_case_id>.txt
```

It refuses to overwrite an existing sample unless `--force` is passed.

## 4. Fixture Guard

The conversion script refuses to write a sample when the raw answer exactly matches any case JSON `sample_output`.

Rules:

- Do not use `sample_output` as a real answer.
- Do not rewrite, polish, or complete the answer before saving it.
- Use `full_raw_answer` whenever possible so the sample is the original AI Coach response.

## 5. Manual Fallback: Run Strict Eval

Run:

```powershell
python tests\aipm-coach-eval\run_eval.py
```

Strict mode still reads only:

```text
tests/aipm-coach-eval/samples/<case_id>.txt
```

If no real samples exist, the report remains `NOT_REAL_RUN_NO_REAL_SAMPLES`. If only some cases have real samples, the report remains partial and lists missing samples. Fixture smoke mode is still explicit:

```powershell
python tests\aipm-coach-eval\run_eval.py --allow-fixtures
```
