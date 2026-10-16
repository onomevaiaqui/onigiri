import json
import tempfile
import unittest
from pathlib import Path

from app.services import DestinationStore, normalize


class DestinationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.seed_path = root / "seed.json"
        self.seed_path.write_text(
            json.dumps(
                {
                    "home": "base",
                    "destinations": [
                        {"name": "base", "aliases": ["recepcao"]},
                        {"name": "escritorio", "aliases": ["escritório"]},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.store = DestinationStore(root / "panel.db", root / "destinations.json", self.seed_path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_normalizes_accents(self) -> None:
        self.assertEqual(normalize("  Escritório  "), "escritorio")

    def test_longest_matching_phrase_wins(self) -> None:
        self.store.save(
            {
                "name": "escritorio x",
                "aliases": ["escritório x"],
                "phrases": ["me leve ao escritório x"],
            }
        )
        result = self.store.interpret("Por favor, me leve ao escritório x")
        self.assertTrue(result["recognized"])
        self.assertEqual(result["destination"]["name"], "escritorio x")

    def test_exports_ros_compatible_file(self) -> None:
        exported = json.loads(self.store.export_path.read_text(encoding="utf-8"))
        self.assertEqual(exported["home"], "base")
        self.assertIn("destinations", exported)

    def test_simulation_never_moves_a_robot(self) -> None:
        result = self.store.simulate("me leve ao escritorio")
        self.assertTrue(result["recognized"])
        self.assertEqual(result["events"][2]["state"], "navegação simulada")
        self.assertIn("Nenhum motor", result["events"][2]["detail"])

    def test_backup_can_restore_and_preserves_home(self) -> None:
        original = self.store.backup()
        self.store.save({"name": "laboratorio", "aliases": [], "phrases": ["me leve ao laboratório"]})
        restored = self.store.restore(original)
        self.assertEqual([item["name"] for item in restored], ["base", "escritorio"])
        self.assertEqual(next(item for item in restored if item["is_home"])["name"], "base")

    def test_readiness_reports_ambiguous_phrase_and_missing_position(self) -> None:
        self.store.save({"name": "laboratorio", "aliases": ["escritorio"], "phrases": []})
        report = self.store.readiness()
        self.assertIn("laboratorio", report["without_map_position"])
        self.assertEqual(report["phrase_conflicts"][0]["phrase"], "escritorio")


if __name__ == "__main__":
    unittest.main()
