"""pop_detail JS 함수 찾기 + 최근 진행중 물건으로 팝업 테스트"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import requests
from bs4 import BeautifulSoup
import base64
import re

BASE_URL = 'https://gfauction.co.kr'

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

# 1. JavaScript 파일에서 pop_detail 함수 찾기
print("=" * 70)
print("[1] JS 파일에서 pop_detail 함수 찾기")
print("=" * 70)

js_files = [
    '/js/main.js',
    '/js/tcommon.js',
    '/js/tsearch_form.js',
    '/js/java_base64.js',
]

for js_file in js_files:
    try:
        r = session.get(f'{BASE_URL}{js_file}', timeout=10)
        print(f"\n  {js_file}: status={r.status_code}, length={len(r.text)}")
        if r.status_code == 200:
            if 'pop_detail' in r.text:
                # Find the function
                lines = r.text.split('\n')
                for i, line in enumerate(lines):
                    if 'pop_detail' in line:
                        start = max(0, i-2)
                        end = min(len(lines), i+15)
                        print(f"  === Found pop_detail at line {i} ===")
                        for j in range(start, end):
                            print(f"    {j}: {lines[j].rstrip()[:120]}")
                        print()
            elif 'function' in r.text:
                # 모든 함수명 나열
                funcs = re.findall(r'function\s+(\w+)\s*\(', r.text)
                print(f"  함수 목록: {funcs[:20]}")
    except Exception as e:
        print(f"  에러: {e}")

# 2. 진행중인 최근 물건 찾기
print("\n" + "=" * 70)
print("[2] 진행중인 최근 물건 찾기")
print("=" * 70)

recent_id = None
for page in range(1, 5):
    list_resp = session.get(f'{BASE_URL}/search/search_list.php?aresult=all&rows=50&page={page}', timeout=15)
    list_soup = BeautifulSoup(list_resp.text, 'html.parser')
    table = list_soup.find('table', class_='tbl_list')
    if not table:
        break
    
    for tr in table.find_all('tr'):
        chk = tr.find('input', {'name': 'aChk'})
        if not chk:
            continue
        iid = chk.get('value', '')
        lis = tr.find_all('li')
        cn = ''
        status = ''
        for li in lis:
            txt = li.get_text(strip=True)
            if re.match(r'\d{4}-\d+', txt):
                cn = txt
            if txt in ['진행중', '매각', '유찰', '취하', '기각', '정지', '미납', '개시']:
                status = txt
        
        if '진행' in status:
            print(f"  진행중 발견: ID={iid} 사건번호={cn} 상태={status}")
            if not recent_id:
                recent_id = iid
                break
    if recent_id:
        break

if not recent_id:
    print("  진행중 물건 없음. 첫 번째 물건 사용.")
    # 첫 번째 물건 사용
    list_resp = session.get(f'{BASE_URL}/search/search_list.php?aresult=all&rows=1&page=1', timeout=15)
    list_soup = BeautifulSoup(list_resp.text, 'html.parser')
    table = list_soup.find('table', class_='tbl_list')
    if table:
        chk = table.find('input', {'name': 'aChk'})
        if chk:
            recent_id = chk.get('value', '')
            print(f"  사용: ID={recent_id}")

print(f"\n  테스트할 ID: {recent_id}")

# 3. 최근 물건으로 팝업 테스트
if recent_id:
    print("\n" + "=" * 70)
    print(f"[3] ID={recent_id} 팝업 테스트")
    print("=" * 70)
    
    # 상세페이지 먼저
    detail_resp = session.get(f'{BASE_URL}/search/detail_view.php?idx={recent_id}', timeout=15)
    print(f"  상세페이지: {detail_resp.status_code} ({len(detail_resp.text)}b)")
    
    # 팝업 URL 패턴들
    popup_types = ['judgement', 'status', 'mun', 'mul', 'bu', 'song']
    for ptype in popup_types:
        urls_to_try = [
            f'{BASE_URL}/search/pop_detail.php?idx={recent_id}&type={ptype}',
            f'{BASE_URL}/search/pop_detail.php?type={ptype}&idx={recent_id}',
        ]
        for url in urls_to_try:
            try:
                r = session.get(url, timeout=10)
                marker = '✅' if r.status_code == 200 and len(r.text) > 500 else '❌'
                print(f"  {marker} {r.status_code} ({len(r.text):>6}b) type={ptype}")
                if r.status_code == 200 and len(r.text) > 500:
                    # 처음 200자 출력
                    soup = BeautifulSoup(r.text, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                    print(f"      내용: {text[:200]}")
                break
            except:
                pass

    # 4. POST 방식 테스트
    print("\n" + "=" * 70)
    print(f"[4] POST 방식 팝업 테스트 (ID={recent_id})")
    print("=" * 70)
    
    for ptype in popup_types:
        try:
            r = session.post(f'{BASE_URL}/search/pop_detail.php', data={
                'idx': recent_id, 'type': ptype
            }, timeout=10)
            marker = '✅' if r.status_code == 200 and len(r.text) > 500 else '❌'
            print(f"  {marker} {r.status_code} ({len(r.text):>6}b) POST type={ptype}")
            if r.status_code == 200 and len(r.text) > 500:
                soup = BeautifulSoup(r.text, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                print(f"      내용: {text[:200]}")
        except Exception as e:
            print(f"  에러: {e}")

    # 5. AJAX/다른 엔드포인트 테스트
    print("\n" + "=" * 70)
    print(f"[5] 기타 엔드포인트 테스트")
    print("=" * 70)
    
    alt_endpoints = [
        f'/search/ajax_pop_detail.php?idx={recent_id}&type=judgement',
        f'/search/get_pop_detail.php?idx={recent_id}&type=judgement',
        f'/search/detail_data.php?idx={recent_id}&type=judgement',
        f'/search/pop_detail.html?idx={recent_id}&type=judgement',
        f'/search/detail_view.php?idx={recent_id}&popup=judgement',
        f'/search/pop.php?idx={recent_id}&type=judgement',
        f'/search/detail_pop.php?idx={recent_id}&type=judgement',
    ]
    
    for ep in alt_endpoints:
        try:
            r = session.get(f'{BASE_URL}{ep}', timeout=8)
            marker = '✅' if r.status_code == 200 and len(r.text) > 500 else '❌'
            if r.status_code == 200 and len(r.text) > 500:
                print(f"  {marker} {r.status_code} ({len(r.text):>6}b) {ep}")
                soup = BeautifulSoup(r.text, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                print(f"      내용: {text[:200]}")
        except:
            pass

print("\n\n완료!")