from __future__ import annotations

import duckdb
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "mgm_311.duckdb"


def get_con(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Allow multiple connections in the same app/runtime by disabling the single-process file lock behavior.
    return duckdb.connect(str(DB_PATH), config={"access_mode": "AUTOMATIC"})


def init_tables():
    con = get_con()
    con.execute(
        """
        create table if not exists tickets (
            Request_ID varchar primary key,
            Create_Date bigint,
            Close_Date bigint,
            Status varchar,
            Request_Type varchar,
            Department varchar,
            Origin varchar,
            District varchar,
            Latitude double,
            Longitude double,
            -- derived
            created_at timestamp,
            closed_at timestamp,
            resolution_hours double,
            age_hours double,
            create_month int,
            create_dow int
        );
        """
    )

    con.execute("create sequence if not exists sla_config_seq start 1")
    con.execute("create sequence if not exists subscriptions_seq start 1")
    con.execute("create sequence if not exists demo_events_seq start 1")

    con.execute(
        """
        create table if not exists sla_config (
            id bigint primary key default nextval('sla_config_seq'),
            scope varchar, -- 'Request_Type' or 'Department'
            key varchar,
            target_days double,
            effective_date date,
            notes varchar
        );
        """
    )

    con.execute(
        """
        create table if not exists subscriptions (
            id bigint primary key default nextval('subscriptions_seq'),
            email varchar,
            request_id varchar,
            created_at timestamp default current_timestamp
        );
        """
    )

    con.execute(
        """
        create table if not exists demo_events (
            id bigint primary key default nextval('demo_events_seq'),
            request_id varchar,
            event_type varchar, -- 'status_change' | 'override' | 'confirm_correct'
            payload json,
            created_at timestamp default current_timestamp
        );
        """
    )

    con.execute(
        """
        create table if not exists model_metadata (
            name varchar,
            version varchar,
            trained_at timestamp
        );
        """
    )

    con.close()
