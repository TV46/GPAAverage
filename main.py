import itertools
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import fmean
import requests
from compasspy.client import Compass
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SCHOOL_SUBDOMAIN = "sthelena-vic"
YEARS = range(13, 20)


class Spinner:
    def __init__(self, text="Loading"):
        self.text = text
        self._stop = threading.Event()

    def _spin(self):
        for dots in itertools.cycle([".", "..", "..."]):
            if self._stop.is_set():
                break
            sys.stdout.write(f"\r{self.text}{dots}   ")
            sys.stdout.flush()
            time.sleep(0.5)
        # Clear the spinner line cleanly before returning control
        sys.stdout.write("\r" + " " * 50 + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()

def pause_exit(code: int = 0) -> None:
    input("\nPress Enter to exit")
    sys.exit(code)

def build_session(client: Compass) -> requests.Session:
    session = requests.Session()
    session.headers.update(client.headers)
    session.cookies.update(client.cookies)

    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    return session


def fetch_learning_tasks(
    session: requests.Session,
    api_endpoint: str,
    user_id: int,
    group_id: int,
    ) -> tuple[int, dict, list] | None:

    payload = {
        "sessionstate": "readonly",
        "userId": user_id,
        "targetUserId": user_id,
        "activityId": -1,
        "page": 1,
        "start": 0,
        "limit": 999,
        "academicGroupId": group_id,
    }

    try:
        response = session.post(
            api_endpoint + "LearningTasks.svc/GetAllLearningTasksByUserId",
            json=payload,
            timeout=(15, 30),
        )
    except requests.exceptions.Timeout:
        print(f"\nTimed out, skipping year.")
        return None

    if response is None:
        return None

    if not response.ok:
        print(f"\nHTTP {response.status_code}, skipping year.")
        return None

    try:
        data = response.json()
    except ValueError:
        print(f"\nInvalid JSON response, skipping year.")
        return None

    tasks = data.get("d", {}).get("data", [])
    if not tasks:
        return None

    subject_scores: dict[str, list[float]] = {}
    all_scores: list[float] = []

    for task in tasks:
        subject = task.get("subjectName", "Unknown")
        for student in task.get("students", []):
            for result in student.get("results", []):
                try:
                    score = float(result.get("result"))
                except (TypeError, ValueError):
                    continue
                subject_scores.setdefault(subject, []).append(score)
                all_scores.append(score)

    return group_id, subject_scores, all_scores


def clean_subject_code(subject: str) -> str:
    return re.sub(r"^0+", "", subject)


def infer_display_year(subject_scores: dict) -> int | None:
    if not subject_scores:
        return None
    match = re.match(r"^0*(\d+)", next(iter(subject_scores)))
    return int(match.group(1)) if match else None


def print_year_results(year: int, subject_scores: dict, all_scores: list) -> None:
    display_year = infer_display_year(subject_scores) or year
    print(f"\n=== Year {display_year} ===")
    print("Subject Averages")
    print("-" * 40)
    for subject in sorted(subject_scores):
        avg = fmean(subject_scores[subject])
        print(f"{clean_subject_code(subject):<25} {avg:.2f}")
    print("-" * 40)
    if all_scores:
        print(f"Yearly Average: {fmean(all_scores):.2f}")


def main() -> None:
    auth_cookie = input("Input Auth Cookie: ")
    client = Compass(SCHOOL_SUBDOMAIN, auth_cookie)

    try:
        with Spinner("Authenticating"):
            client.login()
    except Exception as e:
        print(f"Login authentication failed.\nError: \033[31m{e}\033[0m")
        pause_exit(1)

    user_id = int(client.dt["userId"])
    print(f"Logged in as: {client.user.name} (ID: {user_id})")

    session = build_session(client)

    results: dict[int, tuple[dict, list]] = {}
    with Spinner("Querying Database"):
        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = {
                executor.submit(
                    fetch_learning_tasks, session, client.API_ENDPOINT, user_id, year
                ): year
                for year in YEARS
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    yr, subject_scores, all_scores = result
                    results[yr] = (subject_scores, all_scores)

    for year in YEARS:
        if year in results:
            subject_scores, all_scores = results[year]
            print_year_results(year, subject_scores, all_scores)

    all_scores_flat = list(
        itertools.chain.from_iterable(
            scores for _, scores in results.values() if scores
        )
    )
    if all_scores_flat:
        print(f"\nOverall Average: {fmean(all_scores_flat):.2f}")

    pause_exit(0)


if __name__ == "__main__":
    main()