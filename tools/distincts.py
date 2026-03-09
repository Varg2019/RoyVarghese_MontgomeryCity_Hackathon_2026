import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sample_path = ROOT / "data" / "sample_attrs.json"
out_dir = ROOT / "data"
out_dir.mkdir(parents=True, exist_ok=True)

def load_attrs():
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    return [f.get("attributes", {}) for f in data.get("features", [])]

def distincts(values):
    vals = [v for v in values if v not in (None, "")]
    return sorted(set(vals)), Counter(vals)

def main():
    feats = load_attrs()
    depts, dept_counts = distincts([a.get("Department") for a in feats])
    types, type_counts = distincts([a.get("Request_Type") for a in feats])
    statuses, status_counts = distincts([a.get("Status") for a in feats])
    origins, origin_counts = distincts([a.get("Origin") for a in feats])

    (out_dir / "distinct_departments.json").write_text(
        json.dumps({
            "count": len(depts),
            "values": depts,
            "top20": dept_counts.most_common(20),
        }, indent=2), encoding="utf-8"
    )
    (out_dir / "distinct_request_types.json").write_text(
        json.dumps({
            "count": len(types),
            "values": types,
            "top20": type_counts.most_common(20),
        }, indent=2), encoding="utf-8"
    )
    (out_dir / "distinct_statuses.json").write_text(
        json.dumps({
            "count": len(statuses),
            "values": statuses,
            "top20": status_counts.most_common(20),
        }, indent=2), encoding="utf-8"
    )
    (out_dir / "distinct_origins.json").write_text(
        json.dumps({
            "count": len(origins),
            "values": origins,
            "top20": origin_counts.most_common(20),
        }, indent=2), encoding="utf-8"
    )
    print("Wrote distincts to data/ (departments, request_types, statuses, origins)")

if __name__ == "__main__":
    main()
