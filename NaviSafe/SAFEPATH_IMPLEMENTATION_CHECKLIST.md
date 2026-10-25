# SafePath implementation checklist

This checklist is derived from `safepath_ux_case_study_agent_spec.md`. It tracks the first build milestone and the remaining product work without treating simulated browser capabilities as delivered integrations.

## First milestone — completed

- [x] Responsive SafePath application shell with desktop sidebar and mobile bottom navigation.
- [x] Five primary destinations are visible and linked: Home, Navigate, Community, Check-in, and Profile.
- [x] Home dashboard has honest safety status, quick actions, community preview, and check-in entry point.
- [x] Offline banner uses browser connectivity signals and explains the limited mode.
- [x] Existing map route planner remains available under Navigate.
- [x] Existing analytics and reporting functionality remains reachable.
- [x] Community create/update flow is reachable under Community.
- [x] PWA manifest, theme metadata, app description, and service worker are configured.
- [x] App shell has a cache-first fallback for repeat visits and offline startup.
- [x] Visual system moved from dense neon glassmorphism to calm, high-contrast cards with semantic status colors.
- [x] Mobile safe-area spacing and touch-sized navigation targets are included.
- [x] Public landing page explains the product, capabilities, and limitations before account creation.
- [x] Create-account and sign-in flows validate input and persist a local demo account.
- [x] Three-step onboarding captures preferences, trusted-contact intent, and permission decisions.
- [x] Community upload/report page redesigned with categories, 50-character note validation, drag/drop image selection, privacy guidance, real submission state, and offline queue fallback.
- [x] Check-in flow supports destination, duration, optional contact, persisted deadline, countdown, safe completion, and cancellation.
- [x] Profile view exposes local account information, preference/settings links, saved-route/help placeholders, and local-data reset.
- [x] Landing page redesigned as a responsive product introduction with scroll-aware navigation, mobile menu, animated visual preview, interactive route/check-in/community tabs, product story, privacy framing, and account CTAs.

## Next implementation slices

### Onboarding and persistence

- [ ] Split the current three-step setup into the full named route sequence: `/onboarding/intro`, `/preferences`, `/contacts`, `/location`, `/notifications`, `/privacy`, `/how-it-works`, and `/get-started`.
- [ ] Persist onboarding completion and editable preferences locally.
- [ ] Add permission explainers before geolocation or notification requests.
- [ ] Add trusted-contact add, edit, reorder, and removal states.

### Navigation safety flow

- [ ] Split search, route options, active navigation, arrival, and no-route into stable nested routes.
- [ ] Add manual origin fallback, route freshness, provider limitations, and loading/error/empty states.
- [ ] Add explicit deviation recovery and an always-reachable emergency action.
- [ ] Add arrival confirmation and optional post-arrival contribution.

### Check-in and emergency

- [ ] Add persisted check-in entity with deadline-based reconciliation on launch and visibility changes.
- [ ] Add active timer, extend, cancel, safe confirmation, overdue, and truthful escalation fallback states.
- [ ] Add emergency action panel with `tel:` links only after user action.
- [ ] Add last-location consent and freshness metadata where location is actually available.

### Community and sync

- [ ] Add feed, contributions, queued updates, drafts, retry, and conflict resolution views.
- [ ] Store drafts and queued mutations in IndexedDB with idempotency keys.
- [ ] Distinguish local save, queued-for-sync, syncing, synced, failed, and conflict statuses.
- [ ] Enforce the 50-character note limit and prevent duplicate submissions.

### PWA and quality

- [ ] Add supported install prompt and update-available refresh flow.
- [ ] Add explicit icon sizes and maskable raster assets when product artwork is available.
- [ ] Verify direct-route hosting fallback for production deployment.
- [ ] Add state-machine tests and critical journey integration tests.
- [ ] Document provider adapters, environment variables, demo limitations, and PWA testing.

## Validation commands

```text
cd frontend
npm run build
npm run lint
npm run preview
```

The current frontend build passes. The app still uses the existing backend/map adapters and should not claim real-time delivery, background tracking, SMS, or emergency dispatch until those integrations are configured.

## Backend startup

The API defaults to port `8000`. If that port is already occupied, do not start a second copy on the same port. Reuse the existing server or choose another port:

```powershell
# Check the process currently using port 8000
Get-NetTCPConnection -LocalPort 8000 -State Listen

# Start a second API instance on another port
$env:SAFEPATH_PORT = "8001"
python main.py
```

The process-based frontend proxy is configured for port `8000`; update the proxy target in `frontend/vite.config.ts` if you intentionally run the API on another port.
