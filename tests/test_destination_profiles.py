import copy
import csv
import json
import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from scripts import destination_profiles as profiles
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from scripts import build_property_intelligence as property_build

DATA=Path(__file__).resolve().parents[1]/'data'


class DestinationProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads((DATA/'destination_profile_facts.json').read_text())['profiles']
        cls.places={p['place_id']:p for p in json.loads((DATA/'retail_places.json').read_text())['places']}
        cls.markets={f['properties']['sa2_code']:f['properties'] for f in json.loads((DATA/'sa2_market.geojson').read_text())['features']}

    def test_changed_point_or_ambiguous_area_cannot_reuse_demographics(self):
        f=copy.deepcopy(self.facts[0]);p=self.places[f['place_id']]
        f['demographic_boundary_evidence']['longitude']+=0.001
        with self.assertRaises(ValueError):profiles.validated_market(f,p,self.markets)
        f=copy.deepcopy(self.facts[0]);f['demographic_boundary_evidence']['match_count']=2
        with self.assertRaises(ValueError):profiles.validated_market(f,p,self.markets)

    def test_population_vintages_and_resident_scope_are_preserved(self):
        for f in self.facts:
            m=profiles.validated_market(f,self.places[f['place_id']],self.markets)
            self.assertIn('not a centre trade area',m['interpretation'])
            self.assertAlmostEqual(m['population_2025']-m['population_2021'],m['population_growth_2021_2025_number'])
            self.assertIn('2021',m['quality_note'])

    def test_radius_does_not_establish_street_membership(self):
        # Remove an evidenced mapping in an isolated fixture: this test must
        # remain valid when real research resolves the previously unknown shop.
        summaries=json.loads((DATA/'destination_research.json').read_text())['profiles']
        sid='independent-other-optical-reviewed-au-sunglass-hut-glenelg-b742'
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            for name in ['destination_profile_facts.json','retail_places.json','sa2_market.geojson',
                         'optical_stores.csv','store_certification.csv','destination_directory.json']:
                shutil.copy2(DATA/name,target/name)
            with (DATA/'store_place_memberships.csv').open(newline='') as stream:
                reader=csv.DictReader(stream); fields=reader.fieldnames
                rows=[r for r in reader if r['store_id']!=sid]
            with (target/'store_place_memberships.csv').open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader();writer.writerows(rows)
            saved=profiles.compile_profiles(target,summaries)
        street=next(p for p in saved if p['place_id'].startswith('corridor'))['optical_competition']
        accepted={s['store_id'] for s in street['accepted_current_members']}
        colley=next(s for s in street['nearby_current_non_bn'] if 'sunglass-hut-glenelg' in s['store_id'])
        self.assertNotIn(colley['store_id'],accepted)
        self.assertFalse(colley['accepted_destination_member'])
        self.assertLess(colley['distance_km'],2)

    def test_per_metric_source_does_not_relabel_visit_vintage(self):
        with (DATA/'property_portfolio_assets.csv').open(newline='') as f:
            row=next(r for r in csv.DictReader(f) if r['portfolio_asset_id']=='gpt-current-karrinyup')
        row['matched_place_id']=row['preferred_place_id']
        metrics=property_build.portfolio_metrics([row])[row['preferred_place_id']]
        self.assertEqual(metrics['gla_sqm'],109000)
        self.assertNotIn('tenancy_count',metrics)
        self.assertEqual(metrics['metric_evidence']['gla_sqm']['source_period'],'2025-10')
        self.assertEqual(metrics['metric_evidence']['gla_sqm']['source_date'],'')
        self.assertEqual(metrics['metric_evidence']['annual_visits']['source_date'],'2025-07-09')
        self.assertNotEqual(metrics['metric_evidence']['annual_visits']['source_url'],metrics['metric_evidence']['gla_sqm']['source_url'])

    def test_generated_profiles_match_current_public_inputs(self):
        summaries=json.loads((DATA/'destination_research.json').read_text())['profiles']
        saved=json.loads((DATA/'destination_profiles.json').read_text())['profiles']
        self.assertEqual(saved,profiles.compile_profiles(DATA,summaries))
        for p in saved:
            self.assertTrue(p['profile_status'].startswith('Partial'))
            self.assertTrue(p['limitations'])
            for fact in p['access']+p['property_facts']:
                self.assertTrue(fact['capture_sha256'])

    def test_new_store_without_certificate_is_excluded_until_health_rebuild(self):
        summaries=json.loads((DATA/'destination_research.json').read_text())['profiles']
        baseline=profiles.compile_profiles(DATA,summaries)
        member=next(s for p in baseline for s in p['optical_competition']['accepted_current_members'])
        sid=member['store_id']
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            for name in ['destination_profile_facts.json','retail_places.json','sa2_market.geojson',
                         'optical_stores.csv','store_place_memberships.csv','destination_directory.json']:
                shutil.copy2(DATA/name,target/name)
            with (DATA/'store_certification.csv').open(newline='') as stream:
                reader=csv.DictReader(stream); fields=reader.fieldnames; rows=list(reader)
            def write_certificates(records):
                with (target/'store_certification.csv').open('w',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(records)
            write_certificates([r for r in rows if r['store_id']!=sid])
            pending=profiles.compile_profiles(target,summaries)
            for profile in pending:
                competition=profile['optical_competition']
                self.assertNotIn(sid,{s['store_id'] for s in competition['accepted_current_members']})
                self.assertNotIn(sid,{s['store_id'] for s in competition['nearby_current_non_bn']})
            write_certificates(rows)
            self.assertEqual(profiles.compile_profiles(target,summaries),baseline)

    def test_edsquare_research_keeps_incompatible_measures_separate(self):
        with (DATA/'property_portfolio_assets.csv').open(newline='') as f:
            row=next(r for r in csv.DictReader(f) if r['portfolio_asset_id']=='jll-edsquare-researched')
        row['matched_place_id']=row['preferred_place_id']
        metrics=property_build.portfolio_metrics([row])[row['preferred_place_id']]
        self.assertEqual(metrics['gla_sqm'],24502)
        self.assertEqual(metrics['metric_evidence']['gla_sqm']['source_date'],'2026-04-01')
        for unsupported in ('annual_visits','tenancy_count','trade_area_population'):
            self.assertNotIn(unsupported,metrics)
        facts=next(p for p in self.facts if p['place_id']==row['preferred_place_id'])
        historical=next(f for f in facts['property_facts'] if f['label']=='Historical occupancy')
        self.assertIsNone(historical['source_date'])
        self.assertIn('FY2025',historical['source_period'])
        self.assertEqual(facts['census_context'][0]['source_period'],'2021')


if __name__=='__main__':unittest.main()
