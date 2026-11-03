# SafePath --- Product UX, Information Architecture & Implementation Specification

**Audience:** AI coding agent / frontend implementation agent\
**Product:** SafePath safety and route-awareness platform\
**Delivery target:** Responsive website that is also installable as a
Progressive Web App (PWA)\
**Source of truth:** The supplied "Information Architecture" and "User
Flow" diagrams. Preserve their named screens, branches, actions, and
failure paths. Adapt the app-oriented diagrams to web navigation and PWA
behavior without removing product functionality.

------------------------------------------------------------------------

## 1. Mission and implementation rules

Build SafePath as a safety-oriented route-awareness experience. The
product lets users choose a safer route, navigate, perform a silent
check-in, contact trusted people in an emergency, and contribute safety
updates to the community.

### Non-negotiable requirements

1.  Implement the complete information architecture and every user-flow
    branch described in this document.
2.  Build a **website first**, with responsive layouts for desktop,
    tablet, and mobile. The same application must be installable and
    usable as a **PWA**.
3.  Do not treat this as a collection of static mockups. Buttons, forms,
    route branches, offline states, timers, and status changes must
    work.
4.  Keep navigation and state consistent across direct URL visits,
    browser back/forward, refresh, and PWA launches.
5.  Make safety-critical states unmistakable and accessible. Never
    communicate that an alert, check-in, route, or message succeeded
    unless the relevant operation actually succeeded.
6.  If a real backend, map provider, location permission, notification
    permission, or SMS/calling integration is unavailable, create a
    clear adapter/interface and an honest demo state. Do not fake
    real-world delivery or tracking.
7.  Preserve the diagram's functional labels. Minor copy improvements
    are acceptable, but do not silently remove or merge a named node.
8.  Persist appropriate user preferences and queued work. Clearly
    distinguish locally saved data from server-synced data.
9.  Use realistic loading, empty, permission-denied, offline, retry, and
    error states.
10. Do not request location or notification permissions without
    explaining why and obtaining a user action.

------------------------------------------------------------------------

## 2. Product structure at a glance

### Root application

-   **SafePath Mobile App** is the root product node in the IA.
-   Two major areas branch from it:
    -   **Onboarding**
    -   **Main App**

### Main app shell

-   Persistent **Bottom Navigation** in the mobile experience. On wider
    screens, adapt this to a left rail or compact top-level navigation
    while retaining the same five destinations.
-   Destinations:
    1.  **Home**
    2.  **Navigate**
    3.  **Community**
    4.  **Check-in**
    5.  **Profile**
-   A global **Special States & Modals** layer can appear over any
    relevant page.
-   **Background Services** run as app services where browser/PWA
    capabilities and permissions allow.

### Information architecture diagram --- exact hierarchy

``` text
SAFEPATH MOBILE APP
├── ONBOARDING
│   ├── INTRO
│   │   ├── 1. SPLASH SCREEN
│   │   ├── 2. PREFERENCES
│   │   └── 3. CONTACTS
│   ├── SETUP
│   │   ├── LOCATION
│   │   ├── NOTIFICATIONS
│   │   └── PRIVACY
│   └── ONBOARD
│       ├── HOW IT WORKS
│       └── GET STARTED
│
└── MAIN APP
    └── BOTTOM NAVIGATION
        ├── HOME
        │   ├── DASHBOARD
        │   ├── QUICK ACTIONS
        │   ├── SAFETY STATUS
        │   └── FEED PREVIEW
        ├── NAVIGATE
        │   ├── SEARCH
        │   ├── ROUTE OPTIONS
        │   ├── ACTIVE NAV
        │   └── ARRIVAL
        ├── COMMUNITY
        │   ├── FEED
        │   ├── CREATE UPDATE
        │   └── CONTRIBUTIONS
        ├── CHECK-IN
        │   ├── SET CHECK-IN
        │   ├── ACTIVE TIMER
        │   └── HISTORY
        └── PROFILE
            ├── OVERVIEW
            ├── SAVED ROUTES
            ├── SETTINGS
            └── HELP & SUPPORT

SPECIAL STATES & MODALS
├── NO INTERNET
├── EMERGENCY
├── NO LOCATION
├── LOW BATTERY
├── DEVIATION
├── CELEBRATION
├── CONFLICTS
└── NO ROUTE

BACKGROUND SERVICES
├── MONITORING
├── TRACKING
├── NOTIFICATIONS
└── SYNC
```

------------------------------------------------------------------------

## 3. Navigation and responsive behavior

### Mobile (primary interaction model)

-   Use a persistent bottom navigation bar with Home, Navigate,
    Community, Check-in, and Profile.
-   Keep labels visible alongside icons where space permits.
-   Respect device safe areas and keyboard insets.
-   Important emergency actions must not be hidden behind a menu or
    require navigating away from an active route.

### Desktop and tablet

-   Use a responsive shell with a left navigation rail or sidebar at
    wide widths; retain the same five destinations and route URLs.
-   The content area should use a sensible max-width, with maps and
    route summaries receiving the space they need.
-   Convert mobile bottom sheets into side panels or centered dialogs
    where appropriate.
-   Do not simply stretch the mobile screen to desktop dimensions.

### URL and browser behavior

Use stable routes equivalent to: - `/onboarding/intro` -
`/onboarding/preferences` - `/onboarding/contacts` -
`/onboarding/location` - `/onboarding/notifications` -
`/onboarding/privacy` - `/onboarding/how-it-works` -
`/onboarding/get-started` - `/home` - `/navigate` - `/navigate/search` -
`/navigate/routes` - `/navigate/active` - `/navigate/arrival` -
`/community` - `/community/create` - `/community/contributions` -
`/check-in` - `/check-in/active` - `/check-in/history` - `/profile` -
`/profile/saved-routes` - `/profile/settings` - `/profile/help` -
`/emergency` (global emergency view/modal route if needed)

Use redirects based on onboarding completion, but allow users to revisit
setup from Settings. Browser back must not accidentally cancel or stop
an active safety timer without confirmation.

------------------------------------------------------------------------

## 4. Onboarding --- implement every step

### 4.1 Intro: Splash Screen

**Purpose:** Introduce SafePath and establish trust. - Show product
name, concise value proposition, and a clear primary CTA. - CTA advances
to Preferences. - Show loading only while actual initialization is in
progress. - Avoid fake security guarantees or unsupported safety claims.

### 4.2 Intro: Preferences

**Purpose:** Capture basic safety and usability preferences. - Provide
clear, editable preference choices, including relevant route/safety
preferences and accessibility options. - Explain why each setting
matters. - Save locally immediately; sync to the server when
available. - Continue to Contacts.

### 4.3 Intro: Contacts

**Purpose:** Set up trusted/emergency contacts. - Allow adding a contact
manually and selecting from device contacts only after an explicit user
action and supported permission. - Capture name and a valid phone number
or other supported contact channel. - Allow edit, remove, and
reorder/set primary contact. - Explain how contacts may be used in
check-in and emergency workflows. - Continue to Location setup.

### 4.4 Setup: Location

**Purpose:** Explain and request location access. - Explain use cases:
nearby route information, active navigation, deviation detection, and
check-in context. - Ask for browser/device permission only after the
user presses an explicit CTA. - Provide a "Not now" or manual-location
fallback. - If denied, continue onboarding with a visible
limited-functionality state; do not trap the user. - If unavailable or
inaccurate, show the No Location state and a retry/manual fallback.

### 4.5 Setup: Notifications

**Purpose:** Enable useful check-in and route alerts. - Explain
notification types before requesting permission. - Request browser
notification permission only after user action and only where
supported. - If denied, show how to enable it later in browser/device
settings; do not repeatedly prompt. - Explain that web push/background
delivery depends on browser support, installation state, and permission.

### 4.6 Setup: Privacy

**Purpose:** Make location, contacts, and contribution privacy
understandable. - Explain which data is stored locally and which is sent
to the server. - Explain location use, retention controls, community
post visibility, and emergency-contact use. - Provide links to Privacy
Policy and Terms if available. If not supplied, add clearly marked
placeholders rather than inventing legal terms. - Require acceptance
only for genuinely necessary terms; do not bundle optional consent into
required consent. - Continue to How It Works.

### 4.7 Onboard: How It Works

Explain the core sequence with short cards: 1. Choose a destination. 2.
Review route options and select the safest available route. 3. Start
navigation and receive relevant alerts. 4. Use silent check-in and
trusted contacts when needed. 5. Contribute useful safety updates after
the journey.

### 4.8 Onboard: Get Started

-   Summarize completed setup.
-   Provide a primary "Open SafePath" CTA to Home.
-   Any skipped setup should remain editable and show a non-blocking
    reminder where needed.
-   Mark onboarding complete only when the user intentionally proceeds.

------------------------------------------------------------------------

## 5. Main app destination specifications

## 5.1 Home

### Dashboard

-   Display a concise overview: current safety status, navigation entry
    point, check-in status, and recent community information.
-   If location is unavailable, show a clear explanation and a manual
    destination/search path.
-   Do not display fabricated live data.

### Quick Actions

Provide high-priority shortcuts: - Navigate Now - Silent Check-In -
Emergency / I Feel Unsafe - Create Safety Update (when appropriate)
Actions should be reachable with minimal interaction and have accessible
labels.

### Safety Status

-   Show current state: idle, route active, check-in active,
    offline/limited, or attention required.
-   State labels must reflect actual app state.
-   Explain any degraded capability, such as location unavailable or
    offline data only.

### Feed Preview

-   Show a small preview of relevant community updates.
-   Include loading, empty, stale/offline, and error states.
-   Link to the full Community feed.

------------------------------------------------------------------------

## 5.2 Navigate

### Search

-   Allow origin (current location or manually entered) and destination
    search.
-   Support place suggestions where a geocoding provider is configured.
-   Provide keyboard navigation and screen-reader labels for
    suggestions.
-   If location is unavailable, let the user enter an origin manually.
-   A "Navigate Now" action from Home should land here with the correct
    initial state.

### Route Options

-   Present multiple route choices when the routing provider returns
    them.
-   Include map/route preview and comparable details such as estimated
    duration, distance, route conditions, and known safety signals when
    real data is available.
-   Clearly label the **Safest Route** only when the ranking is backed
    by configured data and logic.
-   If fewer than the expected number of routes are available, show the
    actual available options.
-   If no route is available, show the **No Route** special state and
    allow retry/editing origin or destination.

### Active Navigation

-   Show the selected route, current progress, next step, and essential
    controls.
-   Use location updates only with permission and supported APIs.
-   Monitor deviation only while active navigation is running and the
    user has been informed.
-   On deviation, show the Deviation state with actions to continue,
    recalculate, or stop.
-   Handle route loss, GPS inaccuracy, network loss, and stale route
    information explicitly.
-   Do not imply reliable background GPS tracking on browsers that do
    not support it.

### Arrival

-   Present a clear arrival confirmation.
-   Ask the user to confirm arrival where required by the flow.
-   Offer "I've Arrived Safely" and a return-to-Home path.
-   If the user confirms arrival, stop navigation monitoring and any
    route-specific tracking.
-   Offer a post-arrival contribution flow, without forcing it.

------------------------------------------------------------------------

## 5.3 Community

### Feed

-   List safety updates with timestamp, location/area if shared,
    category/tags, confidence or verification status if implemented, and
    concise details.
-   Support filtering/sorting only where implemented.
-   Show stale/offline status clearly. Never present cached data as
    live.
-   Provide a clear route back to Home and a Create Update action.

### Create Update

Support the user-flow sequence: 1. Detect or select a location, with
manual fallback. 2. Create a safety update. 3. Rate the experience if
relevant to the post-arrival contribution flow. 4. Select tags,
including options aligned with "Well-lit" and "Crowded". 5. Add an
optional note (the diagram specifies a 50-character maximum). 6. Review
and share. 7. Show success only after local save or server confirmation,
explicitly distinguishing which occurred.

-   Validate required fields and prevent accidental duplicate
    submissions.
-   If offline, queue the update locally and show "Queued for sync", not
    "Published".
-   Allow the user to review queued/failed submissions.

### Contributions

-   Show the user's past contributions and their current status.
-   Include Community Tab / Community Feed entry points.
-   Provide Contribution History, including previous posts and any
    supported status/feedback.
-   "View My Contributions" from the flow should open this section.

------------------------------------------------------------------------

## 5.4 Check-in

### Set Check-In

-   Let users select a destination and ETA/duration.
-   Explain what happens if they do not confirm arrival by the deadline.
-   Let the user choose trusted contacts from their configured contact
    list.
-   Require explicit confirmation before starting a timer that may
    trigger outreach.
-   Provide an obvious cancel/edit option before activation.

### Active Timer

-   Display remaining time, destination/ETA, selected contacts, and
    status.
-   Persist the deadline so it survives refresh and app restarts.
-   Recalculate remaining time from the saved deadline; do not rely
    solely on an in-memory interval.
-   Offer "I'm Safe" / confirm arrival, extend timer, or cancel.
-   Send notifications only through supported and configured channels.
-   If background execution cannot be guaranteed, tell the user plainly
    that keeping the app/browser available may be necessary.

### History

-   List completed, cancelled, expired, and triggered check-ins with
    dates and outcomes.
-   Do not expose contact phone numbers unnecessarily.
-   Provide details for each past check-in when available.

------------------------------------------------------------------------

## 5.5 Profile

### Overview

-   Show account/profile basics, setup completion, safety preferences,
    and shortcuts to saved routes, settings, and help.
-   Support guest/local-only usage if authentication is not part of the
    supplied backend.
-   Do not invent account information.

### Saved Routes

-   List saved routes with origin, destination, and last-updated status.
-   Allow opening, renaming, and deleting a saved route.
-   Make clear if a saved route needs refreshing because conditions may
    have changed.
-   Never imply a stored route is currently safe without refreshed data.

### Settings

Include settings for: - Safety and route preferences - Location
permission guidance - Notification preferences and permission guidance -
Trusted contacts - Privacy controls - Offline/cache preferences where
applicable - Accessibility and display preferences - Account/session
actions if authentication exists

### Help & Support

-   Provide FAQs and clear guidance for location, notifications, offline
    mode, check-ins, and emergency actions.
-   Provide support/contact links only when real details are configured.
-   Clearly state that SafePath is not a substitute for local emergency
    services.
-   For immediate danger, make emergency options prominent and avoid
    suggesting the app can guarantee rescue.

------------------------------------------------------------------------

## 6. User flow --- reproduce all branches

The second diagram is the canonical journey map. Implement these paths
and their branching conditions.

### 6.1 Launch and onboarding branch

``` text
App Launch
  └── Internet Available?
      ├── Online → First Time User?
      │   ├── First Time → Welcome Splash → Safety Preferences
      │   │   → Emergency Contacts → Privacy Settings → Location Permission
      │   │   → Tutorial Complete → Home Screen
      │   └── Returning User → Home Screen
      └── Offline → Offline Mode Active (banner at top)
          └── Home Screen (limited functionality)
```

Rules: - Online/offline status must be based on actual browser
connectivity signals plus request failures where appropriate;
`navigator.onLine` alone is not definitive. - Offline mode must retain
usable cached data and queued actions. - First-time/returning status
must be persisted appropriately. - The "Returning User" path should not
repeat onboarding unless the user explicitly chooses to reset/revisit
it.

### 6.2 Home and offline behavior

``` text
Home Screen (Main dashboard)
  ├── Cached Data Only → Limited features
  ├── No Real-Time Updates → Safety data frozen
  └── Connection Restored → Sync queued data / upload pending
```

-   Show a persistent but non-blocking offline banner.
-   Label cached content with its last-updated time.
-   Disable or degrade features that require network data; explain why.
-   Queue eligible user-created content and sync when connectivity
    returns.
-   On sync conflict, use the Conflicts state and preserve the user's
    data.

### 6.3 Quick navigation journey

``` text
Navigate Now (button tapped)
  → Search Destination (enter location)
  → Route Options (map + 3 routes, if 3 are actually returned)
  → Select Safest Route
  → Active Navigation
  → Approaching Destination (alert card)
  → I’ve Arrived Safely (confirm arrival)
  → Home Screen
```

Additional branches: - From Home Screen, **Limited nav** can route to
Search Destination, but show the limitations. - If the selected route is
unavailable or cannot be computed, show **No Route**. - "Map + 3 routes"
describes the intended UI when available, not a requirement to fabricate
three routes. - The safest-route label must be evidence-based, and the
reason for the ranking should be inspectable where possible.

### 6.4 Route deviation / safety branch

``` text
Active Navigation
  ├── Follow route → Continue navigation
  ├── Deviation → Recalculate / choose new route
  └── I Feel Unsafe (panic button)
      → Emergency Route (find safest available route)
      → Choose Action (multiple options)
          ├── Take New Route (resume navigation)
          ├── Call Emergency Contact
          │   → Alert Community (notify nearby users, if supported and consented)
          │   → Community Tab → Community Feed → Contribution History
          └── Other configured emergency actions
```

-   **I Feel Unsafe** must be reachable during active navigation and
    from Quick Actions.
-   Emergency Route must prioritize safety criteria available from the
    configured provider/data. If no reliable safety data exists, say so
    and show available alternatives rather than asserting a route is
    safe.
-   **Choose Action** should clearly separate navigation choices,
    contact actions, and community actions.
-   Calling a contact should invoke a supported `tel:` link or
    integration only after user action.
-   Community alerts must only be sent if a real backend supports them
    and the user has consented. Otherwise present the available
    local/contact alternatives.
-   The panic action must not be hidden behind a multi-step settings
    flow.

### 6.5 Silent check-in journey

``` text
Silent Check-In (card tapped)
  → Set Check-In (destination + ETA)
  → Add Emergency Contacts (select from list)
  → Start Monitoring (background service)
  → User Travels (app can be closed, subject to actual platform capabilities)
  → Near ETA (push notification)
  → Arrival Prompt (confirm safe)
      ├── Confirm → I’m Safe → Notify Contacts (success message sent)
      └── No response → 15 Min Past ETA (no confirmation)
          → Call User (2 attempts, if supported)
          → No Answer
          → Send Emergency Alert (SMS to all contacts, if supported)
          → Share Last Location (maps link included, if available and consented)
```

Critical implementation notes: - Never claim that a web page can always
run a background timer, location tracker, phone call, or SMS after
closure. These depend on browser/OS capabilities and configured
server/push/SMS services. - Implement the full **product state machine**
even if a development environment uses a mock notification adapter.
Clearly label simulation/demo mode. - Use the persisted check-in
deadline and server timestamps where possible. - Do not automatically
call a user or send emergency SMS unless the user has explicitly enabled
and understood that policy, required consent is present, and a
legitimate delivery integration exists. - The "2 attempts" rule should
be configurable and visible in policy/config, not hardcoded as an
undocumented assumption. - If automatic escalation cannot be supported,
show a truthful fallback: prompt the user to call or message the
selected contacts. - Only share last known location when available,
sufficiently recent, and permitted. Include its timestamp in the
message/link context. - Provide a way to cancel false alarms and record
cancellation.

### 6.6 Post-arrival contribution journey

``` text
Arrived
  → Rate Route (optional feedback)
  → Contribute Update? (post-arrival prompt)
      ├── Yes → Create Safety Update (location detected)
      │   → Rate Experience → Select Tags (e.g., Well-lit, Crowded)
      │   → Add Note (optional, max 50 chars)
      │   → Share Update
      │   → View My Contributions
      └── Skip → Back to Home
```

-   Every contribution step is optional unless a specific field is
    genuinely required to submit.
-   Preserve a draft if the user exits partway through.
-   Never attach precise location to a public post without making that
    sharing clear and obtaining consent.

### 6.7 Offline and recovery paths

``` text
Offline Mode Active
  ├── Cached Data Only → limited features
  ├── No Real-Time Updates → show stale-data warning
  ├── Connection Restored → sync queued data
  └── Conflicts → resolve or preserve local/server versions
```

-   The offline banner must be visible without covering primary actions.
-   Provide retry controls for failed syncs.
-   Resolve conflicts with an understandable comparison and explicit
    user choice where merging is unsafe.
-   Do not silently overwrite local drafts or server records.

------------------------------------------------------------------------

## 7. Global special states and modals

The IA names eight global special states. Implement them as reusable
overlays/pages, with appropriate trigger logic and recovery actions.

### 7.1 No Internet

**Trigger:** Browser reports offline or key requests fail due to
connectivity. - Show persistent offline indicator. - Explain what
remains available offline. - Show cached-data freshness. - Queue
eligible writes and offer retry. - Return automatically to normal status
only after connectivity and required requests recover.

### 7.2 Emergency

**Trigger:** User presses I Feel Unsafe/Emergency or a supported
escalation condition occurs. - High-contrast, accessible emergency UI. -
Immediate actions: call selected emergency contact, open local emergency
call option when configured, view emergency route, share last location
if permitted. - Avoid false success states. - Provide cancellation and
"false alarm" handling. - Do not imply the app itself dispatches
emergency services unless a real integration exists.

### 7.3 No Location

**Trigger:** Permission denied, unavailable, timed out, or location
accuracy too poor. - Explain what failed and why it affects the current
action. - Offer Retry, browser permission instructions, or manual
location entry. - Do not block unrelated features.

### 7.4 Low Battery

**Trigger:** Battery API is supported and reports a configured low
threshold, or the user manually enables a low-power mode. - Battery API
is not universally available; feature-detect it. - If unavailable, do
not guess battery level. - Suggest reduced refresh rate and nonessential
background activity. - Never disable emergency access without user
consent.

### 7.5 Deviation

**Trigger:** Active navigation detects a meaningful departure from the
selected route using available location accuracy. - State what happened
without blaming the user. - Offer Recalculate, Continue on current
route, or Emergency Route. - Avoid repeated alerts caused by GPS jitter;
use configurable thresholds and cooldowns. - Stop monitoring when
navigation ends.

### 7.6 Celebration

**Trigger:** Arrival confirmed or meaningful journey milestone
completed. - Use a restrained success state. - Offer optional route
rating/contribution. - Respect reduced-motion preferences; avoid
blocking animation.

### 7.7 Conflicts

**Trigger:** Local queued data conflicts with a server version or sync
fails in a way that needs user choice. - Identify the affected item and
the conflicting versions. - Offer Keep Local, Use Server, or
Review/Merge where safe. - Preserve a recoverable copy until
resolution. - Do not expose private data from other users.

### 7.8 No Route

**Trigger:** Routing service returns no valid route or all candidates
fail validation. - Explain that no route could be calculated. - Offer
edit destination/origin, retry, manual search, or another routing
option. - Do not invent a route or mark an invalid route as safe.

------------------------------------------------------------------------

## 8. Background services

Implement each service as a clearly separated module, with browser
capability checks and adapters for server-backed behavior.

### Monitoring

-   Owns active check-in state and deadline evaluation.
-   Persists check-in state before activation.
-   Reconciles state on launch/visibility changes.
-   Server-side scheduling is preferred for reliable escalation while
    the browser is closed.
-   Client-only timers are a best-effort fallback, never a guarantee.

### Tracking

-   Runs only with explicit permission and while the relevant feature is
    active.
-   Uses the minimum location precision/frequency required.
-   Stops when navigation/check-in ends or the user revokes permission.
-   Indicates when location is being used.
-   Avoid claiming continuous background tracking on unsupported
    platforms.

### Notifications

-   In-app notifications should work regardless of push support.
-   Browser notifications require permission.
-   Web push requires service worker setup, push subscription, and a
    backend push sender.
-   Provide fallback in-app banners/toasts when push is unavailable.
-   Do not repeatedly request permission after denial.

### Sync

-   Queue eligible mutations in durable local storage (IndexedDB
    recommended).
-   Retry with exponential backoff and a maximum retry policy.
-   Use idempotency keys to prevent duplicate posts.
-   Track states such as `draft`, `queued`, `syncing`, `synced`, and
    `failed`.
-   Reconcile conflicts explicitly.
-   Display last successful sync time and queued-item count when
    relevant.

------------------------------------------------------------------------

## 9. PWA requirements

The product is a responsive website and an installable PWA. Implement
both deliberately.

### Required PWA deliverables

-   Web app manifest with name, short name, icons, theme/background
    colors, and `display` mode.
-   Service worker with an intentional caching strategy.
-   Installability checks and a contextual "Install SafePath" prompt
    where supported; do not nag users.
-   App icons in required sizes, including maskable icon support where
    practical.
-   Offline fallback page/shell.
-   HTTPS in production.
-   Update detection and a safe "New version available --- refresh"
    flow.
-   Standalone display support and correct status-bar/safe-area spacing.
-   Deep links and direct-route refresh support on the hosting platform.
-   Install prompt should gracefully disappear if not supported or
    already installed.

### Caching strategy

-   **App shell/static assets:** cache-first with versioned cache names.
-   **API safety/community data:** network-first or
    stale-while-revalidate according to data sensitivity and freshness;
    show timestamps.
-   **User drafts and queued updates:** IndexedDB, durable across
    reloads.
-   **Sensitive data:** avoid broad cache storage; define explicit
    retention and logout/clear-data behavior.
-   **Maps/tiles:** follow the map provider's licensing and caching
    rules; do not cache prohibited tiles.

### PWA limitations to handle honestly

-   Web push availability varies by browser/OS and may require
    installation.
-   Geolocation generally requires HTTPS and permission.
-   Background location and background timers are not reliably available
    across browsers.
-   SMS and phone calls require explicit user action or a configured,
    consented backend integration.
-   A service worker does not grant unrestricted access to device APIs
    or guarantee continuous execution.

------------------------------------------------------------------------

## 10. Visual and interaction design direction

Follow the diagrams' visual logic, not their literal diagram appearance
as the production UI.

### Design principles

-   Calm, trustworthy, highly legible, and safety-focused.
-   Use consistent status colors with text/icon labels so color is never
    the only signal.
-   Use clear cards, restrained shadows, rounded corners, and clean
    spacing.
-   Primary actions must be obvious; destructive/cancel actions must be
    distinct.
-   Keep emergency UI visually urgent but not visually chaotic.
-   Use readable typography and strong contrast.
-   Respect keyboard navigation, visible focus, screen readers, reduced
    motion, and browser zoom.

### Suggested semantic color mapping

Treat these as a starting token system and verify contrast: - Main
sections / primary success: green - Primary features: orange -
Community: blue - Navigation: amber/yellow - Check-in: violet - Profile:
pink/magenta - Emergency/special states: red - Background services:
slate/gray - Offline/limited: neutral amber or gray, with explicit text

The source diagrams use category colors to distinguish node types.
Production UI should use these colors semantically and consistently
without copying the diagram's small rounded boxes as the entire design
system.

### Component inventory

Build reusable components for: - Responsive application shell and
navigation - Status banner (offline, stale data, permission missing) -
Primary/secondary/destructive buttons - Route card and route
comparison - Map panel and location selector - Check-in timer card -
Trusted-contact row - Safety update card and tag picker - Confirmation
dialog - Bottom sheet/dialog - Toast/inline status message -
Empty/loading/error states - Permission explainer - Sync queue/conflict
resolver - Emergency action panel

------------------------------------------------------------------------

## 11. State model and data contracts

Use typed, explicit state rather than scattering booleans throughout
components. Adapt names to the existing codebase if one exists.

### Core domain entities

-   **UserPreferences:** route preferences, accessibility preferences,
    notification choices, privacy choices.
-   **TrustedContact:** stable ID, display name, contact method,
    phone/channel, priority, consent/verification metadata where
    applicable.
-   **RouteQuery:** origin, destination, travel mode if supported,
    requested preferences.
-   **RouteOption:** stable ID, geometry/polyline, distance, duration,
    route warnings, data timestamp, safety-score components, ranking
    explanation.
-   **ActiveNavigation:** route ID, start time, current progress,
    status, last location update, deviation status.
-   **CheckIn:** ID, destination, deadline, selected contacts, status,
    escalation policy, last known location metadata, created/updated
    timestamps.
-   **SafetyUpdate:** ID, category, tags, optional note,
    location-sharing level, timestamp, author display data,
    sync/publication status.
-   **Contribution:** reference to an update, status, created timestamp,
    optional moderation/verification status.
-   **SyncQueueItem:** ID, entity type, operation, payload reference,
    idempotency key, retry count, status, last error.
-   **AppStatus:** connectivity, permission states, cached-data
    freshness, pending sync count, installed/PWA mode where detectable.

### Suggested enums

``` ts
type CheckInStatus =
  | "draft"
  | "active"
  | "arrived_safe"
  | "cancelled"
  | "overdue"
  | "escalating"
  | "escalated"
  | "failed";

type SyncStatus =
  | "draft"
  | "queued"
  | "syncing"
  | "synced"
  | "failed"
  | "conflict";

type NavigationStatus =
  | "idle"
  | "searching"
  | "route_selected"
  | "active"
  | "deviated"
  | "arrived"
  | "cancelled"
  | "no_route";
```

### State transitions

-   A check-in must be saved before its timer is considered active.
-   `active → arrived_safe` when the user confirms they are safe.
-   `active → overdue` when deadline passes without confirmation.
-   `overdue → escalating` only if the configured escalation policy is
    enabled and supported.
-   `escalating → escalated` only when an escalation action is confirmed
    delivered; otherwise use a failure state.
-   Navigation transitions to `arrived` only after an explicit
    confirmation or a verified provider event according to product
    policy.
-   Offline-created updates transition
    `draft → queued → syncing → synced`; failures and conflicts remain
    visible.
-   Permission denial is a first-class state, not an uncaught exception.

------------------------------------------------------------------------

## 12. Technical implementation guidance

First inspect the existing repository and retain its framework,
conventions, routing, design system, and installed dependencies where
practical. Do not replace the project architecture without reason.

### Suggested architecture boundaries

-   `app/` or existing route directory: page-level route components.
-   `components/`: reusable UI and responsive shell.
-   `features/onboarding/`
-   `features/home/`
-   `features/navigation/`
-   `features/community/`
-   `features/check-in/`
-   `features/profile/`
-   `features/emergency/`
-   `services/location/`
-   `services/routing/`
-   `services/notifications/`
-   `services/contacts/`
-   `services/sync/`
-   `services/storage/`
-   `services/check-in-monitoring/`
-   `pwa/` or framework-equivalent manifest/service-worker setup.
-   `types/`: domain types and API contracts.

### Provider adapters

Create interfaces for: - Geolocation - Geocoding/routing/maps - Push
notifications - SMS/contact escalation - Authentication/user profile (if
required) - Community feed and update publishing - Server-side check-in
scheduling/escalation

Keep provider-specific implementation out of page components. Provide
development mocks only when necessary, with a visible demo-mode
indicator.

### Engineering quality

-   Type-safe components and service boundaries.
-   Form validation and meaningful error messages.
-   No dead buttons or placeholder links presented as functional.
-   Avoid duplicated state; derive views from canonical state.
-   Use stable IDs for list keys and sync operations.
-   Protect against duplicate submissions and stale asynchronous
    responses.
-   Clean up subscriptions/listeners when components unmount.
-   Add unit tests for state machines and utilities; integration tests
    for major journeys; end-to-end tests for critical safety flows.
-   Include `.env.example` for required provider keys, never commit
    secrets.
-   Add clear README instructions for development, production build, PWA
    testing, and integrations.

------------------------------------------------------------------------

## 13. Accessibility, privacy, and safety

### Accessibility

-   WCAG 2.2 AA target.
-   Full keyboard support, visible focus, semantic headings/landmarks,
    accessible form errors.
-   Minimum practical touch target sizes on mobile.
-   Do not rely on color alone for route ranking or emergency states.
-   Support reduced motion and high zoom.
-   Announce meaningful timer/status changes without flooding screen
    readers.

### Privacy

-   Request only necessary permissions.
-   Explain why location/contact access is requested.
-   Give users control over location sharing and public contribution
    details.
-   Minimize collection and retention of precise location.
-   Do not log sensitive location/contact payloads to analytics or
    console logs.
-   Secure authenticated endpoints and validate data server-side.
-   Make local-data clearing and account logout behavior explicit.

### Safety

-   Avoid absolute claims such as "guaranteed safe route".
-   Explain uncertainty and data freshness for safety ratings.
-   Provide an immediate path to local emergency calling/contact actions
    where configured.
-   Never silently dispatch alerts or share location.
-   Confirm high-impact actions and provide cancellation where possible.
-   Make all automated escalation policies opt-in, configurable, and
    transparent.

------------------------------------------------------------------------

## 14. Acceptance criteria

The implementation is not complete until all applicable items below are
verified.

### Information architecture

-   [ ] All onboarding pages exist and are linked in the specified
    sequence.
-   [ ] All five main navigation destinations exist.
-   [ ] All subpages under Home, Navigate, Community, Check-in, and
    Profile exist.
-   [ ] All eight special states are implemented.
-   [ ] All four background services have explicit modules and state
    handling.

### User flows

-   [ ] First-time online onboarding works end-to-end.
-   [ ] Returning user lands on Home without repeated onboarding.
-   [ ] Offline launch shows the Offline Mode banner and usable cached
    shell.
-   [ ] Navigate Now supports search, route options, safest-route
    selection, active navigation, deviation, arrival, and no-route
    recovery.
-   [ ] I Feel Unsafe opens emergency choices from both Home and Active
    Navigation.
-   [ ] Silent Check-In supports set-up, timer, safe confirmation,
    overdue state, and honest escalation fallback.
-   [ ] Post-arrival rating and contribution are optional and work
    end-to-end.
-   [ ] Offline updates are queued and synced without duplicates.
-   [ ] Sync conflicts preserve data and offer resolution.
-   [ ] Profile settings allow users to revisit permissions/preferences.

### Responsive/PWA

-   [ ] Mobile, tablet, and desktop layouts are usable.
-   [ ] PWA manifest and service worker are configured.
-   [ ] Installation works in supported browsers.
-   [ ] App shell loads offline after a successful online visit.
-   [ ] Update prompt and refresh behavior work.
-   [ ] Direct navigation to nested URLs works after refresh.
-   [ ] Unsupported capabilities are disclosed with graceful fallbacks.

### Quality

-   [ ] No primary action is a dead button.
-   [ ] No fake success message is shown for unsent notifications, SMS,
    or community posts.
-   [ ] Forms validate input and show accessible errors.
-   [ ] Critical states are keyboard accessible and announced.
-   [ ] Tests cover state transitions and key journeys.
-   [ ] README documents setup, environment variables, PWA testing,
    known limitations, and integration points.

------------------------------------------------------------------------

## 15. Agent execution plan

Implement in this order, committing coherent milestones if version
control is available:

1.  **Repository audit:** identify framework, existing pages, routing,
    design tokens, backend contracts, and current functionality.
2.  **Foundation:** establish responsive shell, route map, shared
    components, state conventions, and visual tokens.
3.  **Onboarding:** implement all eight onboarding nodes and
    persistence.
4.  **Home + navigation:** dashboard, quick actions, search, route
    options, active navigation, arrival, deviation, no-route.
5.  **Check-in + emergency:** check-in setup, timer state machine,
    emergency action panel, safe/overdue/escalation states.
6.  **Community:** feed, create update, contribution history, drafts and
    queued publishing.
7.  **Profile:** overview, saved routes, settings, help.
8.  **Offline + sync:** durable queue, freshness labels, retry, conflict
    handling.
9.  **PWA:** manifest, icons, service worker, caching,
    installation/update UX.
10. **Integration adapters:** wire real provider APIs where credentials
    and backend exist; otherwise label mocks.
11. **Testing and audit:** execute acceptance checklist across
    desktop/mobile, online/offline, permission denied/granted, and key
    safety branches.
12. **Handoff:** document implemented features, missing
    credentials/integrations, test commands, and any behavior that
    remains simulated.

### Final instruction to the coding agent

Use the two supplied diagrams as the functional blueprint. Preserve
every named section and user-flow branch. Build a production-quality
responsive web application with PWA support, not a static diagram or a
mobile-only native app. Where a diagram assumes a device capability that
a browser cannot guarantee, preserve the intended user journey but
implement a truthful, permission-aware fallback. Do not fabricate
routes, safety data, location, contact delivery, SMS delivery, or
successful background execution.
