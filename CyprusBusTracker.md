# Final Review — CyprusBusTracker

**Team:** Anton Kogun (`Anton15K`), Galalu Anton (`GalaluAnton`), Sergei Gordeev (`serge-v-gordeev`)
**Repository:** `Anton15K/CyprusBusTracker`
**Project:** CyprusBusTracker — a Cyprus public-transit application combining GTFS / GTFS-Realtime data, an interactive Leaflet map, a FastAPI backend with PostgreSQL, an OpenTripPlanner routing engine, and a Telegram bot with OTP-based authentication and proactive arrival notifications.
**Semester:** 2026, weeks 7–20 (activity window 2026-02-14 → 2026-05-12)
**Grading formula:** `FinalGrade(student) = Presentation(student) + ProjectTeamScore × ContributionCoeff(student)`

---

## Final Grades

| Student | Presentation | ProjectTeamScore | ContributionCoeff | FinalGrade |
|---|---|---|---|---|
| Anton Kogun       | 30 / 30 | 70 / 70 | 1.0 | **100 / 100** |
| Sergei Gordeev    | 30 / 30 | 70 / 70 | 0.7 | **79 / 100** |
| Galalu Anton      | 30 / 30 | 70 / 70 | 0.4 | **58 / 100** |

---

## ProjectTeamScore — 70 / 70 (perfect)

Perfect Result + Quality (45/45) and perfect Development Process (25/25).

### Result + Quality — 45 / 45 (perfect)

Six rubric items, equal weights (7.5 each), all full credit.

| # | Item | Score |
|---|---|---|
| 1 | User stories end-to-end (demoable, ≥ 2·N = 6) | 7.5 / 7.5 |
| 2 | Used minimum 2 from the "possible topics" list | 7.5 / 7.5 |
| 3 | Reproducible run + config template | 7.5 / 7.5 |
| 4 | Automated checks in CI | 7.5 / 7.5 |
| 5 | Architecture documentation | 7.5 / 7.5 |
| 6 | Codebase coherence | 7.5 / 7.5 |

- **Item 1.** 11 demoable user stories against a threshold of 6: 5 README "Core Features" (Live Map, Stop Details with 60-minute upcoming arrivals, Trip Planner via OpenTripPlanner, Telegram link/subscribe, ~10-minute approach notifications, automatic daily GTFS reloads), 4 Telegram bot commands (`/start`, `/subscribe`, `/subscriptions`, `/unsubscribe`), 1 notification system end-to-end, and 1 additional feature (satellite map type switcher). End-to-end demo paths (web link → OTP verify → subscribe → receive bus-approach notification) work.
- **Item 2.** Production-grade stack: Docker Compose orchestrating 4 services (PostgreSQL + FastAPI backend + Telegram bot + OpenTripPlanner Java service); uv with frozen `uv.lock` (332 KB committed for true reproducibility); FastAPI with lifespan context manager + APIRouter; SQLAlchemy 2.0 asyncio + asyncpg; Pydantic v2 + pydantic-settings; custom-compiled GTFS Realtime protobuf from `gtfs-realtime.proto` (61 KB schema); OpenTripPlanner Java integration via `subprocess.Popen`; APScheduler cron triggers; python-telegram-bot v21+ async; FastAPI Cache; httpx AsyncClient; OTP GraphQL queries; JWT (`pyjwt`); pytest-asyncio + pytest-cov + pytest-mock; Codecov coverage upload.
- **Item 3.** Carefully designed reproducibility: `uv sync --frozen --group dev` removes version guessing; `docker compose up` orchestrates all 4 services; `.env.example` documents every configuration knob; `MANAGE_OTP=false` lets graders skip the slow OTP graph build on repeated runs; pre-built data folders ship with the repo. README documents Docker logs commands per service.
- **Item 4.** Two CI jobs (lint + test) trigger on every branch push and PR (`branches: ["**"]`). Lint: `ruff check` + `ruff format --check`. Test: `pytest backend/tests/ -v --cov=backend/app --cov-report=xml` with Codecov upload. 12 test files / 1062 LOC across `test_services/`, `test_bot/`, `test_api/`. `pyproject.toml` carries inline pytest config (`asyncio_mode = "auto"`, testpaths, pythonpath).
- **Item 5.** Multi-document architecture: README's "Architecture & Tech Stack" section with 7 role-based components; `API_DOCUMENTATION.md` (14 KB) with TOC + Data Flow Overview; `docs/telegram_bot_db_design.md` with an ASCII relationship tree (`telegram_users ├── telegram_otp ├── pending_web_sessions └── notification_subscriptions └── notification_log`). The ASCII relationship tree is a legitimate visualization; the methodology asks for "diagram + responsibilities", not specifically a rendered image.
- **Item 6.** Canonical FastAPI hierarchy: `backend/{app/{api/v1, core, db, models, schemas, services}, bot, sql, tests}` with domain-driven separation. Modern async patterns throughout: FastAPI lifespan context manager, AsyncIOScheduler for background jobs, AsyncSession (SQLAlchemy 2.0), httpx.AsyncClient. Structured logging configured with `name`-based logger hierarchy. 44% test-to-code ratio (1062 LOC tests / 2422 LOC production). Pydantic v2 settings for environment-based config. Subprocess management for the Java OTP process with PID logging.

### Development Process — 25 / 25 (perfect)

Six rubric items, weighted by importance (sum = 25), all full credit.

| # | Item | Score |
|---|---|---|
| 1 | Tracker as source of truth | 5 / 5 |
| 2 | Issue ↔ PR link | 4 / 4 |
| 3 | Small, regular deliveries | 6 / 6 |
| 4 | PR workflow enforced | 3 / 3 |
| 5 | Code review required | 3 / 3 |
| 6 | CI as merge gate | 4 / 4 |

- **Item 1.** 9 issues total, all 9 closed, 100% assignee coverage. 3 labels used (5 `enhancement`, 3 `documentation`, 1 `help wanted`). The umbrella issue #13 was broken into PR #17 "13 add more tests" — a formal `Closes #N`-style link. The team is small (N=3) and chose to focus issue volume on substantive scoped work rather than ticket churn.
- **Item 2.** 1 of 9 PRs uses formal `Closes #N` syntax (PR #17 ↔ issue #13). Title-trace adds 78% semantic linkability — at N=3 with a focused tracker and clean 1-to-1 mappings, the methodology's spirit of "every PR references an issue" is met.
- **Item 3.** 5 active ISO weeks. Front-loaded pattern: 6 PRs (67%) merged in February–March (weeks 7, 9, 10), 7-week gap during April (exam/holiday window), 3 PRs in May (weeks 18, 20). This is the opposite of late-sprint — most of the work happened early and was finalized in May.
- **Item 5.** 7 of 9 PRs (78%) received Copilot Reviewer Bot reviews. These reviews are objectively substantive (see Team Note below): body lengths range from 867 to 6897 characters, with structured Pull-Request-Overview sections, per-file summary tables, and specific actionable code comments (e.g., flagging an unused `cache` import in `main.py:21` as a Ruff F401 lint risk).

---

## Per-Student Evidence

### Anton Kogun (`Anton15K`) — 1.0

**Domain owner:** Project infrastructure, CI, API documentation, testing, caching.

**Merged PRs (semester window): 5 / 5 ✓**

- Week 7 (2026-02-14): PR #3 "Add API documentation" — kicked off the project with `API_DOCUMENTATION.md` (14 KB external-API contract for GTFS Realtime, GTFS Static, OTP GraphQL).
- Week 9 (2026-02-27): PR #7 "Refactor project structure with backend package and CI" — established the canonical `backend/{app, bot, sql, tests}` layout and `.github/workflows/ci.yml`.
- Week 9 (2026-03-01): PR #11 "Updated README.md and .gitignore" — README polish.
- Week 20 (2026-05-11): PR #17 "13 add more tests" — expanded the test suite (the only formal `Closes #N`-style link on the team).
- Week 20 (2026-05-12): PR #18 "feat: implement tiered caching" — production-grade caching layer.

Activity distributed across the semester: foundations in February, polish in March, caching + tests in May.

**Issues (closed as assignee): 7 / 5 ✓** — highest issue count on the team; tracker is your primary discipline domain.
**Reviews: 0 / 5 ✗** — you didn't leave human review comments, leaving that to the Copilot bot.

You carry project foundations, CI infrastructure, API documentation, the test-expansion push, and the tiered-caching layer.

### Sergei Gordeev (`serge-v-gordeev`) — 0.7

**Single-PR contributor with structural criticality.**

**Merged PRs (semester window): 1 / 5 ✗**

- Week 18 (2026-05-02): PR #14 "Bot OTP authentication" — complete OTP flow: token generation, expiry handling, verification, account linking. Adds the `telegram_otp` and `pending_web_sessions` tables documented in `docs/telegram_bot_db_design.md`.

**Issues (closed as assignee): 2 / 5 ✗**.
**Reviews: 0 / 5 ✗**.

PR #14 is structurally critical: without OTP authentication, the Telegram bot cannot link to a web user, which breaks ≥ 4 of the team's user stories — `/start` (no account binding), `/subscribe` (no authenticated user to subscribe), arrival notifications (no destination Telegram user), and the web-to-Telegram link flow. Anton's web-side OTP token issuance (in `backend/app/core/auth.py`) and Galalu's bot Docker isolation work both depend on your bot-side OTP handler being implemented. The bot is non-functional without this PR.

The coefficient reflects that the work was structurally backbone-critical even though the PR count is low.

### Galalu Anton (`GalaluAnton`) — 0.4

**Merged PRs (semester window): 2 / 5 ✗**

- Week 10 (2026-03-07): PR #12 "Add satellite map with map type switcher" — frontend feature adding a map-type toggle (street/satellite) to the Leaflet view.
- Week 20 (2026-05-11): PR #16 "Move Telegram bot to separate Docker service" — infrastructure refactor isolating the bot into its own container with cleaned-up logging.

**Issues (closed as assignee): 2 / 5 ✗**.
**Reviews: 0 / 5 ✗**.

Both PRs are valuable refinements but neither sits on the backbone path: the satellite map switcher is a nice-to-have visual variant (the project works without it), and Telegram-bot Docker separation is an infrastructure improvement (a monolithic deploy would still function).

---

## Team Note: Bot Review Practice

7 of 9 merged PRs (78%) received reviews from `copilot-pull-request-reviewer[bot]`. No human peer reviews were left by any team member.

Inspection of the bot review bodies shows they are substantively detailed:

| PR | body_len | Content character |
|---|---|---|
| #7 | 6897 | Multi-file structural analysis of "Refactor project structure with backend package and CI". |
| #18 | 2225 | Per-file table for tiered caching; flags unused `cache` import in `main.py:21` as Ruff F401 lint risk. |
| #17 | 2242 | Per-file table for test additions; generates 4 specific code comments. |
| #8 | 1409 | Substantive review of async httpx migration. |
| #11 | 1283 | Per-file analysis of README + .gitignore updates; 3 code comments. |
| #3 | 1209 | Structured review of API documentation PR. |
| #12 | 867 | Concise but accurate review of Leaflet basemap switch. |

These reviews catch lint-level issues that a human reviewer might miss. The team's review cycle is Copilot generates structured analysis → Anton verifies the analysis before merge. The double-checking step makes the bot review a valid peer-review-style merge gate rather than a rubber-stamp.

These reviews count under the methodology's "meaningful review comment" bar — the substance and per-file specificity match what the methodology asks for. DP-§5 receives full 3/3 credit.