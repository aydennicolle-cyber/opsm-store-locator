import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from embedded_business_maps import MapEvidenceError, resolve_operator_map
import fetch_additional_optical_networks as importer


CID = "0x6ad63df7673260b5:0x23e94f435791a189"
URL = "https://www.google.com/maps/embed?pb=!1m18!2d145.24945!3d-37.92827!1s" + CID
PROFILE = '<iframe src="' + URL + '"></iframe>'


def feature(identity=CID, point=None):
    row = [None] * 18
    row[0] = [identity, "EyeQ Rowville", point or [-37.9282774, 145.2520316]]
    row[1] = "EyeQ Rowville"
    row[13] = "Shop 9, 1100 Wellington Road, Rowville VIC 3178"
    return row


def response(*rows):
    return "initEmbed(" + json.dumps([[[[-37.0, 144.0]]], list(rows)]) + ");"


class EmbeddedBusinessMapsTests(unittest.TestCase):
    def resolve(self, page, profile=PROFILE):
        return resolve_operator_map(profile, lambda url: page)

    def test_uses_business_point_instead_of_viewport(self):
        result = self.resolve(response(feature()))
        self.assertEqual((result['latitude'], result['longitude']), (-37.9282774, 145.2520316))
        self.assertEqual(result['feature_id'], CID)

    def test_accepts_same_cid_with_zero_prefix_and_escaped_url(self):
        # HTML entities and URL-encoded identity are decoded independently.
        profile = PROFILE.replace(CID, "0x0%3A" + CID.split(':')[1]).replace('?pb=', '?hl=en&amp;pb=')
        result = self.resolve(response(feature()), profile)
        self.assertEqual(result['feature_id'], CID)

    def test_rejects_camera_only_even_with_data_lat_fallback(self):
        with self.assertRaises(MapEvidenceError):
            self.resolve(response(), PROFILE + '<div data-lat="-37.9" data-lon="145.2"></div>')

    def test_rejects_another_business_or_multiple_results(self):
        for rows in [(feature("0x1:0x2"),), (feature(), feature("0x1:0x2"))]:
            with self.subTest(rows=len(rows)), self.assertRaises(MapEvidenceError):
                self.resolve(response(*rows))

    def test_rejects_invalid_and_non_au_points(self):
        for point in [[145.2, -37.9], [float('nan'), 145.2], [True, 145.2], [-37.9], [-37.9, 'bad']]:
            with self.subTest(point=point), self.assertRaises(MapEvidenceError):
                self.resolve(response(feature(point=point)))

    def test_rejects_closed_or_unidentified_features(self):
        for field, value in [(17, 1), (1, ''), (13, '')]:
            f = feature(); f[field] = value
            with self.subTest(field=field), self.assertRaises(MapEvidenceError):
                self.resolve(response(f))

    def test_rejects_ambiguous_operator_maps_without_fetching(self):
        for profile in [PROFILE.replace(CID, 'unidentified'), PROFILE.replace('www.google.com', 'example.org'),
                        PROFILE + PROFILE.replace(CID, '0x1:0x2')]:
            with self.subTest(profile=profile), self.assertRaises(MapEvidenceError):
                resolve_operator_map(profile, lambda _: self.fail('Untrusted or ambiguous URL fetched'))

    def test_eyeq_importer_resolves_point_and_preserves_feed_on_failure(self):
        source = '<h4>Rowville</h4><h6>Search address</h6><h6>1100 Wellington Road, Rowville VIC 3178</h6><li>Fax: 03 9763 4000</li><li>Tel: <a href="tel:03 9763 4577">03 9763 4577</a></li><a href="https://www.eyeq.com.au/optometrist/rowville/">View Profile</a>'
        pages = {'https://www.eyeq.com.au/find-an-optometrist/': source,
                 'https://www.eyeq.com.au/optometrist/rowville/': PROFILE, URL: response(feature())}
        with patch.object(importer, 'fetch_text', side_effect=lambda url: pages[url]):
            _, rows = importer.eyeq()
        self.assertEqual(rows[0]['id'], 'rowville')
        self.assertEqual(rows[0]['longitude'], 145.2520316)
        self.assertEqual(rows[0]['phone'], '0397634577')
        with tempfile.TemporaryDirectory() as directory, patch.object(importer, 'ROOT', Path(directory)):
            importer.write_source('eyeq-optometrists', 'https://www.eyeq.com.au/find-an-optometrist/', rows, '2026-10-05')
            target = Path(directory) / 'retailers/eyeq-optometrists/stores.csv'
            original = target.read_bytes()
            snapshot = json.loads(target.with_name('source_snapshot.json').read_text())
            self.assertEqual(snapshot['coordinate_evidence'][0]['feature_id'], CID)
            pages[URL] = response()
            with patch.object(importer, 'fetch_text', side_effect=lambda url: pages[url]), self.assertRaises(MapEvidenceError):
                importer.eyeq()
            self.assertEqual(target.read_bytes(), original)


class LaubmanLocatorPaginationTests(unittest.TestCase):
    source = 'https://www.laubmanandpank.com.au/store-finder'

    @staticmethod
    def branch(key, name=None, longitude='138.49'):
        return (f'<tr><td class="views-field-title">{name or key}</td>'
                f'<td><div class="map_data" data-lat="-34.88" data-log="{longitude}"></div></td>'
                f'<td><a href="/store/{key}">STORE DETAILS</a></td></tr>')

    def profile(self, key):
        values = {'address-one': 'Shop 1, Test Shopping Centre', 'address-two': '1 Test Road',
                  'suburb': 'Adelaide', 'state': 'SA', 'postcode': '5000', 'phone': '0880000000'}
        return ''.join(f'<div class="field--name-field-{k}"><div class="field__item">{v}</div></div>'
                       for k, v in values.items())

    def test_complete_roster_and_advertised_page_provenance(self):
        pages = {self.source: self.branch('first') + '<a href="?page=1" rel="next">See More</a>',
                 self.source+'?page=1': self.branch('first') + self.branch('last')}
        pages.update({self.source.replace('/store-finder', '/store/'+k): self.profile(k)
                      for k in ('first', 'last')})
        with patch.object(importer, 'fetch_text', side_effect=lambda url: pages[url]):
            _, rows = importer.laubman_and_pank()
        self.assertEqual([r['id'] for r in rows], ['first', 'last'])
        self.assertEqual(rows[-1]['locator_page_url'], self.source+'?page=1')
        with tempfile.TemporaryDirectory() as directory, patch.object(importer, 'ROOT', Path(directory)):
            importer.write_source('laubman-and-pank', self.source, rows, '2026-10-08')
            snapshot = json.loads((Path(directory)/'retailers/laubman-and-pank/source_snapshot.json').read_text())
            self.assertEqual(snapshot['locator_pages'], [self.source, self.source+'?page=1'])

    def test_narrative_notice_is_preserved_separately_from_address(self):
        notice = ('If you are a customer of Eyecare Casino the store is temporarily closed and '
                  'you have been redirected to the nearest store, Laubman & Pank Lismore for '
                  'your eyecare and eyewear needs.')
        profile = self.profile('lismore').replace('Shop 1, Test Shopping Centre', notice)
        pages = {self.source: self.branch('lismore'),
                 self.source.replace('/store-finder', '/store/lismore'): profile}
        with patch.object(importer, 'fetch_text', side_effect=lambda url: pages[url]):
            _, rows = importer.laubman_and_pank()
        self.assertEqual(rows[0]['full_address'], '1 Test Road, Adelaide, SA, 5000')
        self.assertEqual(rows[0]['source_notices'], [notice])
        with tempfile.TemporaryDirectory() as directory, patch.object(importer, 'ROOT', Path(directory)):
            importer.write_source('laubman-and-pank', self.source, rows, '2026-10-08')
            snapshot = json.loads((Path(directory)/'retailers/laubman-and-pank/source_snapshot.json').read_text())
            self.assertEqual(snapshot['source_notices'][0]['notices'], [notice])
        pages[self.source.replace('/store-finder', '/store/lismore')] = profile.replace('1 Test Road', '')
        with patch.object(importer, 'fetch_text', side_effect=lambda url: pages[url]), self.assertRaises(RuntimeError):
            importer.laubman_and_pank()

    def test_rejects_partial_or_failed_second_page_before_returning_feed(self):
        initial = self.branch('first') + '<a rel="next" href="?page=1">More</a>'
        for failure in ['', '<a href="/store/unparsed">Branch</a>', OSError('network failed')]:
            def fetch(url):
                if url == self.source:
                    return initial
                if isinstance(failure, Exception):
                    raise failure
                return failure
            with self.subTest(failure=str(failure)), patch.object(importer, 'fetch_text', side_effect=fetch):
                with self.assertRaises((RuntimeError, OSError)):
                    importer.laubman_and_pank()

    def test_rejects_loop_conflict_and_untrusted_next_links(self):
        cases = [
            (self.branch('a')+'<a rel="next" href="?page=1">More</a>',
             self.branch('a')+'<a rel="next" href="?page=1">More</a>'),
            (self.branch('a')+'<a rel="next" href="?page=1">More</a>',
             self.branch('a', longitude='139.0')+self.branch('b')),
            (self.branch('a')+'<a rel="next" href="https://example.org/store-finder?page=1">More</a>', ''),
            (self.branch('a')+'<a rel="next" href="?page=1">More</a><a rel="next" href="?page=2">More</a>', '')]
        for first, second in cases:
            with self.subTest(first=first, second=second), patch.object(importer, 'fetch_text',
                    side_effect=lambda url: first if url == self.source else second):
                with self.assertRaises(RuntimeError):
                    importer.laubman_locator_rows(self.source)


if __name__ == '__main__':
    unittest.main()
