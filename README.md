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

Everything beyond the Rasa license is optional. Features that need an outside service (real email, text messages, Ticketmaster) are **turned off gracefully**: the app says so plainly (for example "Text reminders not configured") and keeps working.

## What's in the app

Visitors land on a **welcome page** with three choices: *Create a free account*, *Log in* or *Continue as a guest*. A language picker (English / Español) sits at the top. New visitors then take a short survey. After that, Bloom has six large tabs. Each tab is at least 60 px tall, keyboard accessible (arrow keys, Home and End) and labelled for screen readers, and every page has breadcrumbs and a Back button.

| Tab | What it does |
| --- | --- |
| 💬 **Chat** | Ask Bloom (Rasa). Find events by type, day, time or place ("garden events near Silverton", "within 5 miles of 97302"). Save an event, set a reminder, or post an event step by step. Say **"go back"** or tap **↩ Previous question** to return to the last question and change the answer; "cancel" stops a task. Event replies include **Visit website** and **Get tickets** buttons. |
| 📅 **Events** | Every upcoming event. Filters: kind, date (today / next 7 days / this weekend / pick a date), time of day, source, and place or ZIP code with a radius (5, 10, 25, 50 mi). Results are grouped under date headings with category chips, 10 at a time with **Show more**. "Top picks" and a *Best match first* view use the survey. **➕ Share an event** opens a guided form. |
| ⭐ **My Events** | Saved events, from the website or the chat. Each one has **Add to calendar** (.ics, works with Apple, Google and Outlook with no setup) and reminder settings: 1 day or 2 hours before, by email and/or text. |
| 🤝 **Volunteer** | Volunteer opportunities as their own list. |
| 🏡 **Community** | Neighbors post meetups and interest groups (for example a French conversation group meeting Thursdays), organized by interest. Others can join or comment. |
| ⚙️ **Settings** | Language, text size (three steps), high contrast, read aloud, reminder contacts and timing, account, and survey answers. |

**Accounts.** You sign in with any email address and a display name. Your profile, saved events and preferences are stored under that account and follow you to any device. Guests work fully with a browser ID, and their answers and saved events merge into the account when they sign up. Accounts also have a password: on a public link, an email-only login would let anyone sign in as anyone. Passwords are salted PBKDF2 hashes, and emails are never shown publicly. Sharing an event or starting a group needs an account, so neighbors know who is hosting. Neighbors' events show who shared them and how many they've shared, and three "Report a problem" flags hide an event.

## Event sources

Bloom credits and links to every organization it lists. Sources marked **Live** are imported automatically on startup and every 3 hours, from public feeds only, with a descriptive User-Agent and a handful of requests per run. Bloom respects each site's robots.txt and doesn't scrape pages.

| Source | How it's included |
| --- | --- |
| [Center 50+](https://www.cityofsalem.net/community/seniors-and-center-50) (Salem's senior center) | Sample listings; **weighted highest** in ranking |
| [Dave in Salem](https://daveinsalem.wordpress.com/) | Live: the blog's WordPress RSS feed (each post announces one dated event) |
| [Press Play Salem](https://pressplaysalem.com/calendar/) | Live: public community calendar feed |
| [Salem Reporter](https://www.salemreporter.com/) | Sample listings |
| [Salem Public Library](https://cityofsalemlibrary.libcal.com/calendar) | Live: public LibCal iCal feed |
| [Willamette Heritage Center](https://www.willametteheritage.org/calendar/) | Live: public calendar feed |
| [Deepwood Museum & Gardens](https://deepwoodmuseum.org/event-calendar/) | Sample listings (garden events) |
| [Lord & Schryver Conservancy](https://lordschryver.org/) | Sample listings (garden events) |
| [Willamette University](https://events.willamette.edu/) | Live: Bearcats home games (Northwest Conference iCal feed). Arts and lectures are sample listings |
| [Travel Salem](https://www.travelsalem.com/events/) | Sample listings |
| [Salem Art Association](https://salemart.org/) | Sample listings |
| [Elsinore Theatre](https://elsinoretheatre.com/) | Sample listings with a **Get tickets** link |

**About sample listings.** Several organizations don't publish a machine-readable feed, so Bloom includes **sample listings** written for this class project (`actions/sources.py`). They are realistic examples, *not* real scheduled events:
- Every sample is marked **Sample listing** on its card, and its details say to check the organization's website for real dates.
- **Visit website** goes to the real organization.
- A live source falls back to its samples if its feed fails or the container has no internet, and real listings replace the samples automatically when the feed works again.

Children's and teen programs are filtered out for this audience. A gardening-focused profile ranks Deepwood and Lord & Schryver first.

**Optional:** `TICKETMASTER_API_KEY` adds concerts and shows, and `EXTRA_ICAL_FEEDS` adds any public iCal feed (see `.env.example`).

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

Reminders are sent 1 day or 2 hours before, in the person's language, by a background job in the events API that checks every minute. In My Events, **Send a test reminder now** delivers one right away, which is handy for demos with MailHog. In chat: "Save the Gaiety Hollow Garden Tour", then "Remind me 1 day before".

## Languages

English and Spanish throughout:
- **The assistant:** Rasa `additional_languages: [es]`, with `translation:` blocks on every response and a `set_language` flow that sets Rasa's built-in `language` slot. Custom actions use `actions/i18n.py`.
- **The website:** every label is in `web/i18n.js` (English) and `web/i18n-es.js` (Spanish).
- **Speech:** read aloud and speech-to-text switch to `es-US` / `en-US`.
- **Survey and Events:** both include **Language & conversation groups**.

Event titles stay in the language of their source.

## Tests

```sh
# Unit tests (54): ranking, sources and fallback, location search, go back, reminders, Spanish
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
  real_events.py  Importer for live feeds, with sample-listing fallback (startup + every 3 h)
  sources.py      Source list (names, links, weights), known venues, sample listings
  geo.py          ZIP, town and region lookup (bundled Census data in actions/data/)
  notify.py       Email (SMTP) and text (Twilio) delivery, optional
  i18n.py         Assistant messages in English and Spanish
data/             CALM flows (flows.yml) and keyword shortcuts (nlu.yml)
domain.yml        Slots, responses (with Spanish translations), actions
web/              Website: index.html, app.js, reminders.js, i18n.js, i18n-es.js, styles.css
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
- **No real events showing:** the container may be offline. Sample listings fill in, and the importer retries every 3 hours. Check `docker compose logs events-api`.
- **Speech input missing:** some browsers don't support the Web Speech API. Typing always works.

Architecture: [docs/architecture.md](docs/architecture.md). Website text and the community feedback summary: [docs/site-update.md](docs/site-update.md).
