import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from discover_healthpoint import parse_page


class HealthpointDiscoveryTests(unittest.TestCase):
    def test_multiple_branches_keep_separate_phones_and_detail_links(self):
        page = """<title>The Eye Place • Healthpoint</title>
        <div class="practitioner"><h3>Unrelated practitioner</h3><p itemprop="telephone">000</p></div>
        <div class="panel service-panel js-service-contact-panel"><section class="contact">
        <div class="service-location"><h3><a href="/eye-care/optometry/eye-place/at/waihi/" itemprop="name">2 School Lane, Waihi</a></h3>
        <p itemprop="telephone">(07) 863 7019</p><!-- <p itemprop="telephone">duplicate</p> --></div></section></div>
        <div class="panel service-panel js-service-contact-panel"><section class="contact">
        <div class="service-location"><h3><a href="/eye-care/optometry/eye-place/at/paeroa/" itemprop="name">2B Willoughby Street, Paeroa</a></h3>
        <p itemprop="telephone">(07) 862 8978</p></div></section></div>
        This page was last updated at 1:39PM on November 25, 2025."""
        row = parse_page(page, "https://www.healthpoint.co.nz/eye-care/optometry/eye-place/")
        self.assertEqual(row["premises_count"], 2)
        self.assertEqual(row["address"], "")
        self.assertEqual([r["phone"] for r in row["locations"]], ["(07) 863 7019", "(07) 862 8978"])
        self.assertTrue(row["locations"][1]["source_url"].endswith("/at/paeroa/"))
        self.assertTrue(all(not r["latitude"] for r in row["locations"]))
        self.assertEqual(row["source_updated"], "1:39PM on November 25, 2025")

    def test_selected_branch_point_does_not_leak_into_other_branches(self):
        page = """<title>Practice • Healthpoint</title>
        <div class="panel service-panel"><section class="contact"><div class="service-location">
        <h3>41 Queen Street, Warkworth</h3></div><p itemprop="telephone">09 425 9646</p>
        <section class="service-map"><meta itemprop="latitude" content="-36.39823" />
        <meta itemprop="longitude" content="174.66339" /></section>
        <h4>Street Address</h4><div itemprop="address"><p>41 Queen Street<br />Warkworth<br />Auckland 0910</p></div></section></div>
        <div class="panel service-panel js-service-contact-panel"><section class="contact">
        <div class="service-location"><h3><a href="/eye-care/optometry/practice/at/other/">Other branch</a></h3>
        <p itemprop="telephone">09 999 9999</p></div></section></div>"""
        row = parse_page(page, "https://www.healthpoint.co.nz/eye-care/optometry/practice/at/warkworth/")
        self.assertEqual(row["premises_count"], 2)
        first, second = row["locations"]
        self.assertEqual(first["address"], "41 Queen Street, Warkworth, Auckland 0910")
        self.assertEqual(first["latitude"], "-36.39823")
        self.assertEqual(second["latitude"], "")
        self.assertEqual(second["address_basis"], "location_heading")

    def test_single_premises_preserves_existing_scalar_fields(self):
        page = """<title>Clinic • Healthpoint</title><div class="panel service-panel"><section class="contact">
        <h3>Clinic location</h3><p itemprop="telephone">(09) 111 1111</p>
        <h4>Street Address</h4><div itemprop="address">1 Main Street<br />Auckland 0110</div>
        <meta itemprop="latitude" content="-35.1" /><meta itemprop="longitude" content="174.1" />
        </section></div>"""
        row = parse_page(page, "https://www.healthpoint.co.nz/eye-care/optometry/clinic/")
        self.assertEqual(row["premises_count"], 1)
        self.assertEqual(row["address"], "1 Main Street, Auckland 0110")
        self.assertEqual(row["locations"][0]["phone"], row["phone"])
        self.assertEqual(row["locations"][0]["longitude"], row["longitude"])

    def test_missing_contact_panels_do_not_create_practitioner_premises(self):
        page = '<title>Service • Healthpoint</title><h4><a itemprop="name">Dr Example</a></h4><p itemprop="telephone">09 123 1234</p>'
        row = parse_page(page, "https://www.healthpoint.co.nz/private/service/")
        self.assertEqual(row["premises_count"], 0)
        self.assertEqual(row["locations"], [])


if __name__ == "__main__":
    unittest.main()
