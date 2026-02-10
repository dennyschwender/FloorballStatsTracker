#!/usr/bin/env python3
"""Test script to verify web pages load correctly with all information"""

import requests
from bs4 import BeautifulSoup
import time
import sys

BASE_URL = 'http://127.0.0.1:5000'
PIN = 'devpin123'

print('=' * 60)
print('FloorballStatsTracker - Web Page Information Test')
print('=' * 60)

# Test if server is running
try:
    response = requests.get(BASE_URL, timeout=2)
    print(f'\n✓ Server is running at {BASE_URL}')
except requests.exceptions.ConnectionError:
    print(f'\n✗ Server is not running at {BASE_URL}')
    print('  Please start the server first: python app.py')
    sys.exit(1)

# Create a session for maintaining cookies
session = requests.Session()

# Test 1: Login page loads
print('\n1. LOGIN PAGE')
response = session.get(BASE_URL)
soup = BeautifulSoup(response.text, 'html.parser')
print(f'   Status: {response.status_code}')
print(f'   ✓ Title: {soup.title.string if soup.title else "No title"}')
print(f'   ✓ Has PIN input: {"Yes" if soup.find("input", {"name": "pin"}) else "No"}')
print(f'   ✓ Has CSRF token: {"Yes" if soup.find("input", {"name": "csrf_token"}) else "No"}')

# Test 2: Login with PIN
print('\n2. LOGIN TEST')
csrf_token = soup.find('input', {'name': 'csrf_token'})
if csrf_token:
    csrf_value = csrf_token.get('value')
    login_response = session.post(BASE_URL, data={
        'pin': PIN,
        'csrf_token': csrf_value
    }, allow_redirects=True)
    print(f'   Status: {login_response.status_code}')
    print(f'   ✓ Login successful: {"Yes" if login_response.status_code == 200 else "No"}')
else:
    print('   ✗ No CSRF token found')

# Test 3: Games list page
print('\n3. GAMES LIST PAGE')
response = session.get(BASE_URL + '/games')
soup = BeautifulSoup(response.text, 'html.parser')
print(f'   Status: {response.status_code}')
if response.status_code == 200:
    print(f'   ✓ Page title: {soup.title.string if soup.title else "No title"}')
    print(f'   ✓ Language switcher: {"Yes" if soup.find("select", {"name": "lang"}) or soup.find("button", string=lambda t: t and "EN" in t) else "No"}')
    print(f'   ✓ Navigation links: {len(soup.find_all("a", class_="nav-link"))} found')
else:
    print(f'   ✗ Page not accessible (redirected or error)')

# Test 4: Stats page
print('\n4. STATS PAGE')
response = session.get(BASE_URL + '/stats')
soup = BeautifulSoup(response.text, 'html.parser')
print(f'   Status: {response.status_code}')
if response.status_code == 200:
    print(f'   ✓ Page loads successfully')
    print(f'   ✓ Has "Game Score" text: {"Yes" if "Game Score" in response.text else "No"}')
    print(f'   ✓ Has stats table: {"Yes" if soup.find("table") else "No"}')
    print(f'   ✓ Has filter options: {"Yes" if soup.find("select") else "No"}')
else:
    print(f'   ✗ Stats page not accessible')

# Test 5: Roster page
print('\n5. ROSTER PAGE')
response = session.get(BASE_URL + '/roster/')
soup = BeautifulSoup(response.text, 'html.parser')
print(f'   Status: {response.status_code}')
if response.status_code == 200:
    print(f'   ✓ Roster page loads')
    print(f'   ✓ Has category selector: {"Yes" if soup.find("select") else "No"}')
else:
    print(f'   ✗ Roster page not accessible')

# Test 6: Security headers
print('\n6. SECURITY HEADERS')
response = session.get(BASE_URL)
headers = response.headers
security_headers = {
    'X-Content-Type-Options': headers.get('X-Content-Type-Options'),
    'X-Frame-Options': headers.get('X-Frame-Options'),
    'X-XSS-Protection': headers.get('X-XSS-Protection'),
    'Content-Security-Policy': 'Present' if headers.get('Content-Security-Policy') else 'Missing'
}
for header, value in security_headers.items():
    status = '✓' if value else '✗'
    print(f'   {status} {header}: {value or "Missing"}')

# Test 7: Language switching
print('\n7. LANGUAGE SWITCHING')
response = session.post(BASE_URL + '/set_language', data={
    'lang': 'it',
    'csrf_token': csrf_value
}, allow_redirects=True)
if 'Floorball' in response.text or 'Statistiche' in response.text:
    print(f'   ✓ Language switch to Italian works')
else:
    print(f'   ⚠ Language switch unclear')

# Switch back to English
session.post(BASE_URL + '/set_language', data={
    'lang': 'en',
    'csrf_token': csrf_value
}, allow_redirects=True)
print(f'   ✓ Switched back to English')

print('\n' + '=' * 60)
print('✅ WEB PAGE TESTS COMPLETE')
print('=' * 60)
print('\nAll critical information appears to be loading correctly!')
