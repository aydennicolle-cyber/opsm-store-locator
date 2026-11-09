import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_centre_recognition import apply_retained_mapping_reviews
from unresolved_place_reviews import fingerprint

class RetainedMappingReviewTests(unittest.TestCase):
    def setUp(self):
        self.store = {'store_id':'s', 'name':'Example', 'full_address':'Shop 1, Accepted Centre', 'latitude':'-33', 'longitude':'151'}
        self.member = {'s':{'review_status':'Accepted','place_id':'accepted'}}
        self.row = {'store_id':'s','candidate_venue_id':'nearby','evidence':'Proximity only','review_status':'Pending'}
        self.review = {'store_id':'s','candidate_venue_id':'nearby','accepted_place_id':'accepted','store_fingerprint':fingerprint(self.store),'reviewed_at':'2026-10-27','evidence_url':'https://example.com/store','reason':'Written operator address confirms accepted place.'}

    def test_review_changes_queue_explanation_not_membership(self):
        before = copy.deepcopy(self.member)
        apply_retained_mapping_reviews([self.row],[self.store],self.member,[self.review])
        self.assertEqual(self.row['review_status'],'Reviewed; accepted place retained')
        self.assertIn('https://example.com/store',self.row['evidence'])
        self.assertEqual(self.member,before)

    def test_changed_address_membership_or_candidate_reopens_review(self):
        for change in ['address','membership','candidate']:
            with self.subTest(change=change):
                row,store,member = copy.deepcopy((self.row,self.store,self.member))
                if change=='address': store['full_address']='Different premises'
                elif change=='membership': member['s']['place_id']='different'
                else: row['candidate_venue_id']='different'
                apply_retained_mapping_reviews([row],[store],member,[self.review])
                self.assertEqual(row['review_status'],'Pending')

    def test_explicit_noncentre_setting_is_retained_without_inventing_a_place(self):
        self.member['s'].update(place_id='', location_setting='Other')
        self.review.update(accepted_place_id='', accepted_setting='Other')
        before = copy.deepcopy(self.member)
        apply_retained_mapping_reviews([self.row],[self.store],self.member,[self.review])
        self.assertEqual(self.row['review_status'],'Reviewed; accepted non-centre setting retained')
        self.assertEqual(self.member,before)

    def test_unresolved_or_changed_setting_cannot_reuse_noncentre_review(self):
        self.review.update(accepted_place_id='', accepted_setting='Other')
        for status, setting in [('Unresolved','Other'), ('Accepted','Uncertain'), ('Accepted','High Street')]:
            with self.subTest(status=status, setting=setting):
                row = copy.deepcopy(self.row)
                self.member['s'].update(place_id='', review_status=status, location_setting=setting)
                apply_retained_mapping_reviews([row],[self.store],self.member,[self.review])
                self.assertEqual(row['review_status'],'Pending')

    def test_blank_place_requires_explicit_noncentre_setting(self):
        self.review['accepted_place_id']=''
        with self.assertRaises(ValueError):
            apply_retained_mapping_reviews([self.row],[self.store],self.member,[self.review])
