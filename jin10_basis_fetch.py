#!/usr/bin/env python3
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta


API_ROOT = "https://28e2bd69d5104a428d25ff1df132b716.z3c.jin10.com/basic_data"
HEADERS = {
    "x-version": "1.0",
    "x-app-id": "KxBcVoDHStE6CUkQ",
    "User-Agent": "Mozilla/5.0",
}


def fetch_json(url: str, retries: int = 4, sleep_sec: float = 0.8):
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries - 1:
                time.sleep(sleep_sec * (attempt + 1))
    raise last_error


def fetch_snapshot(target_date: str):
    return fetch_json(f"{API_ROOT}?date={target_date}")


def fetch_category_history(category: str, start_date: str, end_date: str):
    params = urllib.parse.urlencode(
        {"category": category, "start": start_date, "end": end_date}
    )
    return fetch_json(f"{API_ROOT}/category?{params}")


def iter_snapshot_rows(snapshot):
    for group in snapshot["data"]["list"]:
        group_name = group["name"]
        for row in group["data"]:
            enriched = dict(row)
            enriched["group_name"] = group_name
            yield enriched


def clean_history_rows(rows):
    cleaned = []
    for row in rows:
        published = row.get("published")
        spot = row.get("spot_data")
        futures = row.get("futures_data")
        basis = row.get("jicha")
        if published != 1:
            continue
        if spot in (None, 0) and futures in (None, 0) and basis in (None, 0):
            continue
        cleaned.append(
            {
                "date": row.get("date"),
                "spot": row.get("spot_data"),
                "futures": row.get("futures_data"),
                "basis": row.get("jicha"),
                "rate": row.get("jicha_rate"),
                "city": row.get("city"),
                "unit": row.get("unit"),
            }
        )
    cleaned.sort(key=lambda item: item["date"])
    return cleaned


def enrich_rows(target_date: str, days: int):
    snapshot = fetch_snapshot(target_date)
    snapshot_rows = list(iter_snapshot_rows(snapshot))
    categories = [row["category"] for row in snapshot_rows]
    start_date = (datetime.strptime(target_date, "%Y-%m-%d").date() - timedelta(days=days)).isoformat()

    history_map = {}
    for category in categories:
        payload = fetch_category_history(category, start_date, target_date)
        raw_rows = payload.get("data", {}).get("list", [])
        history_map[category] = clean_history_rows(raw_rows)

    enriched = []
    for snap in snapshot_rows:
        category = snap["category"]
        history = history_map.get(category, [])

        current = None
        if snap.get("published") == 1 and not (
            snap.get("spot_data") in (None, 0)
            and snap.get("futures_data") in (None, 0)
            and snap.get("jicha") in (None, 0)
        ):
            current = {
                "date": snap.get("date"),
                "spot": snap.get("spot_data"),
                "futures": snap.get("futures_data"),
                "basis": snap.get("jicha"),
                "rate": snap.get("jicha_rate"),
                "city": snap.get("city"),
                "unit": snap.get("unit"),
            }
            if not history or history[-1]["date"] != current["date"]:
                history.append(current)

        if not current and history:
            current = history[-1]

        if not current:
            continue

        previous = None
        for row in reversed(history[:-1] if history and history[-1]["date"] == current["date"] else history):
            if row["date"] < current["date"]:
                previous = row
                break

        enriched.append(
            {
                "category": category,
                "group_name": snap["group_name"],
                "source_date": current["date"],
                "published_today": snap.get("published") == 1 and current["date"] == target_date,
                "city": current["city"],
                "unit": current["unit"],
                "spot_price": current["spot"],
                "futures_price": current["futures"],
                "basis": current["basis"],
                "premium_rate": current["rate"],
                "spot_change": None if previous is None else round(current["spot"] - previous["spot"], 4),
                "futures_change": None if previous is None else round(current["futures"] - previous["futures"], 4),
                "basis_change": None if previous is None else round(current["basis"] - previous["basis"], 4),
                "history": history,
            }
        )

    result = {
        "report_date": target_date,
        "snapshot_date": snapshot["data"]["date"],
        "items": enriched,
    }
    return result


def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    result = enrich_rows(target_date, days)
    json.dump(result, sys.stdout, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
