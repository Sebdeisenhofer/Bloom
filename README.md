# Bloom

A conversational assistant for adults 60 and older in Salem, Oregon. It learns a few activity preferences, helps people discover local events, explains why events may fit, and lets neighbors post events and save RSVPs. The interface uses large text, high-contrast controls, speech input, and optional read-aloud.

Event ranking uses transparent interest-tag overlap, preferred time of day, and preferred group size. **It never hides an event**: every event remains available, even when it is a low-ranked match. People stay in control of what feels right for them.

## Requirements

- Docker Desktop with Docker Compose v2.
- A valid Rasa Pro license. The Rasa Pro model image needs to be available to your Docker runtime.
- Internet access for the configured Rasa tutorial command-generator endpoint during conversation.

The app is configured for **Rasa Pro 3.21.3**, matching the known-good local CALM setup. The project configuration uses its `CompactLLMCommandGenerator` and `rasa_command_generation_model` group.

## Start the app

1. Make a local environment file:

   ```sh
   cp .env.example .env
   ```

2. Edit `.env` and set `RASA_PRO_LICENSE` to the license provided by your Rasa Pro account/instructor. Do not commit this file.
3. From this project folder, start the full stack:

   ```sh
   docker compose up --build
   ```

4. Open <http://localhost:8081>.

The first startup builds the images, seeds the SQLite database with 25 sample Salem-area events, trains the CALM model, then serves the app. Training can take several minutes. SQLite and the trained model are retained in Docker volumes.

Stop the stack with Ctrl+C. To run it in the background, use `docker compose up --build -d`; view logs with `docker compose logs -f`.

## Verification and sample user

No sample account password is needed. The web page creates a browser-local sender ID and retains it in local storage so the profile can be recognized on that browser. Clear the browser's local storage to try a fresh onboarding conversation.

For a direct REST check, send a message using an example sender ID:

```sh
curl -sS -X POST http://localhost:5006/webhooks/rest/webhook \
  -H 'Content-Type: application/json' \
  -d '{"sender":"salem-demo-01","message":"Find book clubs near me"}'
```

The REST reply includes text and a custom `events` payload. Because filters change ranking, the exact event order depends on the message and profile.

## Tests

The project includes CALM conversation scenarios in `tests/e2e_tests.yml`, covering onboarding, search and RSVP, event creation, a search digression during event creation, and cancellation. With the Rasa Pro CLI available, validate the project and run E2E tests using the commands supported by your installed 3.21.3 CLI:

```sh
rasa data validate
rasa test e2e tests/e2e_tests.yml
```

The `tests/test_actions.py` unit tests cover seed data, ranking order and inclusion, filters, and profile persistence. Run them with Python 3.11 and the Rasa SDK installed:

```sh
python -m unittest discover -s tests -p 'test_*.py'
```

The local assistant also exposes the standard Rasa status endpoint at `http://localhost:5006/status`.

## Accessibility

- The default body type is 20 px, with larger headings and an extra-large-text toggle.
- High contrast can be enabled without losing the standard theme.
- Buttons have at least 60 px minimum height, visible keyboard focus, and comfortable spacing.
- The chat supports keyboard navigation, labeled input, and an `aria-live` message log.
- Speech-to-text uses the browser Web Speech API when available, shows a listening state, and falls back to typed input when unsupported.
- Read-aloud uses browser speech synthesis and can be turned off at any time.
- Quick replies and event cards allow tapping instead of typing.
- Short, plain-language replies and one-at-a-time CALM slot questions support an unhurried conversation.

## Project structure

```text
.
├── actions/                 # Rasa custom actions and action-server image
├── data/flows.yml           # CALM conversation flows
├── docs/                    # Architecture and website update content
├── tests/                   # CALM E2E scenarios and action unit tests
├── web/                     # Static accessible single-page app
├── config.yml               # Rasa CALM 3.21.3 configuration
├── domain.yml               # Slots, responses, and action declarations
├── docker-compose.yml        # Rasa, actions, and Nginx services
├── Dockerfile                # Rasa Pro image, training, and server
└── nginx.conf                # Static hosting and same-origin REST proxy
```

## Troubleshooting

- **Port 8081 is already in use:** stop the other service or change the host side of `8081:80` in `docker-compose.yml`.
- **Port 5006 is already in use:** stop the other service or change the host side of `5006:5005`. Nginx still uses the internal service address.
- **Missing license:** make sure `.env` exists and `RASA_PRO_LICENSE` contains a valid Rasa Pro license. Compose intentionally refuses to start without it.
- **Slow first startup:** model training is expected on the first run; inspect `docker compose logs -f rasa`. Later starts reuse the trained image/container model.
- **Chat service unavailable:** check `docker compose ps` and `docker compose logs -f rasa action-server web`. Rasa starts after the action server is healthy, and Nginx starts after Rasa is healthy.
- **Speech input unavailable:** some browsers do not support Web Speech API. Type in the message box instead.

Architecture and conversation sequence diagrams are in [docs/architecture.md](docs/architecture.md). A short copy-ready overview and screenshot checklist are in [docs/site-update.md](docs/site-update.md).
