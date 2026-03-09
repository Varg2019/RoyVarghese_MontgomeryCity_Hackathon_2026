# Phase 1 — Step-by-step: Civic Service Transparency (Read-only)

This document describes exactly how the Phase 1 application will look to users and how it will work behind the scenes, using the City’s public ArcGIS HostedDatasets (read-only) — chiefly the Received_311_Service_Request FeatureService — to ingest existing requests, compute priority/SLA insights, and present a public transparency dashboard.

## What users will see (UI/UX)

- Public landing page
  - KPIs: Open requests, Closed last 30/90 days, Median resolution time, On-time % (derived), Last updated timestamp.
  - Filters: Date range, Status, Category/Subtype, Council District/Neighborhood.
  - Map: Clustered points of requests; color by status or priority; basemap; quick toggles for overlays (City_Limit, sensitive facilities).
  - Request list + detail panel: Selecting a point shows details: description (PII-redacted), created/updated dates, status from source, computed priority score, SLA due-by date, routing suggestion, and any dedupe notes.
  - Download/Open Data: Button to download filtered results as CSV/GeoJSON (with PII removed) + data dictionary link.
  - About data: Methodology, refresh cadence, definitions, and privacy statement.

- Internal (optional) ops view
  - SLA risk queue (due soon/overdue), duplicates suppressed list, workload by category.
  - Same map/lists but with more fields (role-based access).

## How it works (system flow)

1) Scheduler/Trigger
- A job runs every 15–60 minutes (configurable) to refresh data.

2) Incremental ingestion from ArcGIS
- Target: Received_311_Service_Request FeatureServer layer (likely /FeatureServer/0).
- Query strategy: query?where=EditDate>=<last_sync_epoch_ms>&outFields=*&f=json&resultRecordCount=2000&resultOffset=...
- Pagination until all updates are retrieved; handle deleted features via returnDeletes=true if supported, else soft-detect by comparing OBJECTIDs.
- Store raw features to a bronze table (JSON + geometry).

3) Curation and normalization (silver)
- Parse attributes into typed columns (id, created_at, updated_at, status, category, description, location, etc.).
- Standardize category/subtype values; geocode missing coordinates if permissible (fallback minimal for Phase 1).

4) Enrichment and computed fields (gold)
- Jurisdiction check: intersect with City_Limit; flag out-of-bounds.
- Derived geography: district/tract/neighborhood via spatial joins.
- Priority score: rule-based (base severity by category + proximity boosts to schools/health/police/fire + recurrence + keyword boosts). Score 0–100.
- SLA target: set per category/priority (e.g., pothole 3 biz days; drainage higher priority; nuisance 10 biz days). Produce sla_due_at and time_remaining.
- Dedupe: spatial-temporal clustering within a radius/time window + text similarity; assign dedupe_group_id and mark non-lead duplicates as suppressed in aggregates.
- Routing suggestion: department/crew suggestion using ownership (City_Owned_Properities), asset overlays (Maintained_Ditches, Paving_Project), or default by district.

5) Storage options
- Local demo: SQLite/SpatiaLite for fast setup, or a single PostgreSQL/PostGIS instance if available.
- Tables: bronze_raw, requests_silver, requests_gold (with geometry), triage_decisions (audit of computed values), dimension tables for overlays.

6) Read API for the dashboard
- /api/kpis?filters=... -> open, closed, median times, on-time % (computed from status + SLA where applicable), last_updated.
- /api/requests?filters=... -> paginated list with core + computed fields (PII redacted).
- /api/requests.geojson?filters=... -> GeoJSON for the map layer.
- /api/dictionary -> data dictionary of fields.

7) Frontend/dashboard
- Static site (React/Vite or simple HTML + MapLibre) fetches KPIs and GeoJSON.
- Map renders points, clustering, theming by priority/status; detail drawer shows record + computed fields.
- Download buttons hit API endpoints to export current filter set.

8) Refresh and transparency
- Timestamp of last successful sync shown on page.
- All computed fields tagged with version (triage_version) for auditability.

## Data model (minimal)

- requests_gold
  - object_id (from FeatureService), source_layer, created_at, updated_at, status, category, subtype, description_redacted
  - geom, district, tract
  - priority_score (0–100), sla_due_at, time_remaining_minutes
  - routing_suggestion, dedupe_group_id, triage_version, valid_within_city (bool)

- triage_decisions
  - decision_id, object_id, decided_at, rules_fired, priority_components_json, sla_policy_id, routing_rule_id

- dimensions (optional)
  - districts, tracts, sensitive_sites, ownership_layers metadata

## Privacy & security

- Strip requester names, phone, email, exact addresses if present; display generalized location (block-level if needed) on the public site.
- Suppress counts for very small areas to avoid reidentification; public exports are PII-free.

## Deployment options for Phase 1

- Local demo: Run the worker (Node/Python) + a lightweight API (Express/FastAPI) + static frontend. Suitable for demonstration.
- Cloud (recommended for pilot): Host API on a small container/app service; serve the frontend as static files (CDN). DB: managed Postgres or a small VM.

## Acceptance criteria (Phase 1)

- Data ingestion succeeds on schedule and on demand; failures alert to logs.
- Dashboard displays: KPIs, map, filters, request list, and detail panel with computed fields.
- Computed fields visible: priority_score, sla_due_at/time_remaining, routing_suggestion, dedupe_group flag.
- Public export available as CSV/GeoJSON with PII removed; data dictionary provided.
- Last updated timestamp accurate; performance acceptable (<3s for key queries on city-wide filters).

## Timeline (2–3 weeks for a working demo)

- Days 1–3: Confirm layer schema; build incremental ingestion; stand up DB; ingest initial history (bounded by last 90–180 days).
- Days 4–6: Implement triage rules, SLA calculator, dedupe, routing suggestions; write decision logs.
- Days 7–9: Build KPIs/GeoJSON API endpoints; implement frontend map + filters + detail panel.
- Days 10–12: Privacy review, PII redaction, performance tuning, documentation; deploy pilot.

## Notes on access and feasibility

- Feasibility: Confirmed. Public read access to the ArcGIS FeatureServer endpoints is sufficient to implement Phase 1 now (read-only). No city system write credentials are needed, as we mirror source statuses and add computed insights locally.
- Limitations: Without write-back, we do not alter official statuses — we display them as-is and compute SLA risk and priorities for transparency.

## Example URLs to validate during setup

- Folder listing (already validated):
  https://gis.montgomeryal.gov/server/rest/services/HostedDatasets?f=pjson
- Service info:
  https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Received_311_Service_Request/FeatureServer?f=pjson
- Layer 0 schema:
  https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Received_311_Service_Request/FeatureServer/0?f=pjson
- Sample latest 10 (GeoJSON):
  https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Received_311_Service_Request/FeatureServer/0/query?where=1%3D1&outFields=*&orderByFields=EditDate%20DESC&resultRecordCount=10&f=geojson

## Next step

- If approved, I will scaffold the repo with:
  - /ingestion: incremental fetcher + schema mappers
  - /api: endpoints for KPIs, lists, and GeoJSON
  - /web: static dashboard (map + KPIs + filters)
  - /docs: data dictionary and configuration guide

This will produce a working Phase 1 application demo using public endpoints.
