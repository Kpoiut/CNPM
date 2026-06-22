# UI/UX Redesign Direction — AVM Production Runtime

Updated: 2026-06-22

## Visual direction from Image Codex drafts

The redesign direction is a premium Vietnamese proptech SaaS interface:

- deep navy operational shell with bright white work surfaces;
- cyan/blue primary actions, emerald success/trust states, amber warning states;
- glass-line icon language, rounded geometry, soft glow used sparingly;
- clear role separation:
  - public/login focuses on trust, security, OAuth, and conversion;
  - user workspace focuses on guided valuation, map context, confidence, and history;
  - admin workspace focuses on operations, data governance, model monitoring, and auditability.

The generated Image Codex mockups are visual direction only. Production assets should be rebuilt as lightweight SVG/CSS/components instead of embedding heavy raster UI screenshots.

Image Codex concept pass on 2026-06-21 added a three-screen product board:

- Prediction workspace: compact enterprise form, sticky role-aware right rail, and five tabs (`Hồ sơ`, `Định vị`, `Kết quả`, `So sánh`, `Audit`) treated as one continuous workflow.
- Login: security-first page with Google OAuth 2.0 CTA, JWT/session trust cues, and role explanation without exposing secrets.
- Admin operations: related but denser shell for data/model/governance work, with operational status and model lineage always visible.

Implementation gate: do not replace the full UI until the current public, user, and admin screenshots are captured and reviewed. The Prediction page must be audited per property type and per sub-tab because it contains nested state, role-only controls, map/media panels, and result diagnostics.

Image Codex concept pass on 2026-06-22 tightened the direction into a production cockpit:

- graphite/white surfaces with teal, emerald and amber accents; avoid purple hero gradients and decorative radial orbs;
- Prediction shows role, PostgreSQL/PostGIS scope, serving model version and cached response target before the tab workflow;
- Login becomes an access console for OAuth/JWT/PostgreSQL/CI evidence instead of a broad marketing hero;
- admin/user keep one shared component language, but admin surfaces operational depth while user screens stay guided.

## Screen priorities

1. Login
   - Security-first layout.
   - Google OAuth 2.0 button as an integration affordance.
   - No secrets or real provider keys embedded in frontend code.

2. Prediction workspace
   - Preserve the multi-step/sub-tab nature of valuation.
   - Make role differences explicit:
     - user: guided, minimal, confidence explained simply;
     - admin: expert mode with provenance, pipeline, model, and diagnostics.
   - Always separate official holdout-test model metrics from live PostgreSQL residual diagnostics.

3. Admin operations
   - Keep five top-level areas:
     - Overview
     - Data Operations
     - Model Operations
     - Governance
     - Settings/Platform
   - Reduce duplicated data pages by using child actions/tabs inside Data Operations.

## Redesign execution order

1. Baseline audit
   - Run `npm run audit:ui` for `UI_AUDIT_ROLE=public`, `user`, and `admin`.
   - Keep the latest screenshot manifest under `reports/ui-audit/baseline/<timestamp>/`.
   - Treat any `failedCount`, page error, clipped text, or role leakage as a blocker.

2. Prediction workspace
   - Preserve every current sub-flow before visual polish: property type switch, map tab, result tab, comparables, pipeline/audit, impact/admin-only panel, file upload, and summary rail.
   - User mode should be guided and low-noise. Admin mode should expose provenance, metric source, model version, cache state, and audit controls.

3. Login
   - Keep username/password and register flows.
   - Google OAuth button must call backend `/api/auth/google/start`; no provider secret may appear in frontend source or bundled output.

4. Admin key pages
   - Redesign overview, data overview/records/sources/quality/provenance, model experiments/explainability, governance community/accounts as one operations family.
   - Avoid separate visual languages per page.

## Icon system

Use a custom icon family derived from the Image Codex direction:

- home/property
- valuation
- map
- data operations
- data quality
- model training
- explainability
- governance
- user permissions
- security/OAuth
- audit logs
- deployment/cloud

Implementation rule: rebuild icons as SVG components or existing code-native primitives. Do not ship generated bitmap icon sheets as primary UI icons.

## Metric copy rules

Use these labels consistently:

- `Serving Official Test MAPE`: holdout-test metric from the model currently pinned by `models/ACTIVE_MODEL.json`. Current serving value: `16.09%` for `20260504_144753`.
- `Best Historical MAPE`: lowest official test MAPE among retained metadata snapshots. Current best-by-MAPE history: `14.20%` for `20260503_185414`, shown as historical benchmark unless explicitly activated.
- `Live DB MAPE`: diagnostics recomputed on the current PostgreSQL records. This may be higher and is used for drift/data quality monitoring.
- `Latest retrain MAPE`: only shown with model timestamp/version and never presented as serving metric unless activated.

This prevents repeating the earlier confusion where 14.20%, 16.09%, 42.42%, 45.5%, and live residual percentages were compared without scope/version.

## Performance direction

- Keep route-level code splitting.
- Split the Prediction chunk further by lazy-loading map, impact analysis, 3D visualizer, and heavy chart panels.
- Replace repeated heavy fetches with cached React Query queries and stable query keys.
- Use PostgreSQL indexes/materialized summaries for admin overview and explainability diagnostics.
- Target perceived response under 200ms for cached/shell interactions; long ML diagnostics must show immediate progressive states.
- Enforce `npm run build:check` before release:
  - app shell initial JS <= 480 KB;
  - Prediction <= 170 KB;
  - Login <= 40 KB;
  - Property visualizer shell <= 40 KB;
  - 3D dynamic entry <= 40 KB;
  - react-three lazy vendor <= 220 KB;
  - three-core lazy vendor <= 700 KB.
