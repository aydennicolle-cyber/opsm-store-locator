"""Read branch-specific visible headings and hours, excluding menus and image filenames."""
import html
import re


def infer_public_trading_status(page, business=None):
    business=business or {}
    headings=' '.join(re.findall(r'<h[12]\b[^>]*>(.*?)</h[12]>',page,re.I|re.S))
    headings=html.unescape(re.sub(r'<[^>]+>',' ',headings))+' '+str(business.get('name',''))
    if re.search(r'temporar(?:ily|y)\s+clos',headings,re.I):return 'Temporarily Closed'
    if re.search(r'permanently\s+closed|store\s+(?:is\s+)?closed|\s[-–—:]\s*closed\s*$',headings,re.I):return 'Closed'
    if re.search(r'coming\s+soon|opening\s+(?:soon|in\s+\w+)',headings,re.I):return 'Opening Soon'
    if re.search(r'now\s+open',headings,re.I):return 'Active'
    if business.get('openingHours') or business.get('openingHoursSpecification'):return 'Active'
    hours=re.search(r'Opening\s+hours(.*?)(?:Services|Products|Footer|</main>)',page,re.I|re.S)
    if hours and re.search(r'\d\s*(?:am|pm)|\d{1,2}:\d{2}',hours.group(1),re.I):return 'Active'
    return 'Unknown'
