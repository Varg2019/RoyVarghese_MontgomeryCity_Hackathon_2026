Civic Service Triage & Transparency Agent (Montgomery, AL)

Overview
This plan uses the City’s ArcGIS HostedDatasets to triage incoming service requests, route them to the right teams with service-level targets, and make outcomes transparent to residents and leadership.

Phased Delivery (Requested)
- Phase 1: Read-only transparency and prioritization for existing 311 requests
  - Ingest existing records from Received_311_Service_Request (FeatureServer), enrich each record with computed fields (priority score, suggested SLA, dedupe flag, routing suggestion), and publish a public dashboard that reflects current status from the source plus the computed insights. No write-back to city systems required.
  - Outputs: public-facing dashboard (map + KPIs), downloadable open data (PII-redacted), and internal ops view (SLA risk queue). Runs on a scheduled sync (e.g., every 15–60 minutes) to keep data fresh.
- Phase 2: Live triage of new online 311 submissions
  - Intercept or receive webhooks for new requests as they are submitted; apply validation, classification, dedupe, scoring, and routing in real-time; set SLAs; optionally create or update tickets in the city’s CRM/work order systems; notify residents of status changes.
  - Adds write-back/adapters, live notifications, and configurable rules/ML augmentation.

1) Objectives and Success Criteria
- Triage: Auto-classify, validate, prioritize, and route incoming service requests with clear SLAs and audit logs.
- Transparency: Near real-time dashboards for request volumes, backlogs, service times, and geographic equity.
- Accountability: Track all decisions and status changes; publish standardized open data (PII-redacted).
- Insight: Detect hotspots, recurring issues, and opportunities for proactive maintenance.

Example success metrics
- 30% reduction in median time-to-first-action within 3–6 months.
- 60% fewer misrouted tickets within 2 months.
- +20% on-time SLA attainment across key categories.

2) Key ArcGIS Datasets (HostedDatasets)
Operational feeds
- Received_311_Service_Request (primary intake)
- Code_Violations, Nuisance (compliance and abatement workloads)
- Maintained_Ditches (drainage inventory + work history)
- Paving_Project (road segments and program status)
- Grass_Cutting_for_State_Owned_Properties (grounds maintenance)

Context/validation layers
- City_Limit (jurisdiction check)
- City_Owned_Properities (ownership, facilities/public works routing)
- Business_License (business attributes)
- Utility_Poles_Report_Locations (safety/infrastructure context)
- Community_Centers, Libraries, Education_Facilities, Daycare_Centers, Health_Care_Facility (sensitive/public facilities for proximity-based prioritization)
- Fire_Stations, Police_Facilities, Tornado_Sirens (response context)

Note: Each service is available as FeatureServer (best for queries/sync) and MapServer.

3) Reference Architecture
- Intake: 311 channels feed the Received_311_Service_Request FeatureService layer; optional web/SMS form to a staging API.
- Ingestion & Sync: A worker (Python/FastAPI or Node/Express) performs incremental fetches from FeatureServer layers into Postgres/PostGIS.
- Data layers: Bronze (raw GIS mirror), Silver (curated/normalized), Gold (analytics-ready facts/dimensions).
- Triage Engine: Validation, classification, deduplication, priority scoring, routing, and SLA assignment.
- Work Assignment: Adapters push assignments to department systems and receive status updates.
- Transparency: Public dashboards and internal ops views; open data publishing.
- Security/Privacy: PII minimization/redaction; role-based access for internal details.

4) Data Flow (Text)
1. 311 request -> ArcGIS Received_311_Service_Request (FeatureServer)
2. Ingestion worker pulls new/updated features -> PostGIS bronze
3. Transform to silver/gold -> Triage engine consumes gold + context layers
4. Outputs: priority, route, SLA, dedupe flag -> persisted + decision log
5. Assignment adapter pushes to department systems -> statuses synced back
6. Dashboards query gold and/or live FeatureServer for maps/symbology
7. Public transparency site exposes KPIs and redacted request data

5) Triage Logic (Rules + Scoring)
Validation
- Inside City_Limit (unless explicitly supported like certain state properties)
- Location present and valid geometry; required fields populated

Classification (examples)
- “Pothole”, “street damage” -> Public Works / Paving
- “Tall grass”, “overgrown” -> Grounds / Nuisance
- “Illegal dumping”, “debris” -> Solid Waste / Code Enforcement
- “Blocked ditch/drainage” -> Drainage / Maintained_Ditches

Priority score (0–100) components (illustrative)
- Base severity by category (e.g., drainage=40, pothole=30, tall grass=15)
- Proximity amplifiers (+5 to +20) if within 250–500 ft of schools/daycares, health facilities, fire/police, seniors centers, etc.
- Recurrence boost if similar requests at same location in last 60 days (+10)
- Safety keywords in description (e.g., “injury”, “electrical”, “collapse”) (+10)
- Weather intensifier (future): active heavy-rain window -> drainage +15

Deduplication
- Spatial/temporal clustering and text similarity to suppress duplicates while keeping an audit trail.

Routing (sketch)
- If inside City_Owned_Properities and category=Facilities -> Facilities Dept
- If road asset and category=Paving -> route by zone/segment
- If drainage and intersects Maintained_Ditches -> route by drainage zone/crew
- Else route by district grid and nearest depot/crew; consider workload balancing

SLA examples (tunable)
- Life-safety hazard: 4–8 hours
- Road hazard (pothole): 3 business days
- Nuisance/tall grass: 10 business days
- Code violation: per ordinance (notice -> reinspection cadence)

6) Transparency: KPIs & Views
Public portal
- Live map of 311 requests (filters by category/status/date); requester info anonymized.
- KPI cards: Open, Closed (30/90d), Median resolution time, On-time %.
- Equity lens: service time distribution by district/tract with context notes.
- Program trackers: Paving segments; ditch maintenance cycles; code case aging.

Internal ops
- SLA risk queue (due soon/overdue), duplicate suppression metrics, re-open rates.
- Crew dashboards: daily worklist and optimized routing suggestions.

Open data
- Publish JSON/CSV/GeoJSON of request statuses/outcomes with a data dictionary; suppress small-N and PII.

7) ArcGIS FeatureServer Integration Patterns
- Service info (layers):
  https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Received_311_Service_Request/FeatureServer?f=pjson
- Layer schema (index 0 example; verify indices):
  https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Received_311_Service_Request/FeatureServer/0?f=pjson
- Sample recent features (GeoJSON):
  https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Received_311_Service_Request/FeatureServer/0/query?where=1%3D1&outFields=*&orderByFields=EditDate%20DESC&resultRecordCount=10&f=geojson
- Incremental sync since timestamp (EditDate >= epoch_ms): add where=EditDate%3E%3D<epoch_ms>; returnIdsOnly=true for fast change detection.

Phase 1 specifics
- Read-only ingestion from Received_311_Service_Request plus context layers (City_Limit, facilities, ditches, paving, etc.).
- Compute and store: priority_score, sla_due_at (based on category/priority), routing_suggestion, dedupe_group_id, and derived geographic attributes (district/tract).
- Dashboards reflect the source “status” field (no writes) and overlay computed insights; public views apply PII redaction and small-N suppression.

8) Data Model (Gold layer examples)
- requests_fact: request_id, source_layer, object_id, created_at, updated_at, geom, category, subcategory, description, status, status_reason, assigned_dept, assigned_crew, sla_due_at, priority_score, dedupe_group_id, triage_version
- triage_decisions: decision_id, request_id, decided_at, rules_fired, model_version, priority_components, assigned_to, comments
- context_dimensions: assets (ditches, roads, facilities), service areas/zones, neighborhoods/districts/tracts
Indexes: spatial index on geom; btree on created_at, status, priority_score

9) Tech Stack Options
- Ingestion/ETL: Python (requests, arcgis, pandas, geopandas) or Node (node-fetch/axios, esri-leaflet)
- API: FastAPI or Express with OpenAPI
- DB: Postgres + PostGIS; job queue: RQ/Celery (Python) or BullMQ (Node)
- Dashboards: Apache Superset/Metabase for quick start; or custom React + MapLibre/ArcGIS JS API
- Hosting: Azure/AWS/GCP or on-prem; schedule workers with cron/Functions

10) MVP (4–6 weeks)
Week 1: Confirm schemas; stand up Postgres/PostGIS; incremental fetch for Received_311_Service_Request
Week 2: Implement rule-based triage for 2–3 categories (potholes, drainage, tall grass); SLA timers; decision logs
Week 3: Internal ops dashboard (queue + SLA risk); public map (anonymized open requests)
Week 4: Email notifications on status change; duplicate detection v1; publish open dataset + data dictionary
Weeks 5–6 (stretch): Integrate Code_Violations/Nuisance; overlays for maintenance inventories; equity KPIs; optional ML scoring + crew route optimization

11) Governance, Privacy, Equity
- Data governance: dataset stewards; freshness SLAs; change logs
- Privacy: requester PII redaction in public; small-N suppression; role-based internal access
- Equity: monitor service time distributions; investigate gaps; adjust routing and SLAs
- Auditability: log automated decisions with rationale and versioning

12) Risks & Mitigations
- Schema drift in FeatureServices -> nightly schema checks/alerts; versioned mappers
- Rate limits/outages -> caching, backoff/retry, and local mirrors
- Data quality issues -> validation rules, fallbacks, and operator review queue
- Change management -> SOPs, training, phased rollout with pilots

13) Next Actions
1. Validate layer indices and key fields for: Received_311_Service_Request, Nuisance, Code_Violations, Maintained_Ditches, Paving_Project, City_Limit
2. Approve MVP categories, SLAs, and routing matrix with departments
3. Stand up Postgres/PostGIS and bootstrap ingestion worker
4. Build triage rules and internal dashboard; publish first public transparency page

Access and Feasibility (Phase 1)
- Current access: We have public, read-only access to the ArcGIS REST services (FeatureServer/MapServer) at gis.montgomeryal.gov, including the HostedDatasets folder and the Received_311_Service_Request layer for ingestion and enrichment.
- What’s sufficient for Phase 1 to be a workable application:
  - Read access to Received_311_Service_Request (confirmed) and context layers.
  - Permission to host a public dashboard (can be done via a static site + an API or a BI tool like Superset/Metabase).
  - No need for write-back credentials in Phase 1; statuses shown are mirrored from the source and augmented with computed fields locally.
- Constraints: Without write access, we cannot change official request statuses in the city system, but we can compute and display priority, SLA targets, and routing suggestions while reflecting the latest source status for transparency.
- Deliverability: With current public endpoints, we can implement Phase 1 now as a read-only transparency and prioritization app and deploy a working demo (local or cloud) within the MVP timeline.

Appendix: Example Triage Pseudocode
for req in new_requests:
    # Validation
    if not inside_city_limit(req.geom) or not has_required_fields(req):
        route_to_intake_review(req)
        continue
    # Classification
    req.category = classify(req.text, req.subtype)
    # Priority
    score = base_severity(req.category)
    score += proximity_boost(req.geom, sensitive_sites)
    score += recurrence_boost(req.location_hash)
    score += keyword_boost(req.text)
    req.priority_score = min(max(score, 0), 100)
    # Dedupe
    req.dedupe_group_id = find_nearby_similar(req)
    # Routing & SLA
    req.assigned_dept, req.assigned_crew = route(req.category, req.geom, ownership_layers)
    req.sla_due_at = set_sla(req.category, req.priority_score)
    # Persist & notify
    log_decision(req)
    push_assignment(req)
