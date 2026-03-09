from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import re

import duckdb

from backend.db import get_con


REQUIRED_COLS = [
    "Request_ID",
    "Create_Date",
    "Close_Date",
    "Status",
    "Request_Type",
    "Department",
    "Origin",
    "District",
    "Latitude",
    "Longitude",
]


def ingest_csv(csv_path: Path) -> Dict[str, Any]:
    """Load CSV into DuckDB raw temp view, transform into tickets table with derived fields.

    Returns a summary dict per FR-ING-03.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    con = get_con()

    # Load CSV into a temp/raw table inside the same connection used for inserts.
    # DuckDB does not support prepared parameters in this type of statement.
    safe_path = str(csv_path).replace("'", "''")
    con.execute("drop view if exists v_raw")
    con.execute("drop table if exists tickets_raw")
    con.execute(f"create table tickets_raw as select * from read_csv_auto('{safe_path}', header=true)")

    # Validate required columns
    cols = [r[0] for r in con.execute("select column_name from information_schema.columns where table_name='tickets_raw'").fetchall()]
    missing = [c for c in REQUIRED_COLS if c not in cols]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Safe overwrite of tickets table
    con.execute("delete from tickets")

    # Transform and insert
    con.execute(
        """
        insert into tickets
        select
            cast(Request_ID as varchar) as Request_ID,
            cast(Create_Date as bigint) as Create_Date,
            cast(Close_Date as bigint) as Close_Date,
            cast(Status as varchar) as Status,
            cast(Request_Type as varchar) as Request_Type,
            cast(Department as varchar) as Department,
            cast(Origin as varchar) as Origin,
            cast(District as varchar) as District,
            try_cast(Latitude as double) as Latitude,
            try_cast(Longitude as double) as Longitude,
            -- derived
            to_timestamp(CAST(Create_Date AS double)/1000.0) as created_at,
            case when Close_Date is null then null else to_timestamp(CAST(Close_Date AS double)/1000.0) end as closed_at,
            case when Close_Date is not null and cast(Status as varchar) ilike '%closed%'
                 then date_diff('hour', to_timestamp(CAST(Create_Date AS double)/1000.0), to_timestamp(CAST(Close_Date AS double)/1000.0))
                 else null end as resolution_hours,
            case when Close_Date is null or not (cast(Status as varchar) ilike '%closed%')
                 then date_diff('hour', to_timestamp(CAST(Create_Date AS double)/1000.0), now())
                 else null end as age_hours,
            EXTRACT(MONTH from to_timestamp(CAST(Create_Date AS double)/1000.0))::INT as create_month,
            EXTRACT(dow from to_timestamp(CAST(Create_Date AS double)/1000.0))::INT as create_dow
        from tickets_raw
        """
    )

    # Summary metrics
    total = con.execute("select count(*) from tickets").fetchone()[0]
    pct_closed = con.execute(
        "select 100.0 * sum(case when Status ilike '%closed%' then 1 else 0 end)/nullif(count(*),0) from tickets"
    ).fetchone()[0]
    pct_invalid_geo = con.execute(
        """
        select 100.0 * sum(case when Latitude is null or Longitude is null or (abs(Latitude) < 1e-6 and abs(Longitude) < 1e-6) then 1 else 0 end)/nullif(count(*),0)
        from tickets
        """
    ).fetchone()[0]

    top_types = con.execute(
        "select Request_Type, count(*) as c from tickets group by 1 order by c desc limit 10"
    ).fetchall()
    top_depts = con.execute(
        "select Department, count(*) as c from tickets group by 1 order by c desc limit 10"
    ).fetchall()

    summary = {
        "total_rows": int(total or 0),
        "pct_closed": float(pct_closed or 0.0),
        "pct_invalid_geo": float(pct_invalid_geo or 0.0),
        "top_request_types": [{"Request_Type": r[0], "count": int(r[1])} for r in top_types],
        "top_departments": [{"Department": r[0], "count": int(r[1])} for r in top_depts],
    }

    return summary
