import os
os.environ.setdefault("BLOOM_SAMPLE_EVENTS", "1")  # tests use the fixed sample listings
import tempfile
import unittest
from pathlib import Path

from actions import actions


class FakeTracker:
    sender_id = "unit-test-user"

    def __init__(self, slots=None):
        self.slots = slots or {}

    def get_slot(self, key):
        return self.slots.get(key)


class CommunityActionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        actions.DB_PATH = str(Path(self.temp_dir.name) / "community.sqlite3")
        actions.initialize_database()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_start_loads_labelled_sample_listings(self):
        from actions.sources import SAMPLES

        with actions.connect() as db:
            rows = db.execute("SELECT * FROM events").fetchall()
        self.assertEqual(len(rows), len(SAMPLES))
        self.assertTrue(all(r["is_sample"] == 1 and r["source_url"].startswith("https://") for r in rows))
        self.assertTrue(all(r["lat"] is not None and r["lon"] is not None for r in rows))
        sources = {r["source"] for r in rows}
        for key in ("center50", "deepwood", "lordschryver", "elsinore", "travelsalem", "salemart", "salemreporter", "daveinsalem"):
            self.assertIn(key, sources)

    def test_seed_includes_volunteering_and_a_french_conversation_group(self):
        with actions.connect() as db:
            titles = [r["title"] for r in db.execute("SELECT title FROM events WHERE tags LIKE '%volunteering%'")]
            french = db.execute("SELECT * FROM events WHERE title LIKE '%French Conversation%'").fetchone()
        self.assertGreaterEqual(len(titles), 3)
        self.assertIn("language", french["tags"])

    def test_rankings_keep_every_event_and_put_relevant_options_first(self):
        ranked = actions.rank_events({"interests": "reading books", "preferred_times": "morning"})
        with actions.connect() as db:
            self.assertEqual(len(ranked), db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        self.assertIn("books", actions.tag_keys(ranked[0]["tags"], ranked[0]["title"]))

    def test_gardening_profile_ranks_deepwood_and_lord_schryver_first(self):
        ranked = actions.rank_events({"interests": "gardening"})
        self.assertEqual({e["source"] for e in ranked[:5]}, {"deepwood", "lordschryver"})

    def test_center_50_is_weighted_for_everyone(self):
        ranked = actions.rank_events({})
        self.assertEqual(ranked[0]["source"], "center50")

    def test_asking_for_a_kind_of_event_orders_without_excluding(self):
        ranked = actions.rank_events({}, "Find card games on Tuesday afternoon")
        self.assertEqual(ranked[0]["title"], "Pinochle, Bridge & Card Games")

    def test_profile_is_saved_and_loaded_by_user_id(self):
        tracker = FakeTracker()
        profile = actions.save_profile(tracker, {"hobbies": "gardening", "interests": "birdwatching"})
        loaded = actions.profile_for(tracker.sender_id)
        self.assertEqual(loaded["hobbies"], "gardening")
        self.assertEqual(loaded["interests"], "birdwatching")
        self.assertEqual(profile["interests"], "birdwatching")


class DateTimeUnderstandingTests(unittest.TestCase):
    """Event dates/times arrive as free text from chat ("next Tuesday", "2pm")."""

    WEDNESDAY = __import__("datetime").date(2026, 11, 11)

    def test_relative_and_written_dates(self):
        d = lambda text: str(actions.parse_event_date(text, self.WEDNESDAY))
        self.assertEqual(d("today"), "2026-11-11")
        self.assertEqual(d("tomorrow"), "2026-11-12")
        self.assertEqual(d("Friday"), "2026-11-13")
        self.assertEqual(d("next week Tuesday"), "2026-11-17")
        self.assertEqual(d("November 20th"), "2026-11-20")
        self.assertEqual(d("the 3rd of December"), "2026-12-03")
        self.assertEqual(d("11/20"), "2026-11-20")
        self.assertEqual(d("in two weeks"), "2026-11-25")
        self.assertIsNone(actions.parse_event_date("sometime soon", self.WEDNESDAY))

    def test_spoken_and_typed_times(self):
        self.assertEqual(actions.parse_event_time("2pm"), "2:00 PM")
        self.assertEqual(actions.parse_event_time("10:30 in the morning"), "10:30 AM")
        self.assertEqual(actions.parse_event_time("noon"), "12:00 PM")
        self.assertEqual(actions.parse_event_time("14:00"), "2:00 PM")
        self.assertEqual(actions.parse_event_time("3"), "3:00 PM")
        self.assertIsNone(actions.parse_event_time("whenever"))

    def test_interest_tags_use_whole_words(self):
        self.assertEqual(actions.infer_interest_tags("Tea and Teens"), ["cooking", "family"])
        self.assertEqual(actions.infer_interest_tags("Salem Public Library Advisory Board Meeting"), [])



class EventTracker:
    """Just enough of rasa_sdk.Tracker for the event actions."""

    def __init__(self, slots, text="", sender_id="tester"):
        self.slots = dict(slots)
        self.latest_message = {"text": text}
        self.sender_id = sender_id

    def get_slot(self, name):
        return self.slots.get(name)


class FakeDispatcher:
    def __init__(self):
        self.messages = []

    def utter_message(self, text=None, **kwargs):
        self.messages.append({"text": text, **kwargs})


class EventPostingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        actions.DB_PATH = str(Path(self.temp_dir.name) / "community.sqlite3")
        actions.initialize_database()

    def tearDown(self):
        self.temp_dir.cleanup()

    def slots(self, **overrides):
        import datetime
        base = {
            "event_title": "Puzzle Afternoon", "event_date": (datetime.date.today() + datetime.timedelta(days=3)).isoformat(),
            "event_time": "2:00 PM", "event_location": "Salem Public Library", "event_host": "Jordan",
            "event_description": "Bring a puzzle and meet a neighbor.", "event_confirmation": "yes",
        }
        base.update(overrides)
        return base

    # Fix 2: yes/no is understood the same way every time
    def test_yes_variations_are_yes(self):
        for said in ["yes", "Yes!", "yeah", "sure", "yep", "yup", "ok", "Okay", "yes please", "sounds good",
                     "go ahead", "True", True, "post it", "that's right", "Yes, post it"]:
            self.assertIs(actions.parse_yes_no(said), True, said)

    def test_no_variations_are_no(self):
        for said in ["no", "No.", "nope", "nah", "no thanks", "not yet", "cancel", "False", False,
                     "don't post it", "wait", "yes but no"]:
            self.assertIs(actions.parse_yes_no(said), False, said)

    def test_unclear_answers_are_neither(self):
        for said in ["", "hmm", "what time was it again", None]:
            self.assertIsNone(actions.parse_yes_no(said), said)

    def test_confirmation_validator_uses_the_users_words(self):
        for said, expected in [("yeah", "yes"), ("sure", "yes"), ("yep", "yes"), ("nope", "no"), ("no", "no")]:
            tracker = EventTracker({"event_confirmation": "True"}, text=said)  # LLM guess ignored for clear words
            events = actions.ValidateEventConfirmation().run(FakeDispatcher(), tracker, {})
            self.assertEqual(events[0]["value"], expected, said)

    def test_validators_wait_until_the_question_is_answered(self):
        dispatcher = FakeDispatcher()
        self.assertEqual(actions.ValidateEventConfirmation().run(dispatcher, EventTracker({}, text="Jordan"), {}), [])
        self.assertEqual(actions.ValidateEventDescription().run(dispatcher, EventTracker({}, text="no"), {}), [])
        self.assertEqual(dispatcher.messages, [])

    def test_confirmation_validator_reasks_when_unclear(self):
        dispatcher = FakeDispatcher()
        events = actions.ValidateEventConfirmation().run(dispatcher, EventTracker({"event_confirmation": "maybe"}, text="hmm"), {})
        self.assertIsNone(events[0]["value"])
        self.assertIn("yes", dispatcher.messages[0]["text"])

    # Fix 3: a posted event is saved and then found by search
    def test_posted_event_is_saved_and_found_by_search(self):
        dispatcher = FakeDispatcher()
        actions.ActionSaveEvent().run(dispatcher, EventTracker(self.slots()), {})
        self.assertIn("is posted", dispatcher.messages[0]["text"])
        titles = [e["title"] for e in actions.rank_events({}, "puzzle")]
        self.assertEqual(titles[0], "Puzzle Afternoon")

    def test_no_answer_does_not_post(self):
        dispatcher = FakeDispatcher()
        actions.ActionSaveEvent().run(dispatcher, EventTracker(self.slots(event_confirmation="no")), {})
        self.assertIn("haven’t posted", dispatcher.messages[0]["text"])
        self.assertNotIn("Puzzle Afternoon", [e["title"] for e in actions.rank_events({}, "")])

    def test_website_guest_cannot_post_from_chat(self):
        dispatcher = FakeDispatcher()
        actions.ActionSaveEvent().run(dispatcher, EventTracker(self.slots(), sender_id="bloom-guest-123"), {})
        self.assertIn("create a free Bloom account", dispatcher.messages[0]["text"])
        self.assertNotIn("Puzzle Afternoon", [e["title"] for e in actions.rank_events({}, "")])

    def test_signed_in_account_can_post_from_chat(self):
        dispatcher = FakeDispatcher()
        actions.ActionSaveEvent().run(dispatcher, EventTracker(self.slots(), sender_id="acct-abc"), {})
        self.assertIn("Puzzle Afternoon", [e["title"] for e in actions.rank_events({}, "")])

    def test_failed_save_never_claims_success(self):
        original = actions.connect
        def broken():
            raise actions.sqlite3.OperationalError("disk I/O error")
        actions.connect = broken
        try:
            dispatcher = FakeDispatcher()
            actions.ActionSaveEvent().run(dispatcher, EventTracker(self.slots()), {})
        finally:
            actions.connect = original
        self.assertIn("was not posted", dispatcher.messages[0]["text"])
        self.assertNotIn("is posted", dispatcher.messages[0]["text"])

    # Fix 5: the description is optional
    def test_description_can_be_skipped(self):
        for said in ["skip", "no", "none", "Nope", "nothing", "no thanks"]:
            events = actions.ValidateEventDescription().run(FakeDispatcher(), EventTracker({"event_description": said}, text=said), {})
            self.assertEqual(events, [{"event": "slot", "timestamp": None, "name": "event_description", "value": "skip"}], said)
        dispatcher = FakeDispatcher()
        actions.ActionSaveEvent().run(dispatcher, EventTracker(self.slots(event_description="skip")), {})
        self.assertIn("is posted", dispatcher.messages[0]["text"])
        saved = [e for e in actions.rank_events({}, "puzzle") if e["title"] == "Puzzle Afternoon"][0]
        self.assertNotIn("skip", saved["description"].lower())

    def test_real_descriptions_are_kept(self):
        events = actions.ValidateEventDescription().run(
            FakeDispatcher(), EventTracker({"event_description": "No experience needed, all welcome"}, text="No experience needed, all welcome"), {})
        self.assertEqual(events, [])

    def test_skip_question_only_skips_the_description(self):
        dispatcher = FakeDispatcher()
        events = actions.ActionSkipQuestion().run(dispatcher, EventTracker(self.slots(event_description=None)), {})
        self.assertEqual(events[0]["value"], "skip")
        dispatcher = FakeDispatcher()
        events = actions.ActionSkipQuestion().run(dispatcher, EventTracker({"event_title": "Tea"}), {})
        self.assertEqual(events, [])
        self.assertIn("need this one", dispatcher.messages[0]["text"])


class OlderAdultRelevanceTests(unittest.TestCase):
    def test_kids_and_teen_programs_are_filtered_out(self):
        from actions.real_events import is_for_older_adults
        for title, cats in [("Preschool Storytime", "Storytime"), ("LEGO Party for Kids", "Activity"),
                            ("Study with Snacks for Teens", "Drop-In"), ("Infant/Toddler Storytime", ""),
                            ("Baby Prom", "Activity"), ("LIBRARY CLOSED", "Library Closures"),
                            ("Members Only Exhibit Preview", "")]:
            self.assertFalse(is_for_older_adults(title, cats), title)
        self.assertFalse(is_for_older_adults("Winter Craft", "", "A fun craft for ages 6-12."))

    def test_adult_programs_are_kept(self):
        from actions.real_events import is_for_older_adults
        for title in ["Medicare 101", "Brown Bag Book Club", "Adult Game Day", "Genealogy workshop: Discover your roots",
                      "Willamette Bearcats Football vs. Linfield University", "Magic at the Mill 2026"]:
            self.assertTrue(is_for_older_adults(title, "", "All ages welcome."), title)

    def test_ical_end_time_is_read(self):
        from actions.real_events import events_from_ical
        from datetime import date, timedelta
        day = (date.today() + timedelta(days=3)).strftime("%Y%m%d")
        raw = (f"BEGIN:VEVENT\nUID:1\nDTSTART:{day}T140000\nDTEND:{day}T153000\nSUMMARY:Medicare 101\n"
               "LOCATION:Main Library\nEND:VEVENT\n")
        rows = events_from_ical(raw, "library", "Salem Public Library", "")
        self.assertEqual((rows[0]["time"], rows[0]["end_time"]), ("2:00 PM", "3:30 PM"))


if __name__ == "__main__":
    unittest.main()
