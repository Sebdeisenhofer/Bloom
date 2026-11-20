# Bloom

Bloom helps adults 60+ in Salem, Oregon find local events, interest groups and volunteer opportunities, and share their own. It pairs an accessible website with **Ask Bloom**, a Rasa Pro CALM assistant that holds multi-turn conversations in English and Spanish.

Bloom **ranks events but never hides them**. A short survey (interests, part of town, days, time of day, accessibility needs) decides the order, and every card says why it was suggested. People stay in control.

## Quick start

You only need Docker Desktop and a Rasa Pro license.

```sh
cp .env.example .env          # then paste your license after RASA_PRO_LICENSE=
docker compose up --build
```

| Open | What |
| --- | --- |
| <http://localhost:8081> | Bloom |
| <http://localhost:8025> | MailHog demo inbox (reminder emails land here) |
| <http://localhost:5006/status> | Rasa status |

The first start builds the images, trains the assistant (a few minutes), imports real events and serves the app. Later starts are quick. The model **retrains automatically** when `config.yml`, `domain.yml` or `data/` change. **Demo login:** `demo@bloom.local` / `demo`, or open <http://localhost:8081/?demo>.

Everything beyond the Rasa license is optional. Features that need an outside service (an OpenAI key, real email, text messages, Ticketmaster) are **turned off gracefully**: the app says so plainly (for example "Text reminders not configured") and keeps working.

## What's in the app

Visitors land on a **welcome page** with three choices: *Create a free account*, *Log in* or *Continue as a guest*, plus an English / Español picker. New visitors take a short survey (interests are grouped into four columns: outdoors, arts, learning, social). Then Bloom has **four tabs**, in this order:

| Tab | What it does |
| --- | --- |
| 📅 **Events** (home) | Every upcoming real event. A **category bar** (biggest categories first) includes **🤝 Volunteer** and **🏡 Neighbor groups**, so volunteering and community groups are categories, not separate tabs. One simple search box and a day picker; time of day, source, place/ZIP + radius and sort order are under **More filters**. Results come in **pages of 12** with numbered page buttons, grouped by date, in a grid that uses the full screen width. Weekly classes appear **once** with their other dates under *More details*. Cards are compact: date block, the organization's badge, title, time and cost, place; everything else is behind **More details**. |
| ⭐ **My Events** | Saved events (from the website or the chat), with **Add to calendar** and reminders **2 hours, 1 day, 3 days, 1 week or 2 weeks** before, by email and/or text. |
| 💬 **Chat** | Ask Bloom (Rasa) fills the screen under the tabs, with a **⛶ Full screen** button. A visible **AI notice** sits at the top. Suggested questions appear inside the conversation (so they show on phones). "Go back" and "cancel" work as before. |
| ⚙️ **Settings** | Profile picture, language, text size, high contrast, read aloud, reminder contacts and default timing, account, and survey answers. |

**Phone and computer layouts** are chosen automatically by screen width: computers get a wide multi-column layout with tabs at the top; phones get a single column, a compact header and a **bottom tab bar**.

**Terms & privacy** (`#terms`, linked in the footer, the chat and the sign-up form) explains the AI use, that events come from other organizations, acceptable use, what data is stored, security, and limits of responsibility. Creating an account requires agreeing to it.

### Accounts and data

You sign in with an email address, a display name and a password (at least 8 characters). On the server (SQLite in a Docker volume) Bloom stores: email, display name, the password **hash**, survey answers, saved events, reminders and an optional profile picture (shrunk to 128×128 in the browser and stored as a small image string). Guests' answers stay in their browser (`localStorage`) and merge into an account if they sign up.

**Passwords are never stored.** Each password gets a random 16-byte salt and is hashed with **PBKDF2-HMAC-SHA256, 200,000 rounds**, and logins compare hashes in constant time. (Plain SHA-256 would be too fast to resist guessing; PBKDF2 is deliberately slow.) Sharing an event or starting a group needs an account, so neighbors know who is hosting.

### Security

- Passwords: salted PBKDF2-SHA256 as above. Sign-in tokens are random (256-bit) and **expire after 30 days**.
- **Rate limits:** at most 10 failed sign-ins per address or email per 15 minutes; test reminders need sign-in and are limited to 3 per hour.
- **Headers** (nginx): Content-Security-Policy (scripts only from this site), `X-Frame-Options: DENY`, `nosniff`, a strict referrer policy, microphone only for this site; HSTS on the public HTTPS server.
- **Input limits:** request bodies are capped, every field is length-limited and cleaned, links must be `http(s)`, and the database is only reached through parameterized queries.
- `.env` (license and keys) is git-ignored and never committed.

## Event sources

Bloom shows **only real events**. Sources marked **Live** are imported automatically on startup and every 3 hours, from public feeds only, with a descriptive User-Agent and a handful of requests per run. Bloom respects each site's robots.txt and doesn't scrape pages. Each organization has its own badge on event cards, and the Events page lists where events come from.

| Source | How it's included |
| --- | --- |
| [Center 50+](https://www.cityofsalem.net/community/seniors-and-center-50) (Salem's senior center) | Linked; **weighted highest** in ranking if a feed is added |
| [Dave in Salem](https://daveinsalem.wordpress.com/) | Live: the blog's WordPress RSS feed (each post announces one dated event) |
| [Press Play Salem](https://pressplaysalem.com/calendar/) | Live: public community calendar feed |
| [Salem Reporter](https://www.salemreporter.com/) | Linked (no public feed) |
| [Salem Public Library](https://cityofsalemlibrary.libcal.com/calendar) | Live: public LibCal iCal feed |
| [Willamette Heritage Center](https://www.willametteheritage.org/calendar/) | Live: public calendar feed |
| [Deepwood Museum & Gardens](https://deepwoodmuseum.org/event-calendar/) | Linked (no public feed) |
| [Lord & Schryver Conservancy](https://lordschryver.org/) | Linked (no public feed) |
| [Willamette University](https://events.willamette.edu/) | Live: Bearcats home games (Northwest Conference iCal feed) |
| [Travel Salem](https://www.travelsalem.com/events/) | Linked (no public feed) |
| [Salem Art Association](https://salemart.org/) | Linked (no public feed) |
| [Elsinore Theatre](https://elsinoretheatre.com/) | Linked (no public feed) |

**More calendars.** A local events blogger recommended 25 Salem-area calendars (Hallie Ford Museum, Theatre 33, Oregon Symphony, Chemeketa Cellars, Venti's Cafe, Western Oregon University, Albany River Rhythms, City of Salem and more). None of them offers a feed Bloom can import, so the Events page links to all of them under **More Salem-area calendars to explore**. Adding a real feed later only means adding a loader in `actions/real_events.py`.

**Sample listings** (invented examples in `actions/sources.py`) are **off** in the app. They load only with `BLOOM_SAMPLE_EVENTS=1`, which the unit tests use so their results don't depend on today's real listings.

Children's and teen programs, job/ESL classes, board meetings and roller-skate nights are filtered out for this audience, and repeating listings are shown once.

**Optional:** `TICKETMASTER_API_KEY` adds concerts and shows, and `EXTRA_ICAL_FEEDS` adds any public iCal feed (see `.env.example`).

## AI: the chat model and RAG answers

By default the chat uses Rasa's free shared tutorial LLM, which needs no key but is sometimes overloaded. When that happens Bloom still answers searches, event details, saves, reminders and help from keywords (`action_llm_fallback`).

**Optional OpenAI key.** Put `OPENAI_API_KEY=` in `.env` and run `docker compose up --build`. The Rasa container then uses `endpoints-openai.yml` (`gpt-4.1-mini`) instead of the shared endpoint, which is faster and more reliable. It costs a few cents for a class demo.

**RAG (retrieval-augmented generation).** With a key, chat answers about events are written by the LLM from **retrieved listings only** (`actions/rag.py`):
1. **Retrieve:** Bloom's ranking (`rank_events`) picks the 8 most relevant upcoming events for the question, the visitor's interests and any place they named.
2. **Augment:** those listings (title, date, time, place, cost, description, source, distance) go into the prompt with instructions to use only them and never invent events.
3. **Generate:** a 2–3 sentence answer in English or Spanish, shown above the event cards. Without a key, or if the call fails, Bloom uses its built-in wording.

## Location search

Every event stores a latitude and longitude. The **U.S. Census 2020 Gazetteer** files (public domain) are bundled in `actions/data/`, covering every U.S. ZIP code and city/town, so place and ZIP search work **offline and nationwide**:
- **Town names** ("Silverton", "Portland, ME"): Oregon is preferred unless a state is given.
- **Regions:** "the coast" means Lincoln City, Newport, Cannon Beach and other coastal towns; there are also the Portland area, the Mid-Valley and the Gorge.
- **ZIP code + radius** ("within 10 miles of 97301").

Nearby events come first and the rest follow by distance; nothing is hidden. Real listings are Salem-focused today, and expanding coverage elsewhere only requires adding sources.

## Reminders, email and text messages

| Channel | Setup | Without setup |
| --- | --- | --- |
| 📅 Calendar (.ics with an alarm) | None | Always works |
| ✉️ Email | Defaults to the bundled **MailHog** inbox at <http://localhost:8025>. For real email, set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS` in `.env` | `SMTP_HOST=` (empty) turns it off: "Email reminders not configured" |
| 💬 Text (Twilio) | Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | Shows "Text reminders not configured" and logs what would have been sent (`docker compose logs events-api`) |

Reminders are sent 2 hours, 1 day, 3 days, 1 week or 2 weeks before, in the person's language, by a background job in the events API that checks every minute. In My Events, **Send a test reminder now** delivers one right away, which is handy for demos with MailHog. In chat: "Save the Brown Bag Book Club", then "Remind me 1 week before".

## Languages

English and Spanish throughout:
- **The assistant:** Rasa `additional_languages: [es]`, with `translation:` blocks on every response and a `set_language` flow that sets Rasa's built-in `language` slot. Custom actions use `actions/i18n.py`.
- **The website:** every label is in `web/i18n.js` (English) and `web/i18n-es.js` (Spanish).
- **Speech:** read aloud and speech-to-text switch to `es-US` / `en-US`.
- **Survey and Events:** both include **Language & conversation groups**.

Event titles stay in the language of their source.

## Tests

```sh
# Unit tests (61): ranking, sources and fallback, location search, go back, reminders, RAG, Spanish
docker compose run --rm --no-deps -e SMTP_HOST= -v "$PWD/tests:/app/tests:ro" --entrypoint python action-server -m unittest discover -s tests

# Conversation (end-to-end) tests (26), with the app running
docker compose build rasa && docker compose run --rm --no-deps rasa rasa test e2e tests/e2e_tests.yml
```

The end-to-end tests cover:
- onboarding, search, help and cancel
- yes/no confirmation in eight phrasings
- posting and finding an event, and the optional description
- browsing by town and by region, ZIP + radius
- going back mid-flow (typed and with the button)
- saving an event and setting a reminder
- a Spanish conversation

They call the LLM, so an occasional failure can be the shared endpoint being busy. Re-run before debugging. The tests post events titled "E2E Test …"; remove them afterwards with:

```sh
docker compose exec events-api python -c "from actions.actions import connect; db=connect(); db.execute(\"DELETE FROM events WHERE title LIKE 'E2E Test%'\"); db.commit()"
```

## Accessibility

- Large base type (19 px) with two larger sizes, and a high-contrast theme.
- Buttons and tabs are at least 44–64 px, with strong focus outlines.
- Read aloud with a Stop button, speech-to-text in chat, and `aria-live` updates.
- One question at a time in the survey, the share form and the chat, with "go back" everywhere.
- Plain-language explanations of why an event was suggested.

## Project structure

```text
actions/
  actions.py      Rasa custom actions: search and ranking, posting, go back, reminders, language
  events_api.py   JSON API: events, accounts, saved events, reminders, community feed, geo lookup
  real_events.py  Importer for live feeds, relevance filter (startup + every 3 h)
  sources.py      Source list (names, links, weights), known venues, test-only samples
  geo.py          ZIP, town and region lookup (bundled Census data in actions/data/)
  notify.py       Email (SMTP) and text (Twilio) delivery, optional
  rag.py          Retrieval-augmented answers from the ranked listings (needs OPENAI_API_KEY)
  i18n.py         Assistant messages in English and Spanish
data/             CALM flows (flows.yml) and keyword shortcuts (nlu.yml)
domain.yml        Slots, responses (with Spanish translations), actions
web/              Website: index.html, app.js, reminders.js, i18n.js, i18n-es.js, i18n-more.js, styles.css
endpoints-openai.yml  Used instead of endpoints.yml when OPENAI_API_KEY is set
tests/            Unit tests and Rasa end-to-end tests
deploy/           DigitalOcean setup and update scripts, Caddy HTTPS config
docs/             Architecture diagram, deployment guides, website text
```

Services in `docker-compose.yml`:
- `rasa` (port 5006)
- `action-server`
- `events-api`
- `web` (nginx, port 8081)
- `mailhog` (port 8025)

`docker-compose.prod.yml` adds Caddy for HTTPS on a public server (see [docs/deploy-digitalocean.md](docs/deploy-digitalocean.md)).

## Troubleshooting

- **A port is in use (8081, 5006 or 8025):** change the left side of that port mapping in `docker-compose.yml`.
- **Missing license:** Compose refuses to start without `RASA_PRO_LICENSE` in `.env`.
- **Chat says it's having trouble:** the shared LLM endpoint may be busy. Wait a moment. The Events tab works without the chat.
- **No events showing:** the container may be offline (the importer needs internet). It retries every 3 hours; check `docker compose logs events-api`.
- **Speech input missing:** some browsers don't support the Web Speech API. Typing always works.

Architecture: [docs/architecture.md](docs/architecture.md). Website text and the community feedback summary: [docs/site-update.md](docs/site-update.md).
