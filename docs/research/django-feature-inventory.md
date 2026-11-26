# Feature inventory of the Django app (as of master at e8f0176, 2026-11-26)

Method: read straight from the code in `logbook/` (models, views, forms, urls, templates, grades, weekly, pwa), `config/` (settings, urls) and the test list in `tests/`. Nothing here comes from running the app or from secondary write-ups; file names are given so every claim can be checked. This is the "done" checklist for the parity ticket. It describes the app **today**, before Slice 4 (#60 to #64: outdoor routes, outdoor ascents and so on) lands, so outdoor is listed as "not built".

Plain-English terms used below:
- **Server-rendered app**: the server builds finished HTML pages and sends them to the browser. There is no separate API.
- **View**: a function that handles one URL: reads the request, talks to the database, picks a page template.
- **Template**: an HTML file with blanks filled by the view.
- **Model**: a class that describes one database table.
- **Form**: a class that describes the fields of a web form and checks input (validation).
- **Migration**: a versioned script that changes the database table layout.
- **htmx**: a tiny JavaScript library. An element carries `hx-get`/`hx-post` attributes; the browser fetches an HTML *fragment* from the server and swaps it into the page without a full reload.

## 1. Big picture

- One Django app, `logbook`, plus the `config` project. Postgres database. Static files served by WhiteNoise. Everything is HTML pages; the only JSON is the PWA manifest.
- Whole app is **login-protected** (Django's `LoginRequiredMiddleware` in `config/settings.py`); only the manifest opts out (`@login_not_required` in `logbook/pwa.py`).
- Single user, created on the command line with `createsuperuser` (README). No sign-up, no password reset, no user ownership of data: no row has an owner column.
- Time zone `Pacific/Auckland`, `USE_TZ = True` (timestamps stored with time zones).
- About 1,300 lines of app code (excluding migrations) and 148 tests in 16 files.

## 2. URLs and views (the complete list)

All in `logbook/urls.py` and `logbook/views.py`, plus `admin/` from `config/urls.py`. "HTMX fragment" means the response is a piece of HTML, not a whole page.

| URL | Name | Methods | What it does |
|---|---|---|---|
| `/` | session_list | GET | All Sessions, newest first (`-date`, `-id`), each with an Ascent count; shows this-week and last-week total minutes. No paging, filtering or search. Links: Log a Session, Gyms, Sign out (POST form). |
| `/sessions/new/` | session_create | GET, POST | Session form. Valid POST saves and redirects to the list. |
| `/sessions/<id>/` | session_detail | GET | Read-only Session fields plus the Ascents section (below). |
| `/sessions/<id>/edit/` | session_edit | GET, POST | Same form, prefilled. Has a Delete link. |
| `/sessions/<id>/delete/` | session_delete | GET, POST | GET shows confirm page (warns "also deletes N Ascents, Routes are kept"); POST deletes (Ascents cascade) and redirects to list. |
| `/sessions/<id>/ascents/new/` | ascent_create | POST only | Quick-add an Ascent. 400 if the Session is not indoor. If the request came from htmx, returns the Ascents section fragment (with errors if invalid); otherwise redirects to the detail page on success or re-renders it with HTTP 422 on failure. |
| `/sessions/<id>/ascents/form/` | ascent_form | GET | HTMX fragment: the quick-add section with an existing Route chosen (`?route=<id>`) or cleared. 404 if Session is not indoor. |
| `/sessions/<id>/routes/search/` | route_search | GET | HTMX fragment: up to 10 existing Routes at the Gym named in `?gym=` whose name contains `?name=` (both case-insensitive). Each candidate shows grade, hold colour, date set and the result of the last Ascent (or "no Ascents yet"). Returns nothing until both gym and name are non-empty. 404 if Session not indoor. |
| `/ascents/<id>/edit/` | ascent_edit | GET, POST | Edit discipline, result, rests, notes only (the Route and Session cannot be changed). Redirects to the Session detail. 404 if its Session is not indoor. |
| `/ascents/<id>/delete/` | ascent_delete | GET, POST | Confirm page, then delete; redirects to the Session detail. |
| `/routes/<id>/edit/` | route_edit | GET, POST | Edit every Indoor Route attribute, including moving it to another Gym. Redirects to the Gym list. Reached only from a link on each Ascent in the Session detail. |
| `/gyms/` | gym_list | GET | All Gyms, A-Z ignoring case. |
| `/gyms/new/` | gym_create | GET, POST | Gym form. |
| `/gyms/<id>/edit/` | gym_edit | GET, POST | Gym form, prefilled, with Delete link. |
| `/gyms/<id>/delete/` | gym_delete | GET, POST | Confirm page. POST deletes unless the Gym has Routes, in which case HTTP 409 and an error message. |
| `/grades/options/` | grade_options | GET | HTMX fragment: the grade `<option>` list for `?route_type=` and `?grade_system=`. |
| `/results/options/` | result_options | GET | HTMX fragment: the result `<option>` list for `?discipline=` (keeps `?result=` selected). |
| `/manifest.webmanifest` | manifest | GET | PWA manifest as JSON (see section 7). Public. |
| `/login/`, `/logout/` | login, logout | GET/POST | Django's built-in login and logout views. After login go to the list; after logout go to login. Logout is POST only. |
| `/admin/` | (admin) | | Django admin site, see section 8. |

Not present: no Route list or Route detail page, no Route create page (Routes are only created inside the quick-add Ascent form), no Gym detail page, no statistics or charts, no export, no REST/JSON API, no search outside the route matcher.

## 3. Data model (tables and fields)

From `logbook/models.py`. "Optional" means the field may be left empty. `created_at`/`updated_at` are set automatically (on creation / every save).

### Session
| Field | Type | Rules |
|---|---|---|
| date | date | required; form defaults to today (local) |
| activity_type | text, max 20 | required; fixed list, only "climbing" exists; form defaults to climbing |
| duration_minutes | whole number >= 0 | optional |
| effort | whole number | optional; 1 to 10 |
| location | text, max 200 | optional, free text (not linked to a Gym) |
| indoor_outdoor | text | optional; "indoor" or "outdoor" |
| notes | long text | optional |

Default ordering: newest date first, then newest id. No created_at/updated_at on Session.

### Gym
name (max 200, required), city (100), country (100), website (URL); the last three optional. Unique on name **ignoring case** (database constraint on `lower(name)`). Ordered by name ignoring case. A helper `Gym.objects.named(name)` finds a Gym by case-insensitive name or creates it, and copes with two requests creating it at once. No created_at/updated_at.

### IndoorRoute (a Route at a Gym)
Shared fields from the abstract base `Route`: name (max 200), grade (max 20), grade_system (ewbank, v, font, french; blank means "use default for type"), route_type, stars (0 to 3, optional), length_m (>= 1, optional), description, style (free-text tag, max 50), created_at, updated_at. Indoor-specific: gym (required, **protected**: a Gym with Routes cannot be deleted), setter (100), hold_colour (50), date_set (date), rope_number (free text, 20), bolts (whole number >= 1), area (100). Route type choices indoors: top_rope, sport, boulder. Names are **not** unique within a Gym (routes get reset and names reused).

### IndoorAscent (an attempt-or-completion of one Route in one Session)
session (required; deleting the Session deletes its Ascents), route (required; **protected**: a Route with Ascents cannot be deleted, though no view deletes Routes anyway), discipline (boulder, top_rope, sport), result, rests (whole number, optional), notes, created_at, updated_at. Ordered by created_at, then id. There is **no per-Ascent date** in the code today (CONTEXT.md says an Ascent has its own date; only the Session has a date).

Results in total: onsight, flash, redpoint, dogged, working, attempt, dab, repeat, tick.

### Abstract bases and what is not built
`Route` and `Ascent` are *abstract* (no table of their own); each concrete table repeats their fields, which is how ADR 0003 (separate indoor and outdoor routes and ascents) is implemented. Outdoor models (Crag, Outdoor Route, Outdoor Ascent) **do not exist yet**; a Session set to "outdoor" shows "Outdoor Ascents are not available yet". Other Activity types (running, hiking, mountaineering, walking) do not exist.

### Tables created by Django itself
Users and permissions (`auth_*`), login sessions (`django_session`: browser logins, nothing to do with the climbing "Session"), admin log, content types, migration history.

### Migrations
Five: 0001 initial (Session), 0002 route and ascent, 0003 gym, 0004 indoor route and ascent, 0005 indoor route attributes. Migrations run automatically at container start (`docker-entrypoint.sh`).

## 4. Business rules (validation)

Enforced in model `clean()` methods and form classes (`logbook/models.py`, `logbook/forms.py`).

**Session**
1. Setting (indoor/outdoor) cannot be changed while the Session has Ascents; the error says how many and to delete them first.
2. Effort must be 1 to 10 if given.

**Gym**
3. Name unique ignoring case, checked in the form ("A Gym called X already exists") and again by a database constraint; a race between two saves becomes a friendly error on the name field.
4. A Gym with any Routes cannot be deleted (409 plus message).

**Route**
5. Grade is mandatory and must belong to the Route's grade system.
6. If no grade system is chosen, it defaults from the Route type: boulder gets V; top-rope and sport get Ewbank (applied on validation and on save).
7. A boulder cannot have a rope number.
8. Bolts only apply to sport Routes.
9. Area only applies to boulders.
10. Route type cannot be changed once the Route has Ascents (edit form).
11. Stars 0 to 3; length and bolts at least 1.

**Ascent**
12. Only allowed on indoor Sessions (also checked in the views: 400/404).
13. Discipline must suit the Route type (table below).
14. Result must be one of those allowed for the Discipline (table below).
15. Rests only kept when the Result is "dogged"; for any other result rests is silently cleared. A dogged Ascent with rests below 1 is an error. Rests may be blank.
16. When editing, the Discipline list is narrowed to those the Route allows, and a stored Result that no longer fits the chosen Discipline stays visible rather than being silently replaced.

Discipline allowed by Route type:

| Route type | Disciplines |
|---|---|
| boulder | boulder |
| top_rope | top_rope |
| sport | sport, top_rope |

Results allowed by Discipline:

| Discipline | Results |
|---|---|
| boulder | onsight, flash, working, attempt, dab, tick, repeat |
| top_rope | onsight, flash, dogged, working, attempt, tick |
| sport | onsight, flash, redpoint, dogged, working, attempt, tick |

The lists include `dab` and `repeat` (boulder only), which CONTEXT.md does not describe.

## 5. Grade systems

`logbook/grades.py`: code-defined ordered lists, easiest first (the order is meant to power later statistics). Not stored in the database.

- **V** (boulder): VB, V0 to V17.
- **Font** (boulder): 3, 4, 4+, 5, 5+, then 6A, 6A+, 6B, 6B+, 6C, 6C+ and the same pattern for 7 and 8, then 9A.
- **French** (sport): 1, 2, 3, 3+, 4a, 4b, 4c, 5a, 5b, 5c, then 6a, 6a+, 6b, 6b+, 6c, 6c+ and the same pattern for 7 and 8, then 9a, 9a+, 9b, 9b+, 9c.
- **Ewbank** (Australia/NZ, roped): the integers 1 to 39.

Behaviour: the grade drop-down is repopulated by htmx whenever the Route type or grade system changes (`/grades/options/`); with no system chosen it uses the type's default, else V. Any route type can use any grade system. Grade is stored as text; ranking is by position in the list, so a rewrite must keep the lists and their order.

## 6. Weekly summary

`logbook/weekly.py`, shown at the top of the Session list: "This week: N min" and "Last week: N min".
- A week runs **Monday to Sunday**, in local (Auckland) time.
- Total = sum of `duration_minutes` of Sessions dated in that week; a Session with no duration counts as 0; no Sessions gives 0.
- Only these two numbers exist; there are no other statistics (no grade pyramid, volume by discipline and so on).

## 7. Screens, forms and interactive behaviour

Pages: login, Session list, Session detail (with Ascent list and quick-add form), Session form (new/edit), Session delete confirm, Ascent edit, Ascent delete confirm, Route edit, Gym list, Gym form (new/edit), Gym delete confirm. All extend `base.html` (mobile viewport, theme colour, manifest link, apple touch icon, one stylesheet `app.css`, htmx). Styling: a small hand-written stylesheet with light/dark support, and tables that collapse to labelled rows on phones.

Quick-add Ascent form (the most complex screen), on the detail page of an indoor Session:
- Two modes. **New Route**: Gym (free text), Route name, Type, Grade, Grade system, then Discipline, Result, Rests, Notes. **Existing Route chosen**: shows the Route's name/grade/gym/type with a "Change route" link, and only Discipline, Result, Rests, Notes.
- Typing in Gym or Route name (250 ms pause) calls route search; clicking a match switches to "existing Route" mode.
- A new Route with a Gym name that does not exist yet creates the Gym on the spot; an existing Gym is matched ignoring case. A new Route is **never** auto-matched to an existing one by name (the athlete picks from the matches), because names repeat.
- Discipline narrows the Result list live (`/results/options/`); for an existing Route, Discipline choices are limited to those the Route allows.
- Defaults: Discipline (and for a new Route also Gym and Type) are prefilled from the last Ascent logged in this Session, else the most recent Ascent anywhere.
- Saving a new Route and its Ascent is one database transaction.
- Errors show field by field. The Ascent list refreshes in place when JavaScript is on, and the form also works as a plain POST without it.
- A Session with no setting shows "Set this Session as indoor or outdoor to log Ascents"; outdoor shows "not available yet".

Ascent list lines show: Edit link, Route name (link to Route edit), grade, Gym, Discipline, Result, rests count, notes.

CSRF protection: every POST needs a token; htmx sends it via a header set on the page body.

**PWA (installable web app)**: a manifest (`/manifest.webmanifest`) with name "The Logbook", short name "Logbook", start URL `/`, scope `/`, display `standalone`, background and theme colour `#1f2937`, icons 192 and 512 px, plus an Apple touch icon. **No service worker**, so no offline mode and no caching; it only lets "Add to Home Screen" open full-screen. Tests: `tests/test_pwa.py`.

## 8. Admin use

`logbook/admin.py` contains only the default comment: **no model is registered** in the Django admin. The admin site is reachable at `/admin/` for the superuser but manages only users and groups. All climbing data is edited through the app's own pages. The one admin-style task the rewrite must replace is creating the first user (`createsuperuser`, per README), for example with a seed or command-line script.

## 9. Deployment and settings that affect behaviour

- Production mode when `DJANGO_DEBUG` is false: `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` must be real values (placeholders `change-me`, empty, and `logbook` are rejected at start); secure cookies; trusts `X-Forwarded-Proto` from the proxy (Tailscale serve). Allowed hosts and CSRF trusted origins come from environment variables. Tested in `tests/test_production_settings.py`.
- Email backend is the console; nothing sends email.
- Migrations run on container start.

## 10. Test coverage (what the existing tests prove)

148 tests in `tests/`, one file per feature: auth, log session, edit/delete session, session list and detail, log ascent, existing route, edit/delete ascent, results, grades, gyms, route edit, weekly total, PWA, production settings. They can be read as an executable spec for parity; the rewrite can port them as acceptance tests.

## 11. MVC mapping to an API plus client (for the "Teach" part)

How the current pieces map onto a TypeScript API plus React client:

| Today (Django) | In an API plus React design |
|---|---|
| Model (database table plus rules in `clean()`) | Database schema plus a **validation layer** on the server (the rules in section 4 must live on the server; the client may copy them for instant feedback) |
| View (function per URL, returns HTML) | **API endpoint** (returns JSON: data only, plus error codes) |
| Template (HTML with blanks) | **React component** (draws the page from the JSON in the browser) |
| Form class (fields, validation, rendering) | Client form component plus server validation schema (ideally one shared schema in TypeScript) |
| URL routing | Two sets: API routes on the server, page routes in the browser (client-side router) |
| Session cookie plus CSRF token | Token-based API login (as the map notes) |
| htmx fragments (`route_search`, `grade_options`, `result_options`, `ascent_form`) | Plain JSON queries from the client; grade and result lists are constants, so the client can hold them and need no call |
| Redirect after POST | Client navigates after the API call succeeds |
| 409/422 HTML error pages | Structured JSON errors the client shows next to fields |

Things worth noticing for the rewrite:
1. **Rules that only exist in Python** and must be re-implemented once, centrally: section 4 items 1 to 16, the two lookup tables (Route type to Disciplines, Discipline to Results), the grade lists, the default grade system, the week boundaries.
2. **Behaviours that come free from Django and would otherwise be rebuilt**: login and logout, password hashing, CSRF, form error rendering, 404 handling, case-insensitive uniqueness, ordering, the `ProtectedError` mechanism (foreign keys that refuse deletion), automatic `updated_at`, cascade delete of Ascents with a Session.
3. **Endpoints that disappear or change shape**: the three option endpoints and `ascent_form` exist only to serve htmx; `route_search` becomes a real query endpoint; confirm-delete pages become client-side dialogs.
4. **Gaps between code and CONTEXT.md to settle before parity**: Ascent has no own date (CONTEXT.md says it has); Session location is free text, not a Gym or Crag; `dab` and `repeat` results are not described in CONTEXT.md; outdoor, Crag and activities other than climbing are Slice 4 or later.
5. **Hooks the map wants that do not exist today**: `owner` column, client-generated IDs (all ids are database-assigned integers), versioned API routes. `updated_at` exists on Route and Ascent but **not** on Session or Gym.

## Unverified

- The app was not started, so rendered behaviour is inferred from code and templates, not observed.
- Slice 4 designs (#60 to #64) were not read; this inventory is the Django app on master only.
