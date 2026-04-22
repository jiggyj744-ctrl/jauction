"""상세페이지 HTML 깊이 분석 - 버튼/tab 구조, 팝업 URL 패턴"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import requests
from bs4 import BeautifulSoup
import base64
import re

BASE_URL = 'https://gfauction.co.kr'
TEST_ID = '1447471'

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
})

# 로그인
session.get(f'{BASE_URL}/member/member01.php', timeout=15)
encoded_id = base64.b64encode(b'1111').decode('utf-8')
encoded_pw = base64.b64encode(b'1111').decode('utf-8')
session.post(f'{BASE_URL}/member/login_proc.php', data={
    'rtn_page': '', 'id': encoded_id, 'pwd': encoded_pw, 'login_id': '', 'login_pw': '',
}, timeout=15, headers={
    'Referer': f'{BASE_URL}/member/member01.php', 'Origin': BASE_URL,
})

# 상세페이지
detail_resp = session.get(f'{BASE_URL}/search/detail_view.php?idx={TEST_ID}', timeout=15)
soup = BeautifulSoup(detail_resp.text, 'html.parser')

# 1. 감정평가서/현황조사서/매각물건명세서 등 버튼 주변 HTML 구조
print("=" * 70)
print("[1] 탭/버튼 주변 HTML 구조")
print("=" * 70)

keywords = ['감정평가서', '현황조사서', '매각물건명세서', '부동산의표시', '문건접수', '송달내역', '물건사진']

for kw in keywords:
    print(f"\n--- '{kw}' 버튼 ---")
    # Find all elements containing this text
    for elem in soup.find_all(string=re.compile(kw)):
        parent = elem.parent
        # Go up 3 levels
        for level in range(4):
            if parent:
                attrs = dict(parent.attrs) if hasattr(parent, 'attrs') else {}
                print(f"  Level {level}: <{parent.name}> {attrs}")
                # Show onclick
                if 'onclick' in attrs:
                    print(f"    onclick: {attrs['onclick']}")
                if 'href' in attrs:
                    print(f"    href: {attrs['href']}")
                if 'id' in attrs:
                    print(f"    id: {attrs['id']}")
                parent = parent.parent

# 2. 모든 JavaScript에서 함수 정의 찾기
print("\n" + "=" * 70)
print("[2] JavaScript - pop_detail, 탭 관련 함수")
print("=" * 70)
for script in soup.find_all('script'):
    text = script.string or ''
    if not text:
        continue
    # pop_detail 함수
    if 'pop_detail' in text or 'function' in text:
        print(f"\n  Script ({len(text)} chars):")
        # 줄 단위로 출력
        for line in text.split(';'):
            line = line.strip()
            if line and len(line) > 5:
                print(f"    {line[:150]}")

# 3. 전체 HTML에서 pop_detail 패턴
print("\n" + "=" * 70)
print("[3] HTML 전체에서 pop_detail 호출 패턴")
print("=" * 70)
pop_matches = re.findall(r"pop_detail\([^)]*\)", detail_resp.text)
for m in set(pop_matches):
    print(f"  {m}")

# 4. 탭 관련 ID/클래스 찾기
print("\n" + "=" * 70)
print("[4] 탭 관련 ID/클래스 (tab, tab_btn, toggle 등)")
print("=" * 70)
for elem in soup.find_all(['div', 'li', 'a', 'span', 'button']):
    elem_id = elem.get('id', '')
    elem_class = ' '.join(elem.get('class', []))
    if elem_id and ('tab' in elem_id.lower() or 'btn' in elem_id.lower() or 'pop' in elem_id.lower()):
        print(f"  id='{elem_id}' class='{elem_class}' text='{elem.get_text(strip=True)[:30]}'")
    if elem_class and ('tab' in elem_class.lower() or 'toggle' in elem_class.lower()):
        onclick = elem.get('onclick', '')
        print(f"  class='{elem_class}' onclick='{onclick[:80]}' text='{elem.get_text(strip=True)[:30]}'")

# 5. 다른 팝업 URL 패턴 시도
print("\n" + "=" * 70)
print("[5] 다른 팝업 URL 패턴 테스트")
print("=" * 70)

alt_urls = [
    f'{BASE_URL}/search/pop_detail.php?idx={TEST_ID}&type=judgement',
    f'{BASE_URL}/search/pop_detail.php?idx={TEST_ID}&type=judgement&mode=view',
    f'{BASE_URL}/search/pop_judgement.php?idx={TEST_ID}',
    f'{BASE_URL}/search/pop_status.php?idx={TEST_ID}',
    f'{BASE_URL}/search/pop_mul.php?idx={TEST_ID}',
    f'{BASE_URL}/search/pop_bu.php?idx={TEST_ID}',
    f'{BASE_URL}/search/pop_song.php?idx={TEST_ID}',
    f'{BASE_URL}/search/pop_mun.php?idx={TEST_ID}',
    f'{BASE_URL}/search/detail_view.php?idx={TEST_ID}&type=judgement',
]

for url in alt_urls:
    try:
        r = session.get(url, timeout=10)
        status = r.status_code
        length = len(r.text)
        print(f"  {status} ({length:>6}b) {url}")
    except Exception as e:
        print(f"  에러: {url} - {e}")

# 6. 더 최근 물건으로 테스트 (이 물건이 2021년이라 데이터 없을 수 있음)
print("\n" + "=" * 70)
print("[6] 최근 물건 찾기 (리스트 페이지)")
print("=" * 70)
list_resp = session.get(f'{BASE_URL}/search/search_list.php?aresult=all&rows=5&page=1', timeout=15)
list_soup = BeautifulSoup(list_resp.text, 'html.parser')
table = list_soup.find('table', class_='tbl_list')
if table:
    for tr in table.find_all('tr'):
        chk = tr.find('input', {'name': 'aChk'})
        if chk:
            iid = chk.get('value', '')
            onclick_td = tr.find('td', onclick=True)
            cn = ''
            for li in tr.find_all('li'):
                txt = li.get_text(strip=True)
                if re.match(r'\d{4}-\d+', txt):
                    cn = txt
                    break
            status_text = ''
            for li in tr.find_all('li'):
                txt = li.get_text(strip=True)
                if txt in ['진행중', '매각', '유찰', '취하', '기각', '정지', '미납']:
                    status_text = txt
                    break
            print(f"  ID={iid} 사건번호={cn} 상태={status_text}")

# 7. 상세페이지 HTML 일부 (탭 영역) 출력
print("\n" + "=" * 70)
print("[7] 상세페이지 HTML - 탭/버튼 영역")
print("=" * 70)
html_text = detail_resp.text

# '감정평가서' 주변 HTML 추출
for kw in ['감정평가서', '현황조사서', '매각물건명세서', '부동산의표시', '문건접수', '송달']:
    idx = html_text.find(kw)
    if idx >= 0:
        start = max(0, idx - 100)
        end = min(len(html_text), idx + 100)
        snippet = html_text[start:end].replace('\n', ' ').replace('\r', '')
        print(f"\n  [{kw}] 위치 {idx}:")
        print(f"    ...{snippet}...")

print("\n\n완료!")