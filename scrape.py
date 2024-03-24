import json
import re
import sys

import requests
import pandas as pd
from bs4 import BeautifulSoup

facilities_master_dict = {}

with open('facilities.json', 'r') as f:
    facilities_data = json.load(f)


def parse_specialities(soup, pattern=''):
    specialities = []
    # Locate the section containing specialities based on the provided structure
    specialities_container = soup.find('div', {'id': 'full'})
    if specialities_container:
        ul = specialities_container.find('ul', class_='bullet')
        if ul:
            list_items = ul.find_all('li')
            # Check if pattern is provided and found in any of the list items
            if pattern and any(pattern.lower() in item.text.lower() for item in list_items):
                specialities = [li.text.strip() for li in list_items]
            # If pattern is blank, include all items
            elif not pattern:
                specialities = [li.text.strip() for li in list_items]
    # print(f"\tFound {len(specialities)}: [{', '.join(specialities)}]")
    return specialities


def parse_contact_info(soup, info_id):
    info_tag = soup.find('p', {'id': info_id})
    if info_tag:
        # If the contact info is wrapped in an <a> tag
        a_tag = info_tag.find('a')
        if a_tag:
            return a_tag.text.strip()
        return info_tag.text.strip()
    return ""


def parse_address(soup):
    address_label = soup.find('p', text='Full Address')
    if address_label:
        following_siblings = address_label.find_next_siblings('p', limit=2)
        if following_siblings:
            address = following_siblings[0].text.strip()
            # Check if there's an <a> tag with the address
            if len(following_siblings) > 1 and following_siblings[1].name == 'a':
                address = following_siblings[1].text.strip()
                # Clean up the address by removing newlines and unnecessary whitespace
                address = re.sub(r'\s+', ' ', address).strip()
            return address
    return ""


def scrape_facility_details(facility, pattern=''):
    url = f"https://services.dha.gov.ae/sheryan/wps/portal/home/medical-directory/facility-details?facilityId={facility['facilityId']}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Parse specialities
    facility['specialities'] = parse_specialities(soup, pattern)

    # Parse phone, email, and website
    facility['phone'] = parse_contact_info(soup, 'viewPhone')
    facility['email'] = parse_contact_info(soup, 'viewEmail')
    facility['website'] = parse_contact_info(soup, 'viewWebsite')

    # Parse address
    facility['address'] = parse_address(soup)

    return facility


def main(specialty_pattern=''):
    for facility in facilities_data:

        # Create a new dict with only the required fields
        facility_slim = {key: facility[key] for key in
                         ['facilityName', 'facilityCategory', 'facilityLocation', 'facilityId']}

        detailed_facility = scrape_facility_details(facility_slim, specialty_pattern)

        if specialty_pattern:
            # Include only those facilities with the specified specialization pattern
            if detailed_facility["specialities"]:
                facilities_master_dict[detailed_facility['facilityId']] = detailed_facility
        else:
            # Include everything
            facilities_master_dict[detailed_facility['facilityId']] = detailed_facility

    df = pd.DataFrame.from_dict(facilities_master_dict, orient='index')

    # If needed, specify the column order manually to ensure facilityId is first
    columns_order = ['facilityId', 'facilityName', 'facilityCategory', 'facilityLocation', 'specialities', 'phone',
                     'email', 'website', 'address']
    df['facilityId'] = df['facilityId'].astype(str)
    df = df.reindex(columns=columns_order)

    # Save the DataFrame to a CSV file
    df.to_csv('facilities_details.csv', index=False)


# Chance "psyc" to your pattern, or leave empty to get all
main("psyc")
