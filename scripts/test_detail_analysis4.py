"""올바른 팝업 URL(auction_detail_view.php) 테스트"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import requests
from bs4 import BeautifulSoup
import base64
import re

BASE_URL = 'https://gfauction.co.kr'
TEST_ID = '1447465'

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
print("로그인 성공")

# 올바른 URL로 각 팝업 테스트
popup_types = ['judgement', 'status', 'mun', 'mul', 'bu', 'song']
popup_names = {
    'judgement': '감정평가서',
    'status': '현황조사서',
    'mun': '문건접수내역',
    'mul': '매각물건명세서',
    'bu': '부동산의표시',
    'song': '송달내역',
}

for ptype in popup_types:
    print("\n" + "=" * 70)
    print(f"[{popup_names[ptype]}] type={ptype}")
    print("=" * 70)
    
    url = f'{BASE_URL}/search/auction_detail_view.php?type={ptype}&idx={TEST_ID}'
    r = session.get(url, timeout=15)
    print(f"  URL: {url}")
    print(f"  Status: {r.status_code}, Length: {len(r.text)}")
    
    if r.status_code == 200 and len(r.text) > 500:
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # PDF 찾기
        print("\n  --- PDF/다운로드 링크 ---")
        found_pdf = False
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            text = a.get_text(strip=True)
            if '.pdf' in href.lower() or 'download' in href.lower() or 'pdf' in href.lower():
                print(f"    텍스트: '{text}' href: {href}")
                found_pdf = True
        for embed in soup.find_all(['embed', 'object', 'iframe']):
            src = embed.get('src', '') or embed.get('data', '')
            if src:
                print(f"    embed src: {src}")
                found_pdf = True
        if not found_pdf:
            print("    PDF 링크 없음")
        
        # 이미지 찾기
        print("\n  --- 이미지 ---")
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and 'sample_img' not in src and 'logo' not in src:
                print(f"    {src}")
        
        # 테이블 구조
        print("\n  --- 테이블 구조 ---")
        tables = soup.find_all('table')
        print(f"    테이블 수: {len(tables)}")
        for ti, table in enumerate(tables):
            rows = table.find_all('tr')
            if len(rows) > 0:
                print(f"\n    테이블 {ti+1}: {len(rows)}행")
                # 헤더
                header_ths = [th.get_text(strip=True) for th in rows[0].find_all('th')]
                if header_ths:
                    print(f"    헤더: {header_ths}")
                # 처음 5행
                for ri, row in enumerate(rows[:6]):
                    cells = []
                    for cell in row.find_all(['td', 'th']):
                        txt = cell.get_text(strip=True)[:50]
                        cells.append(txt)
                    if cells:
                        print(f"    행{ri}: {cells}")
        
        # 텍스트 내용
        text = soup.get_text(separator='\n').strip()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        print(f"\n  --- 텍스트 ({len(lines)}줄) ---")
        for line in lines[:25]:
            print(f"    {line[:100]}")
        if len(lines) > 25:
            print(f"    ... (총 {len(lines)}줄)")
    else:
        print("  데이터 없음!")

# 또한 상세페이지 본문에 이미 포함된 데이터 확인
print("\n" + "=" * 70)
print("[상세페이지 본문에 이미 포함된 데이터]")
print("=" * 70)
detail_resp = session.get(f'{BASE_URL}/search/detail_view.php?idx={TEST_ID}', timeout=15)
detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')

# 감정평가서 현황 영역 (judDiv)
jud_div = detail_soup.find('div', id='judDiv')
if jud_div:
    text = jud_div.get_text(separator='\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    print(f"\n  judDiv (감정평가서): {len(lines)}줄")
    for line in lines[:30]:
        print(f"    {line[:100]}")

# 테이블 상세 분석
print("\n  --- 상세페이지 내 모든 tbl_dtb 테이블 ---")
for ti, table in enumerate(detail_soup.find_all('table', class_='tbl_dtb')):
    rows = table.find_all('tr')
    # 첫 행으로 용도 파악
    first_text = ' '.join([cell.get_text(strip=True) for cell in rows[0].find_all(['th', 'td'])])
    print(f"\n  테이블 {ti+1} ({len(rows)}행): {first_text[:80]}")
    for ri, row in enumerate(rows[:3]):
        cells = [cell.get_text(strip=True)[:40] for cell in row.find_all(['td', 'th'])]
        if cells:
            print(f"    행{ri}: {cells}")

print("\n\n완료!")