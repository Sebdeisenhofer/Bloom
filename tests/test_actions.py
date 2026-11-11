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

    def test_seed_contains_twenty_five_events(self):
        with actions.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        self.assertEqual(count, 25)

    def test_rankings_keep_every_event_and_put_relevant_options_first(self):
        ranked = actions.rank_events({"interests": "reading books", "preferred_times": "morning", "preferred_group_size": "small"})
        self.assertEqual(len(ranked), 25)
        self.assertEqual(ranked[0]["title"], "Salem Library Book Club")
        self.assertTrue(all(event["why"] for event in ranked))

    def test_day_time_and_location_are_ordering_filters_not_exclusions(self):
        ranked = actions.rank_events({}, "Find Saturday morning events near Riverfront Park")
        self.assertEqual(len(ranked), 25)
        self.assertEqual(ranked[0]["title"], "Riverfront Park Walking Group")

    def test_profile_is_saved_and_loaded_by_user_id(self):
        tracker = FakeTracker()
        profile = actions.save_profile(tracker, {"hobbies": "gardening", "interests": "birdwatching"})
        loaded = actions.profile_for(tracker.sender_id)
        self.assertEqual(loaded["hobbies"], "gardening")
        self.assertEqual(loaded["interests"], "birdwatching")
        self.assertEqual(profile["interests"], "birdwatching")

    def test_event_category_search_is_retained_as_an_interest(self):
        profile = {}
        actions.rank_events(profile, "Find book clubs near me")
        self.assertIn("book", profile["interests"])


if __name__ == "__main__":
    unittest.main()
