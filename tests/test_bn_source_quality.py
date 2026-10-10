"""Guard against incorrect public BN phone metadata and map camera points."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fetch_bailey_nelson_stores import australian_phone, map_coordinates, unlisted_prior_stores
from public_trading_status import infer_public_trading_status


class BaileySourceQualityTests(unittest.TestCase):
    def test_locator_omission_preserves_known_branch_and_actual_observation_date(self):
        prior = [{"id": "listed"}, {"id": "booking-only", "status": "Opening Soon", "fetched_at": "2026-10-04"}, {"id": "legacy", "status": "Unknown"}]
        rows = unlisted_prior_stores([{"id": "listed"}], prior, "2026-09-01")
        self.assertEqual(rows, [{"id": "booking-only", "status": "Opening Soon", "fetched_at": "2026-10-04"}, {"id": "legacy", "status": "Unknown", "fetched_at": "2026-09-01"}])
        self.assertNotIn("fetched_at", prior[-1])

    def test_explicit_branch_closed_heading_overrides_old_hours(self):
        self.assertEqual(infer_public_trading_status('<h1>Bailey Nelson Hornsby - Closed</h1>', {"openingHours": ["Mon 09:00-17:00"]}), "Closed")
        self.assertEqual(infer_public_trading_status('<h1>Branch</h1><p>Closed Sunday</p>'), "Unknown")

    def test_feature_point_wins_over_distant_camera(self):
        url = "https://www.google.com/maps/place/Example/@-31.84,115.71,12z/data=!3d-31.795504!4d115.7542008"
        with patch("fetch_bailey_nelson_stores.fetch_text", return_value=("", url)):
            self.assertEqual(map_coordinates("https://maps.app.goo.gl/example")[:2], (-31.795504, 115.7542008))

    def test_camera_alone_cannot_establish_premises_point(self):
        with patch("fetch_bailey_nelson_stores.fetch_text", return_value=("", "https://www.google.com/maps/@-31.84,115.71,12z")), patch("fetch_bailey_nelson_stores.time.sleep"):
            with self.assertRaises(RuntimeError):
                map_coordinates("https://maps.app.goo.gl/example")

    def test_malformed_phone_uses_complete_visible_number(self):
        page = '<a href="tel:+6161499473">(08) 6149 9473</a>'
        self.assertEqual(australian_phone(page, "+6161499473"), "(08) 6149 9473")
        self.assertEqual(australian_phone("", "+6161499473"), "")

    def test_ambiguous_contacts_are_not_guessed(self):
        page = '<a href="tel:0861499473">08 6149 9473</a><a href="tel:0861499472">08 6149 9472</a>'
        self.assertEqual(australian_phone(page, "+6161499473"), "")
        self.assertEqual(australian_phone(page, "+61861499473"), "+61861499473")


if __name__ == "__main__":
    unittest.main()
