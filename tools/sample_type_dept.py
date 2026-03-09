import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SRC = DATA / "sample_attrs.json"
OUT_CSV = DATA / "request_type_department_sample.csv"
OUT_JSON = DATA / "request_type_department_sample.json"


def main(limit: int = 500):
    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []
    for f in data.get("features", []):
        a = f.get("attributes", {})
        req = a.get("Request_Type")
        dept = a.get("Department")
        if not req or not dept:
            continue
        rows.append({
            "request_type": str(req),
            "department": str(dept),
            "status": a.get("Status"),
            "origin": a.get("Origin"),
            "create_date": a.get("Create_Date"),
            "close_date": a.get("Close_Date"),
            "year": a.get("Year"),
        })
        if len(rows) >= limit:
            break

    # Write CSV
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()) if rows else ["request_type","department"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Write JSON
    OUT_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} records to {OUT_CSV} and {OUT_JSON}")


if __name__ == "__main__":
    main()
