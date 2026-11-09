import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from directory_category_crosswalk import supplement

class DirectoryCategoryCrosswalkTests(unittest.TestCase):
    def row(self,categories,role='Other business or service'):
        return dict(name='Opaque name',source_id='publisher-1',source_categories=categories,categories=[],category_basis='Original source',role=role)
    def apply(self,row):return supplement([dict(records=[row])])[0]['records'][0]
    def test_literal_publisher_category_adds_traceable_classification_without_mutating_source(self):
        row=self.row(['Jewellery']);before=copy.deepcopy(row);got=self.apply(row)
        self.assertEqual(got['categories'],['Fashion and accessories']);self.assertIn('crosswalk v1',got['category_basis']);self.assertEqual(row,before);self.assertEqual(got['source_categories'],row['source_categories'])
    def test_combined_labels_do_not_establish_individual_component_presence(self):
        got=self.apply(self.row(['Communication, Electronics & Games','Health And Beauty']))
        self.assertIn('Health and beauty (combined source category)',got['categories']);self.assertNotIn('Beauty',got['categories']);self.assertNotIn('Health and wellbeing',got['categories']);self.assertNotIn('Games and hobby retail',got['categories'])
    def test_unknown_and_marketing_labels_do_not_invent_activities_or_ownership(self):
        self.assertEqual(self.apply(self.row(['Shopping','Major Stores','Specialty','Private Member','']))['categories'],[])
    def test_case_whitespace_and_apostrophe_variants_are_equivalent(self):
        self.assertEqual(self.apply(self.row([" WOMEN’S FASHION "]))['categories'],['Fashion and accessories'])
    def test_optical_focal_store_does_not_manufacture_cotenant_category(self):
        self.assertEqual(self.apply(self.row(['Jewellery'],'Optical'))['categories'],[])
    def test_existing_attributed_categories_are_retained_and_application_is_idempotent(self):
        row=self.row(['Books']);row['categories']=['Gifts'];got=self.apply(row);self.assertEqual(got['categories'],['Books and stationery','Gifts']);self.assertEqual(self.apply(got),got)

if __name__=='__main__':unittest.main()
