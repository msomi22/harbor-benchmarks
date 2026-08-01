# Task 1: Nginx Log Processing Script (`nginx-log-fix`)

This task tests an AI agent's ability to debug a failing Python script, handle malformed input logs using regex, and output formatted JSON results in a sandboxed Docker container.

---

## 📁 Repository & Directory Layout

To keep the task organized, we will create the following folder structure inside our repository:
For this task, only create folder `harbor-agent-tasks` and inside create another folder 'tasks'.
We will execute the next steps inside this folder 'tasks'. The final layout at the end will look as follows.

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

---

## 🛠️ Step 1: Scaffold Quick Commands

If you want to generate the initial directory structure automatically using Harbor, run:

```bash
mkdir -p tasks && cd tasks
harbor init nginx-log-fix
# Select 't' when prompted for task creation
cd nginx-log-fix

```

---

## 📄 Step 2: Task Files Content

Replace or populate the generated files with the exact contents below:

### 1. `task.toml`

*Configures metadata, container timeouts, and environment parameters for Harbor.*

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

---

### 2. `instruction.md`

*This is the **only text prompt** provided to the AI agent inside the container environment.*

```markdown
# Problem Statement

There is an existing Python script at `/app/parse_logs.py` intended to parse Nginx access log lines from `/var/log/nginx/access.log`.

Currently, running `python3 /app/parse_logs.py` fails when encountering non-standard or malformed log lines.

### Requirements:
1. Fix `/app/parse_logs.py` so that it safely parses all lines in `/var/log/nginx/access.log`.
2. Extract and aggregate HTTP status code families (`2xx`, `4xx`, and `5xx`).
3. Save the final aggregated counts into `/app/metrics.json` using the following exact structure:

```json
{
  "2xx": 1,
  "4xx": 1,
  "5xx": 1
}
```

---

### 3. `environment/Dockerfile`
*Defines the initial container state (including the buggy log file and incomplete script).*

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 1. Create directory structure
RUN mkdir -p /var/log/nginx /app

# 2. Add test access log containing standard lines and one malformed line
RUN echo '192.168.1.1 - - [01/Aug/2026:10:00:00 +0000] "GET /api HTTP/1.1" 200 123' > /var/log/nginx/access.log && \
    echo '192.168.1.2 - - [01/Aug/2026:10:01:00 +0000] "POST /login HTTP/1.1" 404 45' >> /var/log/nginx/access.log && \
    echo '192.168.1.3 - - MALFORMED LINE EXTRA SPACES 500' >> /var/log/nginx/access.log

# 3. Create the initial broken script that crashes on malformed input
RUN cat << 'EOF' > /app/parse_logs.py
import json

metrics = {"2xx": 0, "4xx": 0, "5xx": 0}

with open("/var/log/nginx/access.log", "r") as f:
    for line in f:
        # Rigid split that crashes on unexpected formats
        parts = line.split(" ")
        status = parts[8]  
        if status.startswith("2"): metrics["2xx"] += 1
        elif status.startswith("4"): metrics["4xx"] += 1
        elif status.startswith("5"): metrics["5xx"] += 1

with open("/app/metrics.json", "w") as out:
    json.dump(metrics, out)
EOF

CMD ["bash"]

```

---

### 4. `solution/solve.sh`

*The ground-truth reference solution used to verify that the task can score `1.0`.*

```bash
#!/bin/bash
set -e

# Overwrite /app/parse_logs.py with a resilient regex parser solution
cat << 'EOF' > /app/parse_logs.py
import re
import json

metrics = {"2xx": 0, "4xx": 0, "5xx": 0}

with open("/var/log/nginx/access.log", "r") as f:
    for line in f:
        # Use regex to find 3-digit status codes (2xx, 4xx, 5xx) anywhere in the line
        match = re.search(r'\b([245]\d\d)\b', line)
        if match:
            code = match.group(1)
            if code.startswith("2"):
                metrics["2xx"] += 1
            elif code.startswith("4"):
                metrics["4xx"] += 1
            elif code.startswith("5"):
                metrics["5xx"] += 1

with open("/app/metrics.json", "w") as out:
    json.dump(metrics, out, indent=2)
EOF

# Execute the script
python3 /app/parse_logs.py

```

---

### 5. `tests/test.sh`

*The test harness run by Harbor after the agent finishes. Scores `1.0` for success or `0.0` for failure.*

```bash
#!/bin/bash

# Ensure output directory for harbor evaluation logger exists
mkdir -p /logs/verifier

# 1. Run the python script
python3 /app/parse_logs.py 2>/dev/null

# 2. Assert that metrics.json exists
if [ ! -f "/app/metrics.json" ]; then
    echo "0.0" > /logs/verifier/reward.txt
    exit 0
fi

# 3. Assert correct output contents
HAS_2XX=$(grep -q '"2xx": 1' /app/metrics.json && echo 1 || echo 0)
HAS_4XX=$(grep -q '"4xx": 1' /app/metrics.json && echo 1 || echo 0)
HAS_5XX=$(grep -q '"5xx": 1' /app/metrics.json && echo 1 || echo 0)

if [ "$HAS_2XX" -eq 1 ] && [ "$HAS_4XX" -eq 1 ] && [ "$HAS_5XX" -eq 1 ]; then
    echo "1.0" > /logs/verifier/reward.txt
else
    echo "0.0" > /logs/verifier/reward.txt
fi

```

---

## 🚀 Step 3: Running & Testing the Task

### 1. Test your reference solution first (Sanity Check)

Before testing an AI agent, verify your reference solution scores `1.0`:

From the directory that has tasks ... execute the following 

```bash
harbor run -p ./tasks/nginx-log-fix -a oracle

```

To debug
```bash
harbor trials start -p ./tasks/nginx-log-fix -a oracle
```

### 2. Run against an AI Agent

Run the benchmark against your chosen agent and model:

```bash
harbor run -p ./tasks/nginx-log-fix -a <agent-name> -m <model-name>

```
### Example
```bash
harbor run -p ./tasks/nginx-log-fix -a claude-code -m claude-3-5-sonnet-20241022
```
