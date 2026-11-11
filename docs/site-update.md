# Bloom: site update

Bloom is a conversational helper for adults 60 and older who want to feel more connected. It learns a few activity preferences, finds local events, explains why an activity may fit, and helps neighbors post events and RSVP.

The browser app is served by Nginx. Nginx forwards chat messages to Rasa Pro, which manages the conversation and calls a Python action server. The action server stores profiles, community events, and RSVPs in SQLite. Event recommendations are ranked by transparent preference matches, but every event remains available to browse.

## Setup overview

Install Docker Desktop, copy `.env.example` to `.env`, add a valid Rasa Pro license, then run `docker compose up --build`. Open <http://localhost:8081>. The first startup trains the CALM assistant and may take a few minutes.

## Suggested screenshots

- Welcome page with larger text, high contrast, and read-aloud controls.
- Speech input showing its listening state.
- Onboarding questions and profile preferences.
- Event results with match explanations and “Tell me more” buttons.
- Event details and RSVP confirmation.
- Event hosting confirmation and posted result.
- Architecture diagram from `docs/architecture.md`.
