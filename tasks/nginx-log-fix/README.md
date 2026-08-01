# Task 1: Nginx Log Processing Script (`nginx-log-fix`)

> **Note**
> This is a demo task to help learners get started with Harbor. It is intentionally simple.

## Repository Layout

```text
harbor-agent-tasks/
└── tasks/
    └── nginx-log-fix/
        ├── task.toml
        ├── instruction.md
        ├── environment/
        │   └── Dockerfile
        ├── solution/
        │   └── solve.sh
        └── tests/
            └── test.sh
```

## Step 1: Scaffold the Task

```bash
mkdir -p harbor-agent-tasks/tasks
cd harbor-agent-tasks/tasks

harbor init nginx-log-fix
# Select 't' when prompted to create a task.
# Enter any organization name when prompted
# Organization: demo

cd nginx-log-fix
```

## Step 2: Replace the Generated Files

### `task.toml`

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

### `instruction.md`

````markdown
# Problem Statement

There is an existing Python script at `/app/parse_logs.py` intended to parse Nginx access logs from `/var/log/nginx/access.log`.

Running:

```bash
python3 /app/parse_logs.py
```

currently fails when malformed log entries are encountered.

## Requirements

1. Fix `/app/parse_logs.py` so it safely parses every line in `/var/log/nginx/access.log`.
2. Ignore malformed lines that do not contain a valid HTTP status code.
3. Aggregate HTTP status code families (`2xx`, `4xx`, and `5xx`).
4. Write the aggregated counts to `/app/metrics.json`.

Expected output:

```json
{
  "2xx": 1,
  "4xx": 1,
  "5xx": 1
}
```
````

### `environment/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN mkdir -p /var/log/nginx /app

RUN echo '192.168.1.1 - - [01/Aug/2026:10:00:00 +0000] "GET /api HTTP/1.1" 200 123' > /var/log/nginx/access.log && \
    echo '192.168.1.2 - - [01/Aug/2026:10:01:00 +0000] "POST /login HTTP/1.1" 404 45' >> /var/log/nginx/access.log && \
    echo '192.168.1.3 - - MALFORMED LINE EXTRA SPACES 500' >> /var/log/nginx/access.log

RUN cat << 'EOF' > /app/parse_logs.py
import json

metrics = {"2xx": 0, "4xx": 0, "5xx": 0}

with open("/var/log/nginx/access.log") as f:
    for line in f:
        parts = line.split(" ")
        status = parts[8]
        if status.startswith("2"):
            metrics["2xx"] += 1
        elif status.startswith("4"):
            metrics["4xx"] += 1
        elif status.startswith("5"):
            metrics["5xx"] += 1

with open("/app/metrics.json", "w") as out:
    json.dump(metrics, out)
EOF

CMD ["bash"]
```

### `solution/solve.sh`

```bash
#!/bin/bash
set -e

cat << 'EOF' > /app/parse_logs.py
import re
import json

metrics = {"2xx": 0, "4xx": 0, "5xx": 0}

with open("/var/log/nginx/access.log") as f:
    for line in f:
        match = re.search(r"\b([245]\d\d)\b", line)
        if match:
            code = match.group(1)
            metrics[f"{code[0]}xx"] += 1

with open("/app/metrics.json", "w") as out:
    json.dump(metrics, out, indent=2)
EOF

python3 /app/parse_logs.py
```

### `tests/test.sh`

```bash
#!/bin/bash

mkdir -p /logs/verifier

python3 /app/parse_logs.py >/dev/null 2>&1

python3 <<'EOF'
import json, sys
expected={"2xx":1,"4xx":1,"5xx":1}
try:
    actual=json.load(open("/app/metrics.json"))
except Exception:
    sys.exit(1)
sys.exit(0 if actual==expected else 1)
EOF

if [ $? -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi
```

## Step 3: Run the Task

Return to the project root, the folder named `harbor-agent-tasks`:

```bash
cd ../../
```

Verify the reference solution:

```bash
harbor run -p ./tasks/nginx-log-fix -a oracle
```

Run against an AI agent:

```bash
harbor run -p ./tasks/nginx-log-fix -a <agent-name> -m <model-name>
```

Example:

```bash
harbor run -p ./tasks/nginx-log-fix -a claude-code -m claude-3-5-sonnet-20241022
```

# Congratulations!

You have successfully created and executed your first Harbor demo task.
