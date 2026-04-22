"""상세페이지 + 팝업 6종 HTML 구조 분석 (idx=1447471)"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import requests
from bs4 import BeautifulSoup
import base64
import re
import json

BASE_URL = 'https://gfauction.co.kr'
TEST_ID = '1447471'

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
})

# 1. 로그인
print("=" * 70)
print("[1] 로그인")
print("=" * 70)
session.get(f'{BASE_URL}/member/member01.php', timeout=15)
encoded_id = base64.b64encode(b'1111').decode('utf-8')
encoded_pw = base64.b64encode(b'1111').decode('utf-8')
resp = session.post(f'{BASE_URL}/member/login_proc.php', data={
    'rtn_page': '', 'id': encoded_id, 'pwd': encoded_pw, 'login_id': '', 'login_pw': '',
}, timeout=15, headers={
    'Referer': f'{BASE_URL}/member/member01.php', 'Origin': BASE_URL,
})
check = session.get(f'{BASE_URL}/main/main.php', timeout=15)
print(f"로그인: {'성공' if '로그아웃' in check.text else '실패'}")

# 2. 상세페이지 분석
print("\n" + "=" * 70)
print(f"[2] 상세페이지 (idx={TEST_ID})")
print("=" * 70)
detail_resp = session.get(f'{BASE_URL}/search/detail_view.php?idx={TEST_ID}', timeout=15)
print(f"Status: {detail_resp.status_code}, Length: {len(detail_resp.text)}")

soup = BeautifulSoup(detail_resp.text, 'html.parser')

# 이미지 URL 찾기
print("\n--- 물건 사진 (이미지 URL) ---")
photo_urls = []
for img in soup.find_all('img'):
    src = img.get('src', '')
    if src and ('pic_courtauction' in src or 'nuriauction' in src or 'upload' in src):
        if 'thumb' not in src and 'sample_img' not in src and 'logo' not in src and 'btn' not in src and 'icon' not in src:
            photo_urls.append(src)
            print(f"  {src}")

if not photo_urls:
    print("  위 조건으로 없음. 전체 img src:")
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src and 'sample_img' not in src:
            print(f"  {src}")

# PDF 링크 찾기
print("\n--- PDF 링크 ---")
pdf_links = []
for a in soup.find_all('a', href=True):
    href = a.get('href', '')
    if '.pdf' in href.lower():
        pdf_links.append(href)
        print(f"  텍스트: {a.get_text(strip=True)}, href: {href}")
    elif 'pdf' in a.get('onclick', '') or 'pdf' in href.lower():
        pdf_links.append(href)
        print(f"  [onclick/pdf] 텍스트: {a.get_text(strip=True)}, href: {href}")

# iframe 찾기
print("\n--- iframe ---")
for iframe in soup.find_all('iframe'):
    src = iframe.get('src', '')
    print(f"  iframe src: {src}")

# embed 찾기
print("\n--- embed/object ---")
for embed in soup.find_all(['embed', 'object']):
    src = embed.get('src', '') or embed.get('data', '')
    print(f"  {embed.name} src: {src}")

# pop_detail 관련 버튼/링크 찾기
print("\n--- pop_detail 호출 (버튼/링크) ---")
for elem in soup.find_all(['a', 'button', 'input', 'span', 'div']):
    onclick = elem.get('onclick', '') or ''
    href = elem.get('href', '') or ''
    if 'pop_detail' in onclick or 'pop_detail' in href:
        text = elem.get_text(strip=True)[:50]
        print(f"  텍스트: '{text}' | onclick: {onclick[:100]}")

# 3. 각 팝업 분석
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
    print(f"[3] 팝업: {popup_names[ptype]} (type={ptype})")
    print("=" * 70)
    
    popup_url = f'{BASE_URL}/search/pop_detail.php?idx={TEST_ID}&type={ptype}'
    p_resp = session.get(popup_url, timeout=15)
    print(f"Status: {p_resp.status_code}, Length: {len(p_resp.text)}")
    
    if p_resp.status_code == 200 and len(p_resp.text) > 100:
        p_soup = BeautifulSoup(p_resp.text, 'html.parser')
        
        # PDF 링크
        print("\n  --- PDF 링크 ---")
        found_pdf = False
        for a in p_soup.find_all('a', href=True):
            href = a.get('href', '')
            if '.pdf' in href.lower() or 'pdf' in href.lower():
                print(f"    텍스트: {a.get_text(strip=True)}, href: {href}")
                found_pdf = True
        for embed in p_soup.find_all(['embed', 'object', 'iframe']):
            src = embed.get('src', '') or embed.get('data', '')
            if src:
                print(f"    {embed.name} src: {src}")
                found_pdf = True
        if not found_pdf:
            print("    PDF 링크 없음")
        
        # 이미지
        print("\n  --- 이미지 ---")
        found_img = False
        for img in p_soup.find_all('img'):
            src = img.get('src', '')
            if src and 'sample_img' not in src:
                print(f"    src: {src}")
                found_img = True
        if not found_img:
            print("    이미지 없음")
        
        # 테이블 구조
        print("\n  --- 테이블 구조 ---")
        tables = p_soup.find_all('table')
        print(f"    테이블 수: {len(tables)}")
        for ti, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"\n    테이블 {ti+1}: {len(rows)}행")
            # 헤더
            header_row = rows[0] if rows else None
            if header_row:
                ths = [th.get_text(strip=True) for th in header_row.find_all('th')]
                if ths:
                    print(f"    헤더: {ths}")
            # 처음 3행 데이터
            for ri, row in enumerate(rows[:4]):
                tds = [td.get_text(strip=True)[:40] for td in row.find_all(['td', 'th'])]
                if tds:
                    print(f"    행{ri}: {tds}")
        
        # 텍스트 요약 (앞부분)
        text_content = p_soup.get_text(separator='\n').strip()
        lines = [l.strip() for l in text_content.split('\n') if l.strip()]
        print(f"\n  --- 텍스트 내용 (총 {len(lines)}줄, 처음 20줄) ---")
        for line in lines[:20]:
            print(f"    {line[:80]}")
    else:
        print("  팝업 데이터 없음")

print("\n" + "=" * 70)
print("[4] 상세페이지 전체 HTML에서 PDF/다운로드 관련 패턴")
print("=" * 70)
# PDF, download, file 관련 모든 패턴
for pattern in [r'\.pdf', r'pdf_', r'download', r'file_name', r'file_path', r'attach']:
    matches = re.findall(f'.{{0,50}}{pattern}.{{0,50}}', detail_resp.text, re.IGNORECASE)
    if matches:
        print(f"\n  패턴 '{pattern}' ({len(matches)}개):")
        for m in matches[:5]:
            print(f"    {m.strip()[:100]}")

# pop_detail 관련 전체 JavaScript
print("\n" + "=" * 70)
print("[5] JavaScript에서 pop_detail 관련 코드")
print("=" * 70)
for script in soup.find_all('script'):
    text = script.string or ''
    if 'pop_detail' in text:
        print(f"  {text[:500]}")

# 버튼 영역 (탭/버튼 텍스트)
print("\n" + "=" * 70)
print("[6] 버튼/탭 텍스트")
print("=" * 70)
for btn in soup.find_all(['a', 'button', 'span', 'div', 'input']):
    onclick = btn.get('onclick', '')
    text = btn.get_text(strip=True)
    if text and len(text) < 30 and ('pop' in onclick.lower() or 'detail' in onclick.lower() or 
                                      '감정' in text or '현황' in text or '매각' in text or 
                                      '부동산' in text or '송달' in text or '문건' in text or
                                      'pdf' in text.lower() or 'PDF' in text):
        print(f"  텍스트: '{text}' | onclick: {onclick[:80]}")

print("\n\n완료!")