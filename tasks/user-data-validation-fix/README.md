# Task 2: User Data Validation Gap (`user-validation-gap`)

> **Learning objective**
> This task demonstrates that a benchmark can contain clear instructions and a working environment but still produce misleading results when its reference solution and verifier share the same missed requirement.

Unlike Task 1, the Dockerfile does not generate the application or input data. You will create those files separately and use the Dockerfile only to copy them into the task environment.

## Repository Layout

```text
harbor-agent-tasks/
└── tasks/
    ├── nginx-log-fix/
    └── user-validation-gap/
        ├── task.toml
        ├── instruction.md
        ├── environment/
        │   ├── Dockerfile
        │   ├── users.json
        │   └── validate_users.py
        ├── solution/
        │   └── solve.sh
        └── tests/
            └── test.sh
```

## Step 1: Scaffold the Task

From the `harbor-agent-tasks/tasks` directory, scaffold Task 2:

```bash
harbor init user-validation-gap
# Select 't' when prompted to create a task.
# Organization: demo

cd user-validation-gap
```

## Step 2: Create the Task Files

Replace the generated placeholder content with the files below.

### `task.toml`

```toml
schema_version = "1.3"
artifacts = []

[task]
name = "local/user-validation-gap"
description = "Repair a Python program that validates user records and separates valid and rejected records."
authors = [{ name = "Peter Mwenda" }]
keywords = ["python", "json", "validation", "benchmark-testing"]
category = "software-engineering"
```

### `instruction.md`

````markdown
# Problem Statement

The Python program at `/app/validate_users.py` reads user records from `/app/users.json`, but its validation is incomplete and it crashes when it encounters malformed records.

Fix `/app/validate_users.py` so that it validates every record safely and produces:

- `/app/valid_users.json`
- `/app/rejected_users.json`

## Input

`/app/users.json` contains a JSON array. A valid user record must be a JSON object containing:

- `name`: a non-empty string after trimming surrounding whitespace.
- `email`: a string containing a valid email address.
- `age`: a non-negative integer.

## Requirements

1. Read every item from `/app/users.json` without crashing.
2. Reject any item that is not a JSON object.
3. Reject records with a missing, non-string, or blank `name`.
4. Reject records with an invalid `email`.
5. Reject records whose `age` is missing, is not an integer, is a boolean, or is negative.
6. Detect duplicate email addresses after trimming surrounding whitespace and converting them to lowercase.
7. Accept only the first valid occurrence of an email address and reject later occurrences as duplicates.
8. Preserve accepted user records in their original form and input order.
9. Write accepted records as a JSON array to `/app/valid_users.json`.
10. Write rejected items as a JSON array to `/app/rejected_users.json`.

Each rejected item must use this structure:

```json
{
  "index": 1,
  "record": {
    "name": "Example",
    "email": "invalid-email",
    "age": 30
  },
  "reasons": [
    "invalid email"
  ]
}
```

`index` is the item's zero-based position in the original input array. If a record violates multiple requirements, include every applicable reason.

Run the program with:

```bash
python3 /app/validate_users.py
```
````

### `environment/users.json`

```json
[
  {
    "name": "Amina",
    "email": "amina@example.com",
    "age": 29
  },
  {
    "name": "Brian",
    "email": "brian.example.com",
    "age": 31
  },
  {
    "name": "Carol",
    "email": "carol@example.com",
    "age": -4
  },
  {
    "name": "   ",
    "email": "nameless@example.com",
    "age": 22
  },
  {
    "name": "Amina Duplicate",
    "email": "amina@example.com",
    "age": 30
  },
  "malformed-record",
  {
    "name": "David",
    "email": "david@example.com",
    "age": 35
  }
]
```

The input intentionally contains an exact duplicate email but does not contain duplicates that differ only by capitalization or surrounding whitespace.

### `environment/validate_users.py`

```python
import json


with open("/app/users.json", encoding="utf-8") as source:
    users = json.load(source)

valid_users = []

for user in users:
    if user["name"]:
        valid_users.append(user)

with open("/app/valid_users.json", "w", encoding="utf-8") as output:
    json.dump(valid_users, output, indent=2)
```

This starter implementation is intentionally broken. It performs only a weak name check, does not create `rejected_users.json`, and crashes when it reaches the string item in the input array.

### `environment/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY users.json /app/users.json
COPY validate_users.py /app/validate_users.py

CMD ["bash"]
```

The Dockerfile is intentionally simple. The developer-created files already exist in `environment/`, so the image only copies them into `/app`.

### `solution/solve.sh`

```bash
#!/bin/bash
set -e

cat <<'PYTHON' > /app/validate_users.py
import json
import re


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


with open("/app/users.json", encoding="utf-8") as source:
    users = json.load(source)

valid_users = []
rejected_users = []
seen_emails = set()

for index, user in enumerate(users):
    reasons = []

    if not isinstance(user, dict):
        rejected_users.append({
            "index": index,
            "record": user,
            "reasons": ["record must be an object"],
        })
        continue

    name = user.get("name")
    email = user.get("email")
    age = user.get("age")

    if not isinstance(name, str) or not name.strip():
        reasons.append("invalid name")

    if not isinstance(email, str) or not EMAIL_PATTERN.fullmatch(email.strip()):
        reasons.append("invalid email")

    if isinstance(age, bool) or not isinstance(age, int) or age < 0:
        reasons.append("invalid age")

    if isinstance(email, str) and EMAIL_PATTERN.fullmatch(email.strip()):
        if email in seen_emails:
            reasons.append("duplicate email")

    if reasons:
        rejected_users.append({
            "index": index,
            "record": user,
            "reasons": reasons,
        })
        continue

    seen_emails.add(email)
    valid_users.append(user)

with open("/app/valid_users.json", "w", encoding="utf-8") as output:
    json.dump(valid_users, output, indent=2)

with open("/app/rejected_users.json", "w", encoding="utf-8") as output:
    json.dump(rejected_users, output, indent=2)
PYTHON

python3 /app/validate_users.py
```

This reference solution deliberately contains a subtle defect. It detects only exact duplicate email strings:

```python
if email in seen_emails:
```

It does not normalize email addresses with `strip().lower()` as required by `instruction.md`. Because `users.json` contains only an exact duplicate, the defect is not exposed by the supplied input.

### `tests/test.sh`

```bash
#!/bin/bash

mkdir -p /logs/verifier

python3 /app/validate_users.py >/dev/null 2>&1

python3 <<'PYTHON'
import json
import os
import sys


try:
    with open("/app/valid_users.json", encoding="utf-8") as source:
        valid_users = json.load(source)

    passed = (
        os.path.isfile("/app/rejected_users.json")
        and isinstance(valid_users, list)
        and [user.get("email") for user in valid_users]
        == ["amina@example.com", "david@example.com"]
    )
except Exception:
    passed = False

sys.exit(0 if passed else 1)
PYTHON

if [ $? -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi
```

This verifier is intentionally incomplete. It confirms only that:

- `valid_users.json` can be read.
- `rejected_users.json` exists.
- The two expected valid email addresses appear in the expected order.

It does not verify:

- The contents of `rejected_users.json`.
- Rejection indexes or reasons.
- Multiple validation failures on one record.
- Boolean ages.
- Duplicate emails with different capitalization.
- Duplicate emails with surrounding whitespace.
- Whether the solution is general or merely hard-coded for this input.

## Step 3: Run the Task

Return to the `harbor-agent-tasks` project root:

```bash
cd ../../
```

Run the intentionally incomplete reference solution:

```bash
harbor run -p ./tasks/user-validation-gap -a oracle
```

The Oracle run is expected to receive a reward of `1.0`, even though `solution/solve.sh` does not satisfy the case-insensitive and whitespace-normalized duplicate requirement.

Run the task using an AI agent and model:

```bash
harbor run -p ./tasks/user-validation-gap -a codex -m openai/gpt-5-mini
```

An AI agent may implement the requirement correctly, but it may also make the same raw-string duplicate comparison as the reference solution. The incomplete verifier cannot distinguish between those implementations.

## Step 4: Understand the False Positive

The task reports success whenever the limited checks in `tests/test.sh` pass. A reward of `1.0` therefore does not prove that every requirement in `instruction.md` was implemented.

The missed requirement can be exposed with records such as:

```json
{
  "name": "Amina Case Variant",
  "email": "Amina@Example.com",
  "age": 32
}
```

and:

```json
{
  "name": "Amina Whitespace Variant",
  "email": " amina@example.com ",
  "age": 33
}
```

Both emails normalize to `amina@example.com` and should be rejected as duplicates. The supplied reference solution would incorrectly accept them.

## Step 5: Strengthen the Verifier and Expose the Defect

The first Oracle run produced `1.0` because the original verifier did not test every requirement. Replace `tests/test.sh` with the comprehensive verifier below:

```bash
#!/bin/bash

mkdir -p /logs/verifier

cat <<'JSON' > /app/users.json
[
  {
    "name": "Amina",
    "email": "amina@example.com",
    "age": 29
  },
  {
    "name": "Brian",
    "email": "brian.example.com",
    "age": 31
  },
  {
    "name": "Carol",
    "email": "carol@example.com",
    "age": -4
  },
  {
    "name": "   ",
    "email": "nameless@example.com",
    "age": 22
  },
  {
    "name": "Amina Exact Duplicate",
    "email": "amina@example.com",
    "age": 30
  },
  "malformed-record",
  {
    "name": "David",
    "email": "david@example.com",
    "age": 35
  },
  {
    "name": "Amina Case Variant",
    "email": "Amina@Example.com",
    "age": 32
  },
  {
    "name": "Amina Whitespace Variant",
    "email": " amina@example.com ",
    "age": 33
  },
  {
    "name": "",
    "email": "invalid-email",
    "age": true
  },
  {}
]
JSON

python3 /app/validate_users.py >/dev/null 2>&1

python3 <<'PYTHON'
import json
import sys


expected_valid = [
    {
        "name": "Amina",
        "email": "amina@example.com",
        "age": 29,
    },
    {
        "name": "David",
        "email": "david@example.com",
        "age": 35,
    },
]

expected_rejected = [
    {
        "index": 1,
        "record": {
            "name": "Brian",
            "email": "brian.example.com",
            "age": 31,
        },
        "reasons": ["invalid email"],
    },
    {
        "index": 2,
        "record": {
            "name": "Carol",
            "email": "carol@example.com",
            "age": -4,
        },
        "reasons": ["invalid age"],
    },
    {
        "index": 3,
        "record": {
            "name": "   ",
            "email": "nameless@example.com",
            "age": 22,
        },
        "reasons": ["invalid name"],
    },
    {
        "index": 4,
        "record": {
            "name": "Amina Exact Duplicate",
            "email": "amina@example.com",
            "age": 30,
        },
        "reasons": ["duplicate email"],
    },
    {
        "index": 5,
        "record": "malformed-record",
        "reasons": ["record must be an object"],
    },
    {
        "index": 7,
        "record": {
            "name": "Amina Case Variant",
            "email": "Amina@Example.com",
            "age": 32,
        },
        "reasons": ["duplicate email"],
    },
    {
        "index": 8,
        "record": {
            "name": "Amina Whitespace Variant",
            "email": " amina@example.com ",
            "age": 33,
        },
        "reasons": ["duplicate email"],
    },
    {
        "index": 9,
        "record": {
            "name": "",
            "email": "invalid-email",
            "age": True,
        },
        "reasons": ["invalid name", "invalid email", "invalid age"],
    },
    {
        "index": 10,
        "record": {},
        "reasons": ["invalid name", "invalid email", "invalid age"],
    },
]

try:
    with open("/app/valid_users.json", encoding="utf-8") as source:
        actual_valid = json.load(source)

    with open("/app/rejected_users.json", encoding="utf-8") as source:
        actual_rejected = json.load(source)

    passed = (
        actual_valid == expected_valid
        and actual_rejected == expected_rejected
    )
except Exception:
    passed = False

sys.exit(0 if passed else 1)
PYTHON

if [ $? -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi
```

This verifier replaces `/app/users.json` with expanded test data before running the solution. It now checks:

- Valid records and their original order.
- Invalid names, emails, and ages.
- Boolean ages.
- Non-object records.
- Missing fields.
- Exact duplicate emails.
- Duplicate emails with different capitalization.
- Duplicate emails with surrounding whitespace.
- Multiple rejection reasons on one record.
- Complete rejected-record contents, indexes, and reasons.

Run Oracle again:

```bash
harbor run -p ./tasks/user-validation-gap -a oracle
```

This time, Oracle is expected to receive:

```text
0.0
```

This failure is intentional. The stronger verifier has exposed the defect in `solution/solve.sh`: it compares raw email strings instead of normalized email addresses.

The earlier `1.0` was therefore a false positive caused by incomplete test coverage.

## Step 6: Correct the Reference Solution

The task should not remain in a failing state. Replace `solution/solve.sh` with the corrected reference solution below:

```bash
#!/bin/bash
set -e

cat <<'PYTHON' > /app/validate_users.py
import json
import re


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


with open("/app/users.json", encoding="utf-8") as source:
    users = json.load(source)

valid_users = []
rejected_users = []
seen_emails = set()

for index, user in enumerate(users):
    reasons = []

    if not isinstance(user, dict):
        rejected_users.append({
            "index": index,
            "record": user,
            "reasons": ["record must be an object"],
        })
        continue

    name = user.get("name")
    email = user.get("email")
    age = user.get("age")

    if not isinstance(name, str) or not name.strip():
        reasons.append("invalid name")

    email_is_valid = (
        isinstance(email, str)
        and EMAIL_PATTERN.fullmatch(email.strip()) is not None
    )

    if not email_is_valid:
        reasons.append("invalid email")

    if isinstance(age, bool) or not isinstance(age, int) or age < 0:
        reasons.append("invalid age")

    normalized_email = email.strip().lower() if email_is_valid else None

    if normalized_email is not None and normalized_email in seen_emails:
        reasons.append("duplicate email")

    if reasons:
        rejected_users.append({
            "index": index,
            "record": user,
            "reasons": reasons,
        })
        continue

    seen_emails.add(normalized_email)
    valid_users.append(user)

with open("/app/valid_users.json", "w", encoding="utf-8") as output:
    json.dump(valid_users, output, indent=2)

with open("/app/rejected_users.json", "w", encoding="utf-8") as output:
    json.dump(rejected_users, output, indent=2)
PYTHON

python3 /app/validate_users.py
```

The corrected solution normalizes every valid email before duplicate detection:

```python
normalized_email = email.strip().lower()
```

It uses the normalized value for both the lookup and the `seen_emails` set. The original user record is still preserved in the output, as required by `instruction.md`.

Run Oracle one final time:

```bash
harbor run -p ./tasks/user-validation-gap -a oracle
```

The final Oracle run is expected to receive:

```text
1.0
```

The task is now in its expected final state:

- `instruction.md` defines clear and complete requirements.
- `environment/Dockerfile` builds the intended environment from developer-created files.
- `solution/solve.sh` satisfies the written requirements.
- `tests/test.sh` checks the important valid, invalid, duplicate, malformed, and multi-error scenarios.
- Oracle passes the strengthened verifier with a reward of `1.0`.

## Conclusion

This task demonstrates the complete benchmark-development cycle:

1. The initial verifier allowed an incomplete reference solution to receive `1.0`.
2. A stronger verifier exposed the missing email-normalization behavior and correctly produced `0.0`.
3. The reference solution was corrected to satisfy the written requirements.
4. The final Oracle run produced `1.0` using the strengthened verifier.

An Oracle pass proves only that the reference solution passes the supplied verifier. The verifier must cover the written requirements before that result can be considered meaningful.

The developer should never leave a benchmark with a failing Oracle run. The completed task must contain consistent instructions, a reproducible environment, a correct reference solution, and tests strong enough to reject incomplete implementations.

The quality of a Harbor evaluation depends on the quality of the task design: **garbage in, garbage out.**
