"""로그인 디버깅 스크립트"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import requests
from bs4 import BeautifulSoup
import base64

BASE_URL = 'https://gfauction.co.kr'
LOGIN_ID = '1111'
LOGIN_PW = '1111'

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
})

# 1. Fetch login page
print("=== Step 1: Fetch login page ===")
resp = session.get(f'{BASE_URL}/member/member01.php', timeout=15)
print(f"Status: {resp.status_code}")
print(f"Length: {len(resp.text)}")
print(f"Cookies: {dict(session.cookies)}")

# Parse login page
soup = BeautifulSoup(resp.text, 'html.parser')

# Find all forms
forms = soup.find_all('form')
print(f"\nForms found: {len(forms)}")
for i, form in enumerate(forms):
    action = form.get('action', '')
    method = form.get('method', '')
    print(f"  Form {i}: action={action}, method={method}")
    inputs = form.find_all('input')
    for inp in inputs:
        name = inp.get('name', '')
        typ = inp.get('type', '')
        val = inp.get('value', '')
        if val and len(val) > 50:
            val = val[:50] + '...'
        print(f"    input: name={name}, type={typ}, value={val}")

# Check for captcha
if 'captcha' in resp.text.lower() or 'recaptcha' in resp.text.lower():
    print("\n*** CAPTCHA detected! ***")
else:
    print("\nNo CAPTCHA detected")

# Check for script tags
scripts = soup.find_all('script')
print(f"\nScript tags: {len(scripts)}")
for s in scripts[:10]:
    src = s.get('src', '')
    if src:
        print(f"  script src: {src}")
    else:
        text = s.string or ''
        if len(text) > 0:
            print(f"  inline script ({len(text)} chars): {text[:300]}")

# 2. Try login
print("\n=== Step 2: Login attempt ===")
encoded_id = base64.b64encode(LOGIN_ID.encode('utf-8')).decode('utf-8')
encoded_pw = base64.b64encode(LOGIN_PW.encode('utf-8')).decode('utf-8')
print(f"Encoded ID: {encoded_id}")
print(f"Encoded PW: {encoded_pw}")

login_data = {
    'rtn_page': '',
    'id': encoded_id,
    'pwd': encoded_pw,
    'login_id': '',
    'login_pw': '',
}
print(f"POST data: {login_data}")

login_resp = session.post(
    f'{BASE_URL}/member/login_proc.php',
    data=login_data,
    timeout=15,
    headers={
        'Referer': f'{BASE_URL}/member/member01.php',
        'Origin': BASE_URL,
    },
    allow_redirects=False  # Don't follow redirects
)
print(f"\nLogin response status: {login_resp.status_code}")
print(f"Login response headers: {dict(login_resp.headers)}")
print(f"Login response cookies: {dict(session.cookies)}")
if login_resp.text:
    print(f"Login response body ({len(login_resp.text)} chars): {login_resp.text[:500]}")

# 3. Check if logged in
print("\n=== Step 3: Check login status ===")
check_resp = session.get(f'{BASE_URL}/main/main.php', timeout=15)
print(f"Main page status: {check_resp.status_code}")
print(f"Main page length: {len(check_resp.text)}")

if '로그아웃' in check_resp.text:
    print(">>> LOGIN SUCCESS! (로그아웃 found)")
elif '로그인' in check_resp.text:
    print(">>> LOGIN FAILED! (로그인 found, but not 로그아웃)")
else:
    print(">>> UNKNOWN STATUS")
    # Print some of the page content
    print(f"Page content preview: {check_resp.text[:1000]}")

# 4. Also try without base64 encoding
print("\n=== Step 4: Try without base64 ===")
session2 = requests.Session()
session2.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
})
session2.get(f'{BASE_URL}/member/member01.php', timeout=15)

login_data2 = {
    'rtn_page': '',
    'id': LOGIN_ID,
    'pwd': LOGIN_PW,
    'login_id': '',
    'login_pw': '',
}
login_resp2 = session2.post(
    f'{BASE_URL}/member/login_proc.php',
    data=login_data2,
    timeout=15,
    headers={
        'Referer': f'{BASE_URL}/member/member01.php',
        'Origin': BASE_URL,
    },
    allow_redirects=False
)
print(f"Login response (no base64): {login_resp2.status_code}")
print(f"Location: {login_resp2.headers.get('Location', 'none')}")
if login_resp2.text:
    print(f"Body: {login_resp2.text[:300]}")

check_resp2 = session2.get(f'{BASE_URL}/main/main.php', timeout=15)
if '로그아웃' in check_resp2.text:
    print(">>> LOGIN SUCCESS without base64!")
elif '로그인' in check_resp2.text:
    print(">>> LOGIN FAILED without base64")
else:
    print(">>> UNKNOWN STATUS without base64")