# How the `nginx-log-fix` Harbor Task Works

This document explains the `Step 2` as described in `README.md`

The tutorial's `README.md` shows the commands needed to create and run the task. This document explains why each task file exists, what it does, and how Harbor uses it.

## The init command

Running the following command in Step 1 creates a new Harbor task from a standard template:

```bash
harbor init nginx-log-fix
```

The generated files initially contain placeholder content. In Step 2, you replace that placeholder content with the actual configuration, instructions, environment, solution, and tests for the `nginx-log-fix` task.

After replacement, the task has the following structure:

```text
nginx-log-fix/
├── task.toml
├── instruction.md
├── environment/
│   └── Dockerfile
├── solution/
│   └── solve.sh
└── tests/
    └── test.sh
```

Each file has a separate responsibility.

## 1. `task.toml`: Task Configuration and Metadata

```toml
schema_version = "1.3"
artifacts = []

[task]
name = "local/nginx-log-fix"
description = "Fix a broken Python script parsing malformed Nginx logs into JSON metrics."
authors = [{ name = "Peter Mwenda" }]
keywords = []
category = "sysadmin"
```

`task.toml` is the task manifest that Harbor reads when loading the task. It contains both operational configuration and descriptive metadata.

Some settings can affect whether Harbor can load and run the task. Other settings primarily affect how the task is identified, documented, searched, or categorized.

| Setting | Purpose | What happens if it is wrong? |
| --- | --- | --- |
| `schema_version = "1.3"` | Specifies the Harbor task-definition format used by the file. | An unsupported or incorrect version may cause Harbor to reject the task or interpret its configuration incorrectly. This can prevent both Oracle and AI-agent evaluations from starting. |
| `artifacts = []` | Declares additional files or outputs that Harbor should collect after the run. This task declares none. | An invalid artifacts configuration may cause Harbor to reject the task or fail to collect expected outputs. An empty list is correct here because scoring uses `/logs/verifier/reward.txt`, which is handled by the verifier. |
| `[task]` | Begins the main task metadata section. | If this section is missing or malformed, Harbor may fail to load the task because the following task fields would not be defined in the expected location. |
| `name` | Provides the task's identifying name. The `local/` prefix indicates that it is a locally defined task. | A missing, invalid, or conflicting name may prevent Harbor from identifying the task correctly. An inaccurate but accepted name may not change the solution or score, but it can make results difficult to identify or compare. |
| `description` | Provides a short summary of the problem. | An inaccurate description may make the task misleading, but it does not directly change the broken script, reference solution, or verifier. The detailed requirements are defined in `instruction.md`. |
| `authors` | Records the task author or authors. | An incorrect author does not normally affect task execution or scoring, but it gives incorrect ownership or attribution information. An invalid value type may cause configuration validation to fail. |
| `keywords` | Provides optional terms for searching, filtering, or classifying the task. It is empty in this demo. | Incorrect keywords normally do not affect execution or scoring, but they can make the task harder to find or incorrectly grouped. An invalid value type may cause validation to fail. |
| `category` | Classifies the task by subject area. This task uses `sysadmin`. | An inaccurate category normally does not affect the task solution or score, but it can cause the task and its results to be grouped incorrectly. An invalid value may be rejected if Harbor validates allowed categories. |

### What a Wrong `task.toml` Can Affect

A structurally invalid `task.toml` can affect Harbor itself. Examples include invalid TOML syntax, an unsupported schema version, missing required sections, or fields containing the wrong data types.

Depending on the error, Harbor may:

- Reject the task before starting it.
- Fail to build or start the task environment.
- Fail to start the Oracle or AI-agent run.
- Misidentify or misconfigure the task.
- Fail to collect declared artifacts.
- Produce incomplete or unreliable evaluation results.

If Harbor cannot load or configure the task correctly, the AI model is not being evaluated fairly. A failed result may reflect a broken task definition rather than the model's ability to solve the problem.

Harbor must successfully read and validate `task.toml` before it can coordinate the rest of the task. A structurally correct manifest is therefore necessary for a valid and reliable evaluation.

## 2. `instruction.md`: Instructions Given to the Agent

`instruction.md` contains the problem statement that the AI agent must follow.

It tells the agent that:

- A broken script exists at `/app/parse_logs.py`.
- The script reads Nginx logs from `/var/log/nginx/access.log`.
- Malformed log entries must be handled safely.
- Lines without a valid supported HTTP status code must be ignored.
- Status codes must be grouped into `2xx`, `4xx`, and `5xx` families.
- The final counts must be written to `/app/metrics.json`.
- The expected result is:

```json
{
  "2xx": 1,
  "4xx": 1,
  "5xx": 1
}
```

This file defines the required outcome without giving the agent the reference implementation. The agent must inspect the environment, diagnose the failure, and implement a valid fix.

## 3. `environment/Dockerfile`: The Agent's Working Environment

The Dockerfile builds the isolated container in which the task is performed.

### Base image and working directory

```dockerfile
FROM python:3.12-slim

WORKDIR /app
```

This creates a lightweight Python 3.12 environment and sets `/app` as the working directory.

### Required directories

```dockerfile
RUN mkdir -p /var/log/nginx /app
```

This creates the directories needed for the Nginx access log and Python application.

### Sample Nginx logs

The Dockerfile creates `/var/log/nginx/access.log` with three entries:

1. A normal log entry containing status code `200`.
2. A normal log entry containing status code `404`.
3. An irregularly formatted line containing status code `500`.

These entries test whether the script can process both normally formatted and irregular input.

### Intentionally broken Python script

The Dockerfile also creates `/app/parse_logs.py` with this fragile parsing logic:

```python
parts = line.split(" ")
status = parts[8]
```

The script assumes that the HTTP status code is always the ninth space-separated value. That assumption is unsafe because:

- Multiple spaces can create empty list elements.
- A malformed line might have fewer fields.
- A differently formatted line might place the status code at another position.
- Accessing a missing element can raise an `IndexError`.

This is the defect the AI agent is expected to diagnose and repair.

### Default command

```dockerfile
CMD ["bash"]
```

This makes Bash available when the container starts so Harbor and the agent can execute commands inside it.

## 4. `solution/solve.sh`: Reference Solution

`solution/solve.sh` contains the benchmark author’s known-good solution. When the task is run with `-a oracle`, Harbor executes this reference solution and then runs `tests/test.sh` to verify the result.

Here, `oracle` means the benchmark’s reference solution - not an AI model. 
It is used to confirm that the task environment, reference solution, and verifier work correctly before the task is tested with an AI agent:

```bash
harbor run -p ./tasks/nginx-log-fix -a oracle
```

The script first enables immediate failure handling, meaning `solve.sh` should stop immediately if any command inside it fails:

```bash
set -e
```

It then replaces `/app/parse_logs.py` with a corrected version and runs it.

The corrected parser searches each log line using this regular expression:

```python
match = re.search(r"\b([245]\d\d)\b", line)
```

The expression searches for a complete three-digit code that:

- Starts with `2`, `4`, or `5`.
- Is followed by two digits.
- Appears as a separate value because of the word boundaries (`\b`).

Examples include `200`, `404`, and `500`.

When a matching code is found, the script converts its first digit into the appropriate metrics key:

```python
metrics[f"{code[0]}xx"] += 1
```

Therefore:

| Status code | Metrics group |
| --- | --- |
| `200` | `2xx` |
| `404` | `4xx` |
| `500` | `5xx` |

If no supported status code is found, the line is skipped safely. Finally, the script writes the aggregated counts to `/app/metrics.json` and executes the repaired parser.

The reference solution serves two purposes:

1. It proves that the task can be solved in the supplied environment.
2. It lets the task author verify the benchmark before evaluating an AI agent.

It is not intended to be shown to the AI agent as part of the problem instructions.

## 5. `tests/test.sh`: Automated Verifier

`tests/test.sh` grades the result produced by the agent.

First, it creates Harbor's verifier log directory:

```bash
mkdir -p /logs/verifier
```

It then runs the current version of the parser:

```bash
python3 /app/parse_logs.py >/dev/null 2>&1
```

Standard output and standard error are hidden because the verifier is interested in the generated JSON file rather than console output.

The embedded Python test attempts to load `/app/metrics.json` and compare it with:

```python
expected = {"2xx": 1, "4xx": 1, "5xx": 1}
```

The test passes only when the generated dictionary exactly matches the expected dictionary.

The verifier then writes the score to `/logs/verifier/reward.txt`:

```text
1.0
```

means the task passed, while:

```text
0.0
```

means the task failed.

## How the Files Work Together

Harbor can run this task in two different ways:

1. With `oracle`, which applies the supplied reference solution.
2. With an AI agent and model, which must inspect the task and implement a solution.

### Flow When Using Oracle

Run the task with:

```bash
harbor run -p ./tasks/nginx-log-fix -a oracle
```

Here, `oracle` means the benchmark’s reference solution, not an AI model.

Harbor performs the following steps:

1. Reads `task.toml` to identify and configure the task.
2. Builds the container defined by `environment/Dockerfile`.
3. Starts the container with the sample Nginx access log and the intentionally broken `/app/parse_logs.py`.
4. Executes `solution/solve.sh`.
5. `solve.sh` replaces the broken `/app/parse_logs.py` with the benchmark author’s reference implementation.
6. `solve.sh` runs the repaired Python script to generate `/app/metrics.json`.
7. Harbor runs `tests/test.sh`.
8. The verifier checks the generated `/app/metrics.json`.
9. The verifier writes `1.0` to `/logs/verifier/reward.txt` if the output is correct, or `0.0` if it is incorrect.

The Oracle run confirms that the task environment, reference solution, and verifier work correctly before the task is evaluated using an AI agent.

### Flow When Using an AI Agent and Model

Run the task with:

```bash
harbor run -p ./tasks/nginx-log-fix -a <agent-name> -m <model-name>
```

For example:

```bash
harbor run -p ./tasks/nginx-log-fix -a claude-code -m claude-3-5-sonnet-20241022
```

Harbor performs the following steps:

1. Reads `task.toml` to identify and configure the task.
2. Builds the container defined by `environment/Dockerfile`.
3. Starts the container with the sample Nginx access log and the intentionally broken `/app/parse_logs.py`.
4. Gives the requirements from `instruction.md` to the selected AI agent.
5. The AI agent uses the selected model to inspect the environment, diagnose the problem, and modify `/app/parse_logs.py`.
6. Harbor runs `tests/test.sh`.
7. The verifier checks the generated `/app/metrics.json`.
8. The verifier writes `1.0` to `/logs/verifier/reward.txt` if the output is correct, or `0.0` if it is incorrect.

In this flow, Harbor does not use `solution/solve.sh`. The AI agent must produce its own solution.

Both the Oracle flow and the AI-agent flow are evaluated using the same `tests/test.sh` verifier. This ensures that the reference solution and the AI-generated solution are checked against the same expected result.

## Responsibility Summary

| File | Responsibility |
| --- | --- |
| `task.toml` | Identifies and describes the Harbor task. |
| `instruction.md` | Defines the problem and expected result for the agent. |
| `environment/Dockerfile` | Builds the isolated environment containing the logs and broken script. |
| `solution/solve.sh` | Supplies the benchmark author's known-good reference solution. |
| `tests/test.sh` | Verifies the output and assigns the task reward. |

