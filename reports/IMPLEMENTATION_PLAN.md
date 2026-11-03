# Implementation plan and baseline audit — 20 October 2026

1. Preserve React 19 / TypeScript / Vite / React Router / Leaflet, FastAPI, NetworkX, pandas and LightGBM. Backup source before edits; retain all legacy datasets/uploads and existing route/graph/report contracts.
2. Extend the existing responsive shell and landing page. Complete onboarding, real community feed/drafts/contributions, navigation/arrival/recovery, check-in/history, profile/settings and emergency actions.
3. Add IndexedDB outbox with image blobs, idempotency, explicit conflicts, install/update controls and static-only service-worker caching.
4. Audit every CSV, document source licensing and Dwarka-only geographic coverage. Preserve legacy generation; add reproducible manifests and refuse destructive output reuse.
5. Replace resubstitution training with chronological, non-overlapping snapshot horizons and geographically held-out groups, training-only preprocessing, validation-selected thresholds and untouched final evaluation. Save separate versioned artifacts.
6. Add private image storage, decoded-content validation, hashes/quality/metadata signals, independent corroboration, moderation state machine, permissions, audit history and review requests. Never use community reports as automatic training labels.
7. Exercise build/lint, API/evidence tests, ML split/inference tests, responsive/browser/PWA journeys and document real results and dependencies.

## Baseline findings
- No Git repository or existing tests, dependency pins, deployment config or saved model artifact found.
- Frontend production build passes (604 kB main JS chunk warning). Lint initiated separately.
- Existing Python routing mutates shared graph state and uses report_propensity as fallback risk; geospatial snapping uses raw degree distances.
- Legacy trainer filters synthetic truth spam labels, fits all observations, predicts on the same rows and saves only a risk table. No valid held-out accuracy exists.
- Legacy CSV reports and two uploads are preserved as unreviewed legacy records, never imported as verified ground truth.
- Existing onboarding does not save phone contacts or request permissions; feed has illustrative observations without disclosure; emergency action points to report form.
- Existing PWA caches all requests and automatically activates updates. Existing local check-in persists deadline but has no overdue/history/escalation workflow.
- Supplied reference images reviewed: five primary destinations, eight onboarding stages, route comparison/arrival, silent check-in, evidence contributions and recovery states. Keep website-first desktop layouts and mobile bottom navigation.
