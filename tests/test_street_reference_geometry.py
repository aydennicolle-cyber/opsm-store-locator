import unittest
from scripts.street_reference_geometry import nearest_named_road

XML = b'''<osm><node id="1" lat="-38.0" lon="145.0"/><node id="2" lat="-38.002" lon="145.0"/><way id="3" version="4"><nd ref="1"/><nd ref="2"/><tag k="name" v="Main Street"/><tag k="highway" v="residential"/></way></osm>'''

class StreetReferenceGeometryTests(unittest.TestCase):
    def test_projects_to_named_road_without_changing_latitude_along_segment(self):
        r = nearest_named_road(XML, 'Main Street', -38.001, 145.0004)
        self.assertEqual(r['status'], 'matched')
        self.assertAlmostEqual(r['latitude'], -38.001)
        self.assertAlmostEqual(r['longitude'], 145)
        self.assertEqual(r['node_ids'], ['1', '2'])
        self.assertGreater(r['displacement_m'], 30)

    def test_does_not_match_different_street_or_distant_namesake(self):
        self.assertEqual(nearest_named_road(XML, 'Main Road', -38.001, 145)['status'], 'unresolved')
        self.assertEqual(nearest_named_road(XML, 'Main Street', -38.001, 146)['status'], 'unresolved')

    def test_clamps_to_endpoint_and_excludes_named_building_geometry(self):
        r = nearest_named_road(XML, 'Main Street', -37.9999, 145)
        self.assertEqual(r['latitude'], -38)
        self.assertEqual(nearest_named_road(XML.replace(b'residential', b'footway'), 'Main Street', -38.001, 145)['status'], 'unresolved')

class RetainedStreetPointTests(unittest.TestCase):
    def test_reviewed_points_remain_on_their_evidenced_segments(self):
        import csv, json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        reviews = json.loads((root/'data/discovery/reviewed_street_reference_geometry.json').read_text())['reviews']
        with (root/'data/place_coordinate_overrides.csv').open() as source:
            overrides = {r['place_id']: r for r in csv.DictReader(source)}
        for r in reviews:
            with self.subTest(place=r['place_id']):
                a, b = r['segment']; t = r['fraction']
                self.assertTrue(0 <= t <= 1)
                self.assertAlmostEqual(r['longitude'], a[0]+t*(b[0]-a[0]))
                self.assertAlmostEqual(r['latitude'], a[1]+t*(b[1]-a[1]))
                self.assertEqual(float(overrides[r['place_id']]['latitude']), r['latitude'])
                self.assertEqual(float(overrides[r['place_id']]['longitude']), r['longitude'])
                self.assertEqual(overrides[r['place_id']]['evidence_url'], r['source_url'])
                self.assertEqual(len(r['node_ids']), 2)

class RoadGeometryCacheTests(unittest.TestCase):
    def test_review_annotations_cannot_change_subsequent_geometry_results(self):
        first = nearest_named_road(XML, 'Main Street', -38.001, 145.0004)
        first['node_ids'][0] = 'changed'
        first['segment'][0][0] = 0
        first['source_tags']['indoor'] = 'yes'
        second = nearest_named_road(XML, 'Main Street', -38.001, 145.0004)
        self.assertEqual(second['node_ids'], ['1', '2'])
        self.assertEqual(second['segment'][0][0], 145)

class NamedPedestrianReferenceTests(unittest.TestCase):
    def test_named_pedestrian_path_requires_explicit_review_opt_in(self):
        path = XML.replace(b'residential', b'footway')
        self.assertEqual(nearest_named_road(path, 'Main Street', -38.001, 145)['status'], 'unresolved')
        result = nearest_named_road(path, 'Main Street', -38.001, 145, allow_named_pedestrian_paths=True)
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['highway'], 'footway')

class IndoorStreetReferenceTests(unittest.TestCase):
    def test_named_indoor_passage_cannot_supply_street_marker(self):
        indoor = XML.replace(b'<tag k="highway"', b'<tag k="indoor" v="yes"/><tag k="highway"')
        self.assertEqual(nearest_named_road(indoor, 'Main Street', -38.001, 145, allow_named_pedestrian_paths=True)['status'], 'unresolved')
