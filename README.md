# harbor-benchmarks

Custom evaluation benchmarks and containerized test tasks built for Harbor.

I assume you are using a MacBook or Linux-related OS.

To get started, follow the steps below to set up your environment and run your first test task.

---

## Step 1: Python 3

Ensure you have Python 3 installed. Run the following command to confirm:

```bash
python3 -V

```

Sample output

```text
Python 3.14.6

```

---

## Step 2: Install `uv`

Install `uv` (Fast Python package installer and resolver) via Homebrew:

```bash
brew install uv

```

Then 
```bash
uv --version
```

Sample output

```text
uv 0.11.32 (Homebrew 2026-07-23 x86_64-apple-darwin)

```

---

## Step 3: Install Harbor

Install the Harbor evaluation framework using `uv`:

```bash
uv tool install harbor==0.20.0

```

Then
```bash
harbor --version
```

Sample output

```text
0.20.0

```

---

## Step 4: Run Your First Demo Task (`nginx-log-fix`)

Navigate to the repo `tasks/nginx-log-fix`
