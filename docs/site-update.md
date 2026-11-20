# Bloom: website update (Architecture, Setup & Community Feedback)

This is the text and images for the Google Site. Copy each section into the
site, and upload `docs/architecture.png` as the diagram image.

---

## How Bloom works

Bloom helps adults 60+ in Salem, Oregon find local events, interest groups and
volunteer opportunities, in English or Spanish. A short first-visit survey
learns what someone enjoys and when they're free. Bloom then **ranks** every
upcoming event by how well it fits, and explains why. It never hides an event,
so the person stays in control.

![Bloom architecture](architecture.png)

**The pieces**

| Part | Technology | What it does |
| --- | --- | --- |
| Website | HTML, CSS, JavaScript | Welcome page (account, log in or guest), survey, and four tabs: Events, My Events, Chat, Settings. Separate phone and computer layouts, English and Spanish, larger text, high contrast, read aloud, voice input, Terms & privacy. |
| Ask Bloom agent | Rasa Pro CALM 3.21 | Multi-turn conversations in English and Spanish: find events by type, day, time or place; save an event and set a reminder; post an event step by step; "go back" to change the last answer; cancel. An LLM (Rasa-hosted, or your own OpenAI key) turns free-form messages into Rasa commands; with a key, event answers use retrieval-augmented generation (RAG) over the ranked listings. |
| Action server | Python (rasa_sdk) | Ranks events by interests, source, time and distance; checks dates, times and yes/no answers; rewinds the conversation for "go back"; saves events and reminders. |
| Events API | Python | Events board, accounts (email + display name; passwords salted and hashed with PBKDF2-SHA256), saved events, community groups with joins and comments, ZIP/town lookup, sign-in rate limits, and the reminder job. |
| Importer | Python, on start and every 3 hours | Pulls public feeds (Salem Public Library, Press Play Salem, Dave in Salem, Willamette Heritage Center, Willamette Bearcats), removes children's, teen and other irrelevant programs, tags and locates each event. Real events only. |
| Location data | U.S. Census gazetteer (bundled) | Every U.S. ZIP code and town, so place and ZIP + radius search work offline. |
| Reminders | Calendar files, SMTP, Twilio | .ics calendar reminders always work. Email goes to the bundled MailHog demo inbox unless real SMTP is configured; text messages are optional (Twilio). |
| Database | SQLite (Docker volume) | One shared store, so an event saved or posted in the chat shows up on the website right away. |
| Hosting | Docker Compose; Caddy HTTPS on DigitalOcean | One command locally; an always-on public link. |

## Setup overview

**Try it live:** <https://206-189-212-135.sslip.io>

**Run it yourself.** You need Docker Desktop and a Rasa Pro developer license. Nothing else is required.

1. `git clone https://github.com/Sebdeisenhofer/Bloom.git && cd Bloom`
2. `cp .env.example .env`, then paste your license after `RASA_PRO_LICENSE=`
3. `docker compose up --build`
4. Open <http://localhost:8081>. Reminder emails appear at <http://localhost:8025>.

**Demo login:** `demo@bloom.local` / `demo`, or open the site with `?demo`.

**Optional services:** an OpenAI key (faster chat and RAG answers), real email (SMTP) and text messages (Twilio) are set in
`.env`. Without them Bloom still runs and says plainly that those reminders are
not configured.

**Tests:** 61 unit tests and 26 end-to-end conversation tests, including
location search, ZIP + radius, "go back", reminders and Spanish.

---

## Community Feedback

Bloom was reviewed by a Salem local who ran the **Dave in Salem** events blog,
and our teammate ran user testing with older adults. Here is what they told us
and what we changed in response.

**What testers liked (kept):** the warm look and the emoji greetings, choosing a
preferred time of day, and seeing events from several sources.

**What they suggested, and what we changed:**

1. **"The giant block of events isn't working."**
   - Bloom now has six large tabs: Chat, Events, My Events, Volunteer, Community and Settings. Each is at least 60 px tall and works with the keyboard and screen readers.
   - Every page has breadcrumbs and a Back button.
   - Events are grouped under date headings, 10 at a time.
   - Filters cover kind of event, date (today, this week, this weekend, a chosen date), time of day, place and source.
2. **"Use the places Salem people actually check."** Events and listings now come from:
   - Center 50+, which ranks highest
   - Dave in Salem
   - Press Play Salem
   - Salem Reporter
   - Salem Public Library
   - Willamette Heritage Center
   - Deepwood Museum & Gardens
   - Lord & Schryver Conservancy
   - Willamette University
   - Travel Salem
   - Salem Art Association
   - Elsinore Theatre

   Public feeds are imported automatically. Calendars without a feed are linked from the Events page. Every event has **Visit website**, plus **Get tickets** when tickets apply. Gardeners see Deepwood and Lord & Schryver first.
3. **"Let me look somewhere else, like the coast or Portland."**
   - Search by town or region name, or by ZIP code within 5, 10, 25 or 50 miles. This works in the chat and in the Events tab.
   - Nearby events come first, and nothing is hidden.
4. **"Volunteering deserves its own place."** Volunteering is a one-tap category on the Events page.
5. **"People want to start groups, like a French conversation group."**
   - "Neighbor groups" (a category on the Events page) lets neighbors post meetups by interest, and others can join or comment.
   - "Language & conversation groups" is now an interest in the survey and in Events.
6. **"Help me remember."**
   - My Events has calendar files that work everywhere.
   - Email reminders are demoed with MailHog, and text reminders work when Twilio is set up.
   - Reminders can go 1 day or 2 hours before an event.
   - In the chat you can say "Save the garden tour", then "remind me a day before".
7. **"Let me fix my last answer."** In the chat, "go back" or the **↩ Previous question** button returns to the last question so you can change it.
8. **"Not everyone is most comfortable in English."**
   - Spanish runs throughout: the website, every assistant message, and voice input and read-aloud.
   - A language picker is on the welcome page and in Settings.
9. **Accounts and accountability.**
   - Sign in with any email and a display name.
   - Guests can still browse, and their saves move into the account when they sign up.
   - Shared events show who posted them, and events reported by several people are hidden.

---

### Second round of feedback (November 20)

After testing the first redesign, our team and the Dave in Salem blogger asked for a calmer, denser layout and only real events. What we changed:

1. **Simpler navigation.** Four tabs in the order people use them: **Events, My Events, Chat, Settings**. Volunteer and Community became categories inside Events.
2. **Less scrolling.**
   - The Events page uses the full screen width, with compact cards in a grid (four across on a laptop).
   - Results come in numbered pages of 12.
   - A weekly class appears once, with its other dates under *More details*.
   - A category bar, one search box and a day picker replace the long filter form. The rest sits under *More filters*.
3. **Smaller, cleaner cards.**
   - The default size is about 25% smaller; *Larger text* is still one tap away.
   - The date appears only in the date block, and the place only once.
   - Tags and other details moved behind *More details*.
4. **Who posted it.** Each organization has its own badge on every card, and people can add a profile picture.
5. **Only real, relevant events.**
   - All invented sample events are gone.
   - Job-search, ESL, board-meeting and roller-skate listings are filtered out, along with children's programs.
   - The 25 calendars the blogger recommended are linked on the Events page.
6. **Reminders further ahead:** 2 hours, 1 day, 3 days, 1 week or 2 weeks before.
7. **A bigger, sturdier chat.**
   - The chat fills the screen, with a full-screen button.
   - Suggested questions show on phones too.
   - Common questions still work when the shared AI service is busy.
   - An optional OpenAI key gives faster replies and RAG answers.
8. **Phone and computer layouts.** Phones get a single column and a bottom tab bar; computers get the wide grid. The site picks the layout automatically.
9. **Trust and safety.**
   - A visible AI notice sits in the chat and the footer.
   - A Terms & privacy page covers AI use, events, acceptable use, data, security and limits of responsibility. New accounts must agree to it.
   - Passwords are hashed with PBKDF2-SHA256 and must be at least 8 characters.
   - Sign-in attempts are rate limited, sessions expire after 30 days, and security headers are on.

## Screenshots to add to the site

Ready-made screenshots are in `docs/screenshots/`:

1. `01-welcome.png`: the welcome page with the English / Español picker
2. `02-survey-interests.png`: the survey, with interests grouped in four columns
3. `03-events-laptop.png`: the Events tab on a laptop (category bar, card grid, page numbers)
4. `04-card-more-details.png`: an event card with *More details* open
5. `05-sources-and-calendars.png`: "Where these events come from" and the linked calendars
6. `06-my-events-reminders.png`: My Events with the reminder panel (2 hours to 2 weeks)
7. `07-chat-full-screen.png`: the chat in full screen, with the AI notice
8. `08-terms-privacy.png`: the Terms & privacy page
9. `09-settings-large-text-contrast.png`: Settings with larger text and high contrast
10. `10-chat-spanish-go-back.png`: the chat in Spanish, going back with "volver atrás"
11. `11-events-phone-es.png`: the Events tab on a phone (in Spanish), with the bottom tab bar
