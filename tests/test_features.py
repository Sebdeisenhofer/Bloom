"""Tests for the community-feedback update: sources, location search, go back, reminders, Spanish."""

import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from actions import actions, geo, notify, real_events
from actions.i18n import t
from actions.sources import SAMPLES, sample_rows


class Tracker:
    def __init__(self, slots=None, text="", sender_id="tester", stack=None, entities=None, metadata=None):
        self.slots = dict(slots or {})
        self.sender_id = sender_id
        self.latest_message = {"text": text, "entities": entities or [], "metadata": metadata or {}}
        self.stack = stack or []
        self.events = []

    def get_slot(self, key):
        return self.slots.get(key)


class Dispatcher:
    def __init__(self):
        self.messages = []

    def utter_message(self, text=None, **kwargs):
        self.messages.append({"text": text, **kwargs})


class TempDb(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        actions.DB_PATH = str(Path(self.temp_dir.name) / "community.sqlite3")
        actions.initialize_database()

    def tearDown(self):
        self.temp_dir.cleanup()


class LocationTests(unittest.TestCase):
    def test_zip_codes_work_offline_nationwide(self):
        self.assertAlmostEqual(geo.zip_point("97301")[0], 44.95, places=1)
        self.assertIsNotNone(geo.zip_point("10001"))  # New York
        self.assertIsNotNone(geo.zip_point("99501"))  # Anchorage

    def test_town_names_prefer_oregon_unless_a_state_is_given(self):
        self.assertEqual(geo.parse_location("events near Lincoln City")["label"], "Lincoln City, OR")
        self.assertEqual(geo.parse_location("events in Portland, ME")["label"], "Portland, ME")
        self.assertEqual(geo.lookup("Boise, ID")["state"], "ID")

    def test_zip_with_radius(self):
        where = geo.parse_location("Show me events within 5 miles of 97302")
        self.assertEqual((where["label"], where["radius"], where["kind"]), ("97302", 5, "zip"))

    def test_coast_covers_coastal_towns_not_salem(self):
        coast = geo.parse_location("anything on the coast?")
        self.assertIn("Lincoln City", coast["towns"])
        self.assertIn("Cannon Beach", coast["towns"])
        self.assertGreater(geo.distance_to(coast, 44.9429, -123.0351), 40)  # Salem is ~46 mi from the nearest coastal town

    def test_ordinary_requests_have_no_location(self):
        for text in ("Find music events", "events in the morning", "find book clubs near me"):
            self.assertIsNone(geo.parse_location(text), text)


class SearchByLocationTests(TempDb):
    def test_chat_search_near_a_town_puts_nearby_events_first(self):
        dispatcher = Dispatcher()
        actions.ActionSearchEvents().run(dispatcher, Tracker(text="Find events near Silverton"), {})
        self.assertIn("within 10 miles of Silverton", dispatcher.messages[0]["text"])
        first = dispatcher.messages[0]["json_message"]["events"][0]
        self.assertIn("Silverton", first["location"])

    def test_every_event_is_still_ranked(self):
        ranked = actions.rank_events({}, "", geo.parse_location("near 97301"))
        self.assertEqual(len(ranked), len(SAMPLES))

    def test_event_cards_carry_website_and_ticket_links(self):
        cards = [actions.event_card(e) for e in actions.rank_events({}, "")]
        self.assertTrue(all(c["source_url"].startswith("https://") for c in cards))
        self.assertTrue(any(c["ticket_url"] for c in cards))  # Elsinore samples


class GoBackTests(unittest.TestCase):
    def stack(self, step):
        return [
            {"flow_id": "create_event", "step_id": step, "type": "flow"},
            {"flow_id": "pattern_collect_information", "type": "pattern_collect_information", "collect": "x"},
            {"flow_id": "go_back", "step_id": "START", "type": "flow"},
        ]

    def test_goes_back_one_question_and_clears_both_answers(self):
        plan = actions.go_back_plan(self.stack("ask_location"))
        self.assertEqual(plan["restart_after"], "ask_date")
        self.assertEqual(plan["clear"], ["event_time", "event_location"])

    def test_going_back_from_the_confirmation_re_asks_the_description(self):
        plan = actions.go_back_plan(self.stack("ask_confirmation"))
        self.assertEqual(plan["question_slot"], "event_description")
        self.assertEqual(plan["restart_after"], "ask_host")

    def test_first_question_has_nothing_before_it(self):
        self.assertTrue(actions.go_back_plan(self.stack("ask_title"))["first"])

    def test_action_patches_the_dialogue_stack(self):
        dispatcher = Dispatcher()
        events = actions.ActionGoBack().run(dispatcher, Tracker(stack=self.stack("ask_time")), {})
        self.assertEqual(events[0]["event"], "stack")
        self.assertIn('"remove", "path": "/1"', events[0]["update"])
        self.assertIn("previous question", dispatcher.messages[0]["text"])

    def test_nothing_to_go_back_to_outside_a_task(self):
        dispatcher = Dispatcher()
        actions.ActionGoBack().run(dispatcher, Tracker(stack=[]), {})
        self.assertIn("no question to go back to", dispatcher.messages[0]["text"])


class ImporterTests(TempDb):
    def test_failed_feeds_fall_back_to_samples(self):
        def broken():
            raise OSError("no internet")

        counts = real_events.refresh(loaders=[("library", broken)])
        self.assertEqual(counts["library"], "error, using samples")
        with actions.connect() as db:
            library = db.execute("SELECT * FROM events WHERE source = 'library'").fetchall()
        self.assertTrue(library and all(r["is_sample"] == 1 for r in library))

    def test_live_feed_replaces_that_sources_samples(self):
        today = date.today() + timedelta(days=2)
        live = [{
            "external_id": "library:test-1", "source": "library", "title": "Real Book Talk", "date": today.isoformat(),
            "time": "2:00 PM", "end_time": "3:00 PM", "location": "Main Library", "category": "Talk", "tags": "books",
            "group_size": "small", "description": "A real event.", "host": "Salem Public Library", "area": "downtown",
            "cost": "Free", "needs": "", "url": "https://example.org/e/1", "source_url": "https://example.org/e/1",
            "ticket_url": "", "is_sample": 0, "lat": 44.93, "lon": -123.04, "city": "Salem",
        }]
        real_events.refresh(loaders=[("library", lambda: live)])
        with actions.connect() as db:
            titles = [r["title"] for r in db.execute("SELECT title FROM events WHERE source = 'library'")]
            deepwood = db.execute("SELECT COUNT(*) FROM events WHERE source = 'deepwood'").fetchone()[0]
        self.assertEqual(titles, ["Real Book Talk"])
        self.assertGreater(deepwood, 0)  # sources without feeds keep their samples

    def test_dave_in_salem_titles_are_parsed_into_dated_events(self):
        day = date.today() + timedelta(days=5)
        title = f"Salem Hardy Plant Society – Sat. {day.strftime('%b')}. {day.day}th in #SalemOR"
        rss = (f"<rss><channel><item><title>{title}</title><link>https://daveinsalem.wordpress.com/x</link>"
               f"<pubDate>Mon, 01 {day.strftime('%b')} {day.year} 10:00:00 +0000</pubDate>"
               "<description>Join us at 7 pm for a garden talk.</description></item></channel></rss>")
        with mock.patch.object(real_events, "fetch", return_value=rss.encode()):
            rows = real_events.dave_in_salem_events()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Salem Hardy Plant Society")
        self.assertEqual(rows[0]["date"], day.isoformat())
        self.assertEqual(rows[0]["time"], "7:00 PM")
        self.assertIn("gardening", rows[0]["tags"])

    def test_samples_are_labelled_and_never_stale(self):
        rows = sample_rows()
        self.assertTrue(all(r["is_sample"] == 1 and r["date"] > date.today().isoformat() for r in rows))


class ReminderTests(TempDb):
    def test_send_times(self):
        event = {"date": "2026-12-05", "time": "2:00 PM"}
        self.assertEqual(actions.reminder_send_at(event, "1d"), "2026-12-04T14:00")
        self.assertEqual(actions.reminder_send_at(event, "2h"), "2026-12-05T12:00")

    def test_text_reminders_are_disabled_gracefully_without_keys(self):
        with mock.patch.dict(os.environ, {"TWILIO_ACCOUNT_SID": "", "TWILIO_AUTH_TOKEN": "", "TWILIO_FROM_NUMBER": ""}):
            self.assertFalse(notify.sms_ready())
            self.assertEqual(notify.send_sms("503-555-0123", "hi"), (False, "Text reminders not configured"))

    def test_email_is_disabled_when_no_smtp_host(self):
        with mock.patch.dict(os.environ, {"SMTP_HOST": ""}):
            ok, detail = notify.send_email("a@example.com", "s", "b")
        self.assertFalse(ok)
        self.assertIn("not configured", detail)

    def test_reminder_text_in_spanish(self):
        subject, body = notify.reminder_text({"title": "Tea", "date": "2026-12-05", "time": "2:00 PM", "location": "Library"}, "1d", "es")
        self.assertIn("Recordatorio", subject)
        self.assertIn("sábado 5 de diciembre", body)

    def test_chat_reminder_for_a_saved_event(self):
        with actions.connect() as db:
            event_id = db.execute("SELECT id FROM events WHERE title = 'Gaiety Hollow Garden Tour'").fetchone()[0]
        dispatcher = Dispatcher()
        actions.ActionSaveRsvp().run(dispatcher, Tracker(text="Save the Gaiety Hollow Garden Tour"), {})
        self.assertIn("saved Gaiety Hollow Garden Tour", dispatcher.messages[0]["text"])
        actions.ActionSetReminder().run(dispatcher, Tracker(text="Remind me 2 hours before", slots={"selected_event_id": str(event_id)}), {})
        self.assertIn("2 hours before", dispatcher.messages[-1]["text"])
        with actions.connect() as db:
            row = db.execute("SELECT * FROM reminders WHERE event_id = ?", (event_id,)).fetchone()
        self.assertEqual(row["timing"], "2h")

    def test_unclear_timing_asks_with_buttons(self):
        dispatcher = Dispatcher()
        actions.ActionSetReminder().run(dispatcher, Tracker(text="set a reminder"), {})
        self.assertEqual(len(dispatcher.messages[0]["buttons"]), 2)


class SpanishTests(TempDb):
    def test_language_switch_sets_the_slot(self):
        events = actions.ActionSetLanguage().run(Dispatcher(), Tracker(text='/set_language{"lang":"es"}', entities=[{"entity": "lang", "value": "es"}]), {})
        self.assertEqual(events[0]["value"], "es")

    def test_actions_answer_in_spanish(self):
        dispatcher = Dispatcher()
        actions.ActionSearchEvents().run(dispatcher, Tracker(slots={"language": "es"}, text="Quiero eventos de jardinería"), {})
        self.assertTrue(dispatcher.messages[0]["text"].startswith("Encontré"))
        first = dispatcher.messages[0]["json_message"]["events"][0]
        self.assertIn(first["source"], ("deepwood", "lordschryver", "daveinsalem"))

    def test_spanish_yes_and_skip(self):
        self.assertIs(actions.parse_yes_no("sí"), True)
        self.assertIs(actions.parse_yes_no("cancelar"), False)
        self.assertTrue(actions.is_skip("omitir"))

    def test_message_table_has_every_english_key_in_spanish(self):
        from actions.i18n import MESSAGES

        self.assertEqual(set(MESSAGES["en"]) - set(MESSAGES["es"]), set())
        self.assertIn("volvamos", t("es", "go_back_ok"))


if __name__ == "__main__":
    unittest.main()
