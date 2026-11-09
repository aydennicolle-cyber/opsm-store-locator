"""Literal publisher-category translations, independent of brand or BN status.

Combined publisher labels remain one combined category. Vague labels stay unknown.
Existing separately attributed classifications are retained, not inferred here.
"""
import copy
import re
import unicodedata


def label_key(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', value).replace('’', "'").strip()).casefold()


GROUPS = {
    'Fashion and accessories': [
        'Jewellery', 'Jewellery Stores', 'Jewellery and watches', 'Apparel',
        'Clothing Stores', 'Womens Clothing Stores', 'Mens Clothing Stores',
        'Kids Clothing Stores', 'Shoe Stores', 'Womens Shoe Stores', 'Mens Shoe Stores',
        'Womens Fashion & Accessories', 'Mens Fashion & Accessories',
        'Childrens Fashion & Accessories', 'Womens Accessories', 'Mens Accessories',
        'Womens Footwear', 'Mens Footwear', 'Childrens Footwear', 'Sportswear',
        "Women's fashion", "Men's fashion", 'Footwear', 'Fashion Accessories',
    ],
    'Food and dining': ['Restaurants & Food Court', 'Dining & Takeaway', 'Takeaway', 'Cafes', 'Restaurants', 'Food and drink'],
    'Beauty': ['Hair & Beauty', 'Cosmetic Stores', 'Skincare', 'Haircare', 'Nail salons', 'Hairdressers and barbers', 'Waxing and laser', 'Makeup'],
    'Services': ['Travel', 'Financial services', 'Dry cleaning and alterations', 'Electronic repairs', 'Post office'],
    'Books and stationery': ['Newsagent & Stationery', 'Books', 'Stationery'],
    'Electronics and technology': ['Technology', 'Electronics Stores', 'Mobile phones', 'Electronics', 'Household appliances'],
    'Health and wellbeing': ['Chemists & Supplements', 'Medical', 'Gym and fitness', 'Physiotherapy', 'Health and wellness'],
    'Games and hobby retail': ['Toys & hobbies', 'Toys and games'],
    'Communication, electronics and games (combined source category)': ['Communication, Electronics & Games'],
    'Sport, fitness and outdoors (combined source category)': ['Sport, Fitness & Outdoors'],
    'Books, stationery and gifts (combined source category)': ['Gifts and stationery'],
    'Gifts, stationery and specialty (combined source category)': ['Gifts, Stationery & Speciality', 'Gifts, Stationery & Specialty'],
    'Gifts and flowers (combined source category)': ['Gifts & Flowers'],
    'Music, DVDs and books (combined source category)': ['Music, DVDs & Books'],
    'Liquor and tobacco (combined source category)': ['Liquor & Tobacco'],
    'Health and beauty (combined source category)': ['Health And Beauty'],
    'Gifts and homewares (combined source category)': ['Gifts And Homewares'],
    'Automotive goods and services (combined source category)': ['Car and auto'],
    'Luggage and travel accessories': ['Bags & Luggage'],
    'Outdoor and sports retail': ['Sports and adventure'],
}
CROSSWALK = {label_key(source): category for category, sources in GROUPS.items() for source in sources}


def supplement(captures):
    output = copy.deepcopy(captures)
    for capture in output:
        for row in capture['records']:
            if row.get('role') == 'Optical':
                continue
            translations = sorted({CROSSWALK[label_key(label)] for label in row.get('source_categories', []) if label_key(label) in CROSSWALK})
            added = set(translations) - set(row['categories'])
            if added:
                row['categories'] = sorted(set(row['categories']) | added)
                note = 'Literal publisher-category crosswalk v1; combined labels retained, no brand or ownership inference'
                row['category_basis'] = '; '.join(filter(None, [row.get('category_basis'), note]))
    return output
