import time
import requests
from compasspy.client import Compass
from statistics import fmean
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

SCHOOL_SUBDOMAIN = "***REMOVED***"
AUTH_COOKIE = input("Input Auth Cookie: ")
YEARS = range(13, 20)
client = Compass(SCHOOL_SUBDOMAIN, AUTH_COOKIE)
client.login()
user_id = int(client.dt["userId"])
print(f"Logged in as: {client.user.name} (ID: {user_id})")

SESSION = requests.Session()
SESSION.headers.update(client.headers)
SESSION.cookies.update(client.cookies)

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=20,
    pool_maxsize=20
)
SESSION.mount("https://", adapter)

def fetch_learning_tasks(year):
    payload = {
        "sessionstate": "readonly",
        "userId": user_id,
        "targetUserId": user_id,
        "activityId": -1,
        "page": 1,
        "start": 0,
        "limit": 999,
        "academicGroupId": year,
    }

    for attempt in range(3):
        try:
            r = SESSION.post(
                client.API_ENDPOINT + "LearningTasks.svc/GetAllLearningTasksByUserId",
                json=payload,
                timeout=(15, 30)
            )
            break
        except requests.exceptions.Timeout:
            if attempt == 2:
                print(f"Year {year}: timed out after 3 attempts, skipping.")
                return None
            wait = 2 ** attempt
            print(f"Year {year}: timeout on attempt {attempt + 1}, retrying in {wait}s...")
            time.sleep(wait)

    try:
        data = r.json()
    except ValueError:
        print(f"Year {year}: invalid JSON response")
        return None

    tasks = data.get("d", {}).get("data", [])
    if not tasks:
        return None

    tasks = data.get("d", {}).get("data", [])
    subject_scores = {}
    all_scores = []

    ss_setdefault = subject_scores.setdefault  # local binding (faster)
    append_all = all_scores.append

    for task in tasks:
        subject = task.get("subjectName", "Unknown")
        students = task.get("students", [])
        for student in students:
            results = student.get("results", [])
            for result in results:
                try:
                    score = float(result.get("result"))
                except (TypeError, ValueError):
                    continue
                ss_setdefault(subject, []).append(score)
                append_all(score)

    return year, subject_scores, all_scores

# Extract year from first subject's code, e.g. "07ECL" -> 7, "10MAT" -> 10
def get_display_year(subject_scores):
    if not subject_scores:
        return None
    first_subject = next(iter(subject_scores))
    match = re.match(r'^0*(\d+)', first_subject)
    return int(match.group(1)) if match else None

# Strip leading zeros from subject codes, e.g. "07ECL" -> "7ECL"
def clean_subject_code(subject):
    return re.sub(r'^0+', '', subject)

# Fetch all years concurrently
results = {}
with ThreadPoolExecutor(max_workers=7) as executor:
    futures = {executor.submit(fetch_learning_tasks, year): year for year in YEARS}
    for future in as_completed(futures):
        result = future.result()
        if result:
            year, subject_scores, all_scores = result
            results[year] = (subject_scores, all_scores)

# Print results in order
for year in YEARS:
    if year not in results:
        continue
    subject_scores, all_scores = results[year]

    display_year = get_display_year(subject_scores)
    print(f"\n=== Year {display_year} ===" if display_year else f"\n=== Year {year} ===")
    print("Subject Averages")
    print("-" * 40)
    averages = {s: fmean(scores) for s, scores in subject_scores.items()}
    for subject in sorted(subject_scores):
        print(f"{clean_subject_code(subject):<25} {averages[subject]:.2f}")
    print("-" * 40)
    if all_scores:
        print(f"Yearly Average: {fmean(all_scores):.2f}")

all_years_scores = [
    score
    for subject_scores, all_scores in results.values()
    if all_scores
    for score in all_scores
]
print(f"\nOverall Average: {fmean(all_years_scores):.2f}")

input("Press enter to close")