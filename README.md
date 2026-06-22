# Compass Learning Task Averages

A command-line tool for St Helena Secondary College that queries the Compass school portal and prints per-subject and per-year score averages across all year groups.

---

## What it does

- Authenticates with Compass using your session cookie
- Concurrently fetches learning task results for all year groups (Years 7-13)
- Calculates and displays a score average for every subject, every year group, and the school overall
- Retries failed requests automatically with exponential backoff

### Example output

```
Logged in as: John Smith (ID: 12345)

=== Year 7 ===
Subject Averages
----------------------------------------
7ECL                      72.45
7MAT                      68.90
7SCI                      74.10
----------------------------------------
Yearly Average: 71.82

=== Year 8 ===
...

Overall Average: 73.14
```

---

## Requirements

- A Compass account
- Python 3.12+ (if running from source)

---

## Usage

### Option 1 — Download the pre-built executable (recommended)

1. Go to the **Actions** tab in this repository
2. Open the latest successful **Build Executable** workflow run
3. Download the `compass_tasks` artifact
4. Run `compass_tasks.exe`

### Option 2 — Run from source

```bash
git clone https://github.com/your-org/your-repo.git
cd your-repo
pip install -r requirements.txt
python main.py
```

### Getting your auth cookie

The tool requires a Compass session cookie to authenticate. To find it:

1. Log in to compass in your browser
2. Open developer tools (`F12`)
3. Go to **Application** > **Cookies**
4. Copy the value of the `ASP.NET_SessionId` cookie (or equivalent session cookie)
5. Paste it when prompted by the tool

> The cookie is only valid for the duration of your browser session. You will need to repeat this each time you log in.

---

## Building from source

The GitHub Actions workflow at `.github/workflows/build.yml` automatically compiles a Windows executable on every push to `main`.

To build manually:

```bash
pip install pyinstaller -r requirements.txt
pyinstaller --onefile --name compass_tasks --clean main.py
```

The output will be at `dist/compass_tasks.exe`.

---

## Dependencies

| Package | Purpose |
|---|---|
| `compasspy` | Compass API client and authentication |
| `requests` | HTTP session management |
| `urllib3` | Retry logic and connection pooling |

---

## Project structure

```
.
├── main.py                        # Main script
├── requirements.txt               # Python dependencies
└── .github/
    └── workflows/
        └── build.yml              # CI workflow — builds compass_tasks.exe
```
