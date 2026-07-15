import tempfile
import unittest
from pathlib import Path

from scripts.lab import LabError, build_release_candidate, load_state, promote, save_state


SHA_A = "a" * 40
SHA_B = "b" * 40
NOW = "2030-01-01T10:00:00Z"


class LabTests(unittest.TestCase):
    def test_missing_file_has_empty_registry_and_environments(self):
        state = load_state(Path("missing-state.json"))
        self.assertEqual({}, state["releaseCandidates"])
        self.assertEqual({"test", "uat", "production"}, set(state["environments"]))

    def test_state_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = load_state(path)
            save_state(path, state)
            self.assertEqual(state, load_state(path))

    def test_release_candidate_is_deterministic_and_cannot_be_rebuilt(self):
        state = load_state(Path("missing-state.json"))
        manifest = build_release_candidate(state, SHA_A, NOW)
        self.assertRegex(manifest["digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual("rc-aaaaaaaaaaaa", manifest["tag"])
        with self.assertRaisesRegex(LabError, "already exists"):
            build_release_candidate(state, SHA_A, NOW)

    def test_promotion_requires_same_digest_in_preceding_environment(self):
        state = load_state(Path("missing-state.json"))
        first = build_release_candidate(state, SHA_A, NOW)
        second = build_release_candidate(state, SHA_B, NOW)
        promote(state, "test", first["digest"], SHA_A, "promote", NOW)

        with self.assertRaisesRegex(LabError, "TEST does not contain"):
            promote(state, "uat", second["digest"], SHA_B, "promote", NOW)

        promote(state, "uat", first["digest"], SHA_A, "promote", NOW)
        record = promote(state, "production", first["digest"], SHA_A, "promote", NOW)
        self.assertEqual(first["digest"], record["digest"])

    def test_rollback_requires_previously_deployed_digest(self):
        state = load_state(Path("missing-state.json"))
        first = build_release_candidate(state, SHA_A, NOW)
        second = build_release_candidate(state, SHA_B, NOW)
        promote(state, "test", first["digest"], SHA_A, "promote", NOW)

        with self.assertRaisesRegex(LabError, "not previously deployed"):
            promote(state, "test", second["digest"], SHA_B, "rollback", NOW)

        promote(state, "test", second["digest"], SHA_B, "promote", NOW)
        rollback = promote(state, "test", first["digest"], SHA_A, "rollback", NOW)
        self.assertEqual("rollback", rollback["operation"])


if __name__ == "__main__":
    unittest.main()
