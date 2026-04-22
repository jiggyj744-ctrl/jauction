"""
gfauction 경매 정보 웹사이트 일괄 생성기
- SEO 최적화 정적 HTML 생성
- 병렬 처리 (multiprocessing)
- sitemap.xml, RSS feed, robots.txt 생성
- CTA 컨설팅 배너 포함
- 전문가 분석 코멘트 자동 생성
"""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import sqlite3
import os
import json
import html
import re
from datetime import datetime
from multiprocessing import Pool, cpu_count
from collections import defaultdict
from expert_comment import generate_expert_comment


def format_long_text_readability(text):
    """
    스크래핑된 긴 법무 텍스트 가독성 개선: 날짜 정규화, 날짜 괄호, 번호 목록, 탭 구분 필드 등에 줄바꿈 삽입.
    """
    if text is None:
        return ''
    t = str(text).replace('\r\n', '\n').replace('\r', '\n').strip()
    if not t:
        return ''
    # 날짜 정규화: 끊어진 날짜 합치기 (예: "2003.\n11.\n22." → "2003.11.22.")
    t = re.sub(r'(\d{4})\.\s*\n\s*(\d{1,2})\.\s*\n\s*(\d{1,2})\.', r'\1.\2.\3.', t)
    # 탭으로 이어 붙인 항목(라벨\t내용) 분리
    if '\t' in t:
        t = re.sub(r'\t+', '\n', t)
    # [YYYY.MM.DD] 각 항목을 한 줄씩 (붙어 있는 타임라인)
    t = re.sub(r'(?<=[^\n\[])(\[\d{4}\.\d{2}\.\d{2}\])', r'\n\1', t)
    # '제출1.' 처럼 붙은 번호 목록 시작 분리
    t = re.sub(r'(제출)(?=\d+\.\s)', r'\1\n', t)
    # '. 2. ' '. 3. ' 형태의 번호 조항
    t = re.sub(r'(?<=[\.。．])\s+(?=(?:[1-9]|[1-9]\d)\.\s)', '\n', t)
    # 법원명 앞 줄바꿈 (예: "청주지방법원", "서울중앙지법" 등)
    # 단, 법원명 뒤에 바로 사건번호가 오는 경우는 줄바꿈하지 않음
    t = re.sub(r'(?<=[^\n])([가-힣]+(?:지방법원|지법|고등법원|고법|법원))(?!\s*\d{4}[가-힣])', r'\n\1', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()


def format_bid_price(price):
    """입찰가를 읽기 쉬운 형식으로 포맷 (예: 6525184000 → '6,525,184,000원')"""
    try:
        p = int(float(str(price).replace(',', '').strip()))
        if p == 0:
            return None  # 0이면 None 반환하여 건너뛰기
        return f'{p:,}원'
    except (ValueError, TypeError):
        return None


def format_related_cases_with_links(text):
    """관련사건 텍스트를 파싱하여 gfauction 바로가기 링크와 줄바꿈 적용"""
    if not text:
        return ''
    t = html.escape(format_long_text_readability(text))
    # 패턴: "법원명 사건번호" (예: "청주지방법원 2021타기203")
    # 사건번호에서 연도와 번호 추출하여 gfauction 링크 생성
    def make_link(m):
        court = m.group(1)
        case_num = m.group(2)
        # 사건번호에서 연도(숫자)와 타경/타기/가합 등 뒤의 번호 추출
        cn_match = re.match(r'(\d{4})(?:타경|타기|가합|가단|나단|다단|라단|마단|바단|사단|아단|자단|차단|카단|타단|파단|하단|기소|고소|형사|민사|소액|가소|나소|다소|라소|마소|바소|사소|아소|자소|차소|카소|타소|파소|하소|재심|항소|상고|파기환송|파기)(\d+)', case_num)
        if cn_match:
            sno = cn_match.group(1)
            tno = cn_match.group(2)
            url = f'https://gfauction.co.kr/search/search_list.php?aresult=all&sno={sno}&tno={tno}'
            return f'{court} <a href="{url}" target="_blank" rel="noopener" style="color:var(--primary);font-weight:600;">{case_num} 🔗</a>'
        return f'{court} {case_num}'
    t = re.sub(r'([가-힣]+(?:지방법원|지법|고등법원|고법|법원))\s+(\d{4}[가-힣]+\d+)', make_link, t)
    return t


def html_escape_formatted_long_text(text):
    return html.escape(format_long_text_readability(text))


def format_address_html(addr):
    """주소 표시 개선: 구) 앞 줄바꿈, 도로명+번호 띄어쓰기, 괄호 안 쉼표 띄어쓰기"""
    if not addr:
        return '-'
    a = addr
    # 도로명+번호 띄어쓰기 (예: 가야대로747번길 → 가야대로 747번길)
    a = re.sub(r'([가-힣])(\d+번길)', r'\1 \2', a)
    # 괄호 안 쉼표 뒤 띄어쓰기 (예: (부전동,라자오피스텔) → (부전동, 라자오피스텔))
    a = re.sub(r',([가-힣])', r', \1', a)
    # 구) 앞 줄바꿈: 신주소와 구주소 분리
    if ')구)' in a:
        parts = a.split(')구)', 1)
        return html.escape(parts[0] + ')') + '<br>' + html.escape('구)' + parts[1])
    return html.escape(a)


# ======================================
# 설정
# ======================================
from config import BASE_DIR, DB_PATH, SITE_NAME, SITE_URL, PHONE_NUMBER
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
DESCRIPTION = '전국 법원 경매 부동산 정보 - 아파트, 토지, 상업용 부동산 경매 물건 검색'

# 지역 매핑
REGION_MAP = {
    '서울': 'seoul', '경기': 'gyeonggi', '인천': 'incheon', '강원': 'gangwon',
    '충남': 'chungnam', '충북': 'chungbuk', '대전': 'daejeon', '세종': 'sejong',
    '부산': 'busan', '울산': 'ulsan', '대구': 'daegu', '경북': 'gyeongbuk',
    '경남': 'gyeongnam', '전남': 'jeonnam', '광주': 'gwangju', '전북': 'jeonbuk',
    '제주': 'jeju'
}

REGION_TITLE = {
    'seoul': '서울', 'gyeonggi': '경기도', 'incheon': '인천', 'gangwon': '강원도',
    'chungnam': '충남', 'chungbuk': '충북', 'daejeon': '대전', 'sejong': '세종',
    'busan': '부산', 'ulsan': '울산', 'daegu': '대구', 'gyeongbuk': '경북',
    'gyeongnam': '경남', 'jeonnam': '전남', 'gwangju': '광주', 'jeonbuk': '전북',
    'jeju': '제주도'
}

# 카테고리 매핑
CATEGORY_MAP = {
    '주거용 부동산': ('apartment', '주거용 부동산'),
    '토지': ('land', '토지'),
    '상업용 부동산': ('commercial', '상업용 부동산'),
    '기타': ('other', '기타 경매 물건'),
}

# ======================================
# 공통 HTML 템플릿
# ======================================
def get_head(title, description='', canonical='', additional_meta='', use_legacy_google_verification=True, css_path='style.css'):
    legacy_google = ''
    if use_legacy_google_verification:
        legacy_google = '<meta name="google-site-verification" content="VNMGQ8RFZK8mPlJU1cM00-lW4PwxPrA9ZAYGv_cEm_M" />\n'
    extra = additional_meta.strip()
    extra_block = (extra + '\n') if extra else ''
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="keywords" content="법원경매,부동산경매,경매물건,jauction,{html.escape(title)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:image" content="{SITE_URL}/images/kakao_img.png">
<link rel="canonical" href="{canonical}">
<link rel="stylesheet" href="{css_path}">
<meta name="NaverBot" content="All"/>
<meta name="NaverBot" content="index,follow"/>
<meta name="Yeti" content="All"/>
<meta name="Yeti" content="index,follow"/>
{extra_block}{legacy_google}</head>'''

def get_header(current='', show_search=False, base_path='./'):
    nav_items = [
        (base_path, '홈'),
        (f'{base_path}apartment/', '아파트/주거'),
        (f'{base_path}land/', '토지'),
        (f'{base_path}commercial/', '상업용'),
        (f'{base_path}region/', '지역별'),
        (f'{base_path}faq/', 'FAQ'),
    ]
    nav_html = '\n'.join(
        f'<a href="{url}" class="nav-link{" active" if current == url else ""}">{label}</a>'
        for url, label in nav_items
    )
    search_html = ''
    if show_search:
        search_html = '''<div class="header-search">
<form action="/" method="get" style="display:flex;gap:4px">
<input type="text" name="q" placeholder="사건번호, 주소 검색..." style="padding:6px 12px;border:1px solid var(--gray-300);border-radius:20px;font-size:0.85em;outline:none;width:180px">
<button type="submit" style="padding:6px 12px;background:var(--primary);color:#fff;border:none;border-radius:20px;font-size:0.85em;cursor:pointer">🔍</button>
</form>
</div>'''
    return f'''<header class="site-header">
<div class="container">
<a href="{base_path}" class="logo">🏷️ {SITE_NAME}</a>
{search_html}
<a href="tel:{PHONE_NUMBER}" class="header-phone">
<span class="header-phone-icon">📞</span>
{PHONE_NUMBER}
</a>
<nav class="nav">{nav_html}</nav>
</div>
</header>'''

def get_footer(base_path='./'):
    return f'''<footer class="site-footer">
<div class="container">
<div class="footer-links">
<a href="{base_path}guide/">경매가이드</a>
<a href="{base_path}dictionary/">용어사전</a>
<a href="{base_path}about/">사이트 소개</a>
<a href="{base_path}privacy/">개인정보처리방침</a>
<a href="{base_path}terms/">이용약관</a>
<a href="{base_path}faq/">자주묻는질문</a>
<a href="{base_path}feed.xml">RSS</a>
</div>
<p class="footer-copy">© {datetime.now().year} {SITE_NAME}. 본 사이트는 참고용이며, 실제 경매 정보는 해당 법원에서 확인하세요.</p>
<p class="footer-copy" style="margin-top:6px;font-size:0.8em;">최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
</footer>'''

# ======================================
# style.css
# ======================================
def generate_css():
    return f'''/* {SITE_NAME} 공통 스타일 v2 - 모바일 최적화 + CTA */
:root {{
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --primary-light: #dbeafe;
    --success: #16a34a;
    --warning: #f59e0b;
    --danger: #dc2626;
    --cta-orange: #ff6d00;
    --cta-orange-dark: #e65100;
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-400: #9ca3af;
    --gray-500: #6b7280;
    --gray-600: #4b5563;
    --gray-700: #374151;
    --gray-800: #1f2937;
    --gray-900: #111827;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
    --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1);
    --radius: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
    color: var(--gray-800);
    background: var(--gray-50);
    line-height: 1.7;
    font-size: 16px;
    -webkit-font-smoothing: antialiased;
}}

a {{ color: var(--primary); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

.container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}

/* ==================== HEADER ==================== */
.site-header {{
    background: #fff;
    border-bottom: 1px solid var(--gray-200);
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: var(--shadow-sm);
}}
.site-header .container {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
    gap: 16px;
}}
.logo {{
    font-size: 1.4em;
    font-weight: 800;
    color: var(--primary);
    text-decoration: none;
    white-space: nowrap;
    letter-spacing: -0.02em;
}}
.logo:hover {{ text-decoration: none; }}

.nav {{ display: flex; gap: 4px; align-items: center; }}
.nav-link {{
    padding: 8px 14px;
    border-radius: 8px;
    text-decoration: none;
    color: var(--gray-600);
    font-size: 0.9em;
    font-weight: 500;
    transition: all 0.15s;
    white-space: nowrap;
}}
.nav-link:hover {{ background: var(--gray-100); color: var(--gray-900); text-decoration: none; }}
.nav-link.active {{ background: var(--primary); color: #fff; }}
.nav-link.active:hover {{ background: var(--primary-dark); }}

/* Header CTA */
.header-cta {{
    display: flex;
    align-items: center;
    gap: 12px;
}}
.header-phone {{
    display: flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
    color: var(--cta-orange);
    font-weight: 700;
    font-size: 1.1em;
    transition: color 0.2s;
}}
.header-phone:hover {{ color: var(--cta-orange-dark); text-decoration: none; }}
.header-phone-icon {{
    background: var(--cta-orange);
    color: #fff;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1em;
}}
.header-cta-btn {{
    background: var(--cta-orange);
    color: #fff;
    padding: 8px 16px;
    border-radius: 20px;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.9em;
    transition: background 0.2s;
}}
.header-cta-btn:hover {{ background: var(--cta-orange-dark); text-decoration: none; }}

/* ==================== HERO ==================== */
.hero {{
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%);
    color: #fff;
    padding: 56px 0;
    text-align: center;
}}
.hero h1 {{ font-size: 2.2em; margin-bottom: 12px; font-weight: 800; letter-spacing: -0.03em; }}
.hero p {{ opacity: 0.9; font-size: 1.15em; font-weight: 400; }}

/* Stats */
.stats-bar {{
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
    margin: 32px 0 8px;
}}
.stat-card {{
    background: rgba(255,255,255,0.15);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: var(--radius-lg);
    padding: 20px 28px;
    text-align: center;
    min-width: 130px;
}}
.stat-card .num {{ font-size: 2em; font-weight: 800; line-height: 1.2; }}
.stat-card .label {{ font-size: 0.85em; opacity: 0.85; margin-top: 4px; }}

/* ==================== SEARCH ==================== */
.search-section {{ background: #fff; padding: 28px 0; border-bottom: 1px solid var(--gray-200); }}
.search-box {{
    display: flex;
    gap: 12px;
    max-width: 640px;
    margin: 0 auto;
}}
.search-box input {{
    flex: 1;
    padding: 14px 20px;
    border: 2px solid var(--gray-300);
    border-radius: var(--radius-lg);
    font-size: 1.05em;
    outline: none;
    transition: all 0.2s;
    background: var(--gray-50);
}}
.search-box input:focus {{ border-color: var(--primary); background: #fff; box-shadow: 0 0 0 3px var(--primary-light); }}
.search-box button {{
    padding: 14px 28px;
    background: var(--primary);
    color: #fff;
    border: none;
    border-radius: var(--radius-lg);
    font-size: 1.05em;
    cursor: pointer;
    font-weight: 700;
    transition: background 0.15s;
}}
.search-box button:hover {{ background: var(--primary-dark); }}

/* Filters */
.filters {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 16px;
}}
.filter-btn {{
    padding: 8px 18px;
    border: 1px solid var(--gray-300);
    border-radius: 24px;
    background: #fff;
    cursor: pointer;
    font-size: 0.9em;
    font-weight: 500;
    transition: all 0.15s;
    text-decoration: none;
    color: var(--gray-600);
}}
.filter-btn:hover {{ border-color: var(--primary); color: var(--primary); text-decoration: none; }}
.filter-btn.active {{ background: var(--primary); color: #fff; border-color: var(--primary); }}

/* ==================== ITEM GRID ==================== */
.item-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 20px;
    padding: 32px 0;
}}
.item-card {{
    background: #fff;
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow);
    overflow: hidden;
    transition: all 0.2s;
    text-decoration: none;
    color: inherit;
    display: block;
    border: 1px solid var(--gray-200);
}}
.item-card:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-lg); border-color: var(--primary-light); text-decoration: none; }}
.item-card .card-body {{ padding: 4px 20px 16px; }}
.item-card .address {{ font-size: 0.9em; color: var(--gray-600); margin-bottom: 12px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 2.7em; }}
.item-card .card-header {{
    padding: 20px 20px 12px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}}
.item-card .case-num {{ font-weight: 700; font-size: 1.05em; color: var(--primary); }}
.item-card .category-badge {{
    font-size: 0.75em;
    padding: 4px 12px;
    border-radius: 12px;
    font-weight: 600;
}}
.badge-residential {{ background: #dbeafe; color: #1d4ed8; }}
.badge-land {{ background: #dcfce7; color: #15803d; }}
.badge-commercial {{ background: #fef3c7; color: #92400e; }}
.badge-other {{ background: var(--gray-100); color: var(--gray-600); }}
.item-card .price-row {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
}}
.price-item {{ text-align: center; flex: 1; }}
.price-item .price-label {{ font-size: 0.75em; color: var(--gray-400); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }}
.price-item .price-value {{ font-weight: 700; font-size: 1em; }}
.price-value.accent {{ color: var(--danger); font-size: 1.15em; }}
.item-card .card-footer {{
    padding: 12px 20px;
    background: var(--gray-50);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.85em;
    color: var(--gray-500);
    border-top: 1px solid var(--gray-100);
}}
.status-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.8em;
    font-weight: 600;
}}
.status-proceeding {{ background: #dbeafe; color: #1d4ed8; }}
.status-bid {{ background: #dcfce7; color: #15803d; }}
.status-stop {{ background: #fef3c7; color: #92400e; }}
.status-cancel {{ background: #fee2e2; color: #991b1b; }}

/* ==================== PAGINATION ==================== */
.pagination {{
    display: flex;
    gap: 6px;
    justify-content: center;
    padding: 32px 0;
}}
.pagination a, .pagination span {{
    padding: 10px 16px;
    border: 1px solid var(--gray-300);
    border-radius: var(--radius);
    text-decoration: none;
    color: var(--gray-600);
    font-size: 0.9em;
    font-weight: 500;
    transition: all 0.15s;
}}
.pagination a:hover {{ border-color: var(--primary); color: var(--primary); text-decoration: none; }}
.pagination .active {{ background: var(--primary); color: #fff; border-color: var(--primary); }}

/* ==================== DETAIL PAGE ==================== */
.detail-container {{ max-width: 900px; margin: 0 auto; padding: 32px 24px; }}
.breadcrumb {{ font-size: 0.9em; color: var(--gray-400); margin-bottom: 20px; }}
.breadcrumb a {{ color: var(--primary); text-decoration: none; font-weight: 500; }}
.breadcrumb a:hover {{ text-decoration: underline; }}

.detail-card {{
    background: #fff;
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow);
    padding: 28px 32px;
    margin-bottom: 20px;
    border: 1px solid var(--gray-200);
}}
.detail-card h2 {{
    font-size: 1.4em;
    font-weight: 700;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--gray-100);
    color: var(--gray-800);
}}
.detail-table {{ width: 100%; border-collapse: collapse; }}
.detail-table th, .detail-table td {{
    padding: 14px 16px;
    text-align: left;
    border-bottom: 1px solid var(--gray-100);
    vertical-align: top;
}}
.detail-table th {{
    width: 150px;
    color: var(--gray-500);
    font-weight: 600;
    font-size: 0.88em;
    white-space: nowrap;
}}
.detail-table td {{ font-size: 0.98em; color: var(--gray-800); line-height: 1.6; }}
.detail-table tr:last-child th, .detail-table tr:last-child td {{ border-bottom: none; }}
.detail-table tr:hover {{ background: var(--gray-50); }}

.price-highlight {{ font-size: 1.25em; font-weight: 800; color: var(--danger); }}

/* Price Summary Cards */
.price-summary {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 20px;
}}
.price-card {{
    background: #fff;
    border-radius: var(--radius-lg);
    padding: 24px;
    text-align: center;
    border: 1px solid var(--gray-200);
    box-shadow: var(--shadow-sm);
}}
.price-card .pc-label {{ font-size: 0.82em; color: var(--gray-400); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }}
.price-card .pc-value {{ font-size: 1.6em; font-weight: 800; }}
.price-card.pc-appraisal .pc-value {{ color: var(--gray-800); }}
.price-card.pc-min .pc-value {{ color: var(--danger); }}
.price-card.pc-rate .pc-value {{ color: var(--primary); }}
.price-card .pc-sub {{ font-size: 0.8em; color: var(--gray-400); margin-top: 4px; }}

/* Detail Navigation */
.detail-nav {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    gap: 8px;
}}
.detail-nav a {{
    padding: 10px 20px;
    border-radius: var(--radius);
    text-decoration: none;
    font-size: 0.9em;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    border: 1px solid var(--gray-300);
    background: #fff;
    color: var(--gray-600);
}}
.detail-nav a:hover {{ background: var(--primary); color: #fff; border-color: var(--primary); text-decoration: none; }}

/* Header Search */
.header-search {{ display: flex; gap: 4px; align-items: center; }}
.header-search input {{
    padding: 8px 14px;
    border: 1px solid var(--gray-300);
    border-radius: 20px;
    font-size: 0.88em;
    outline: none;
    width: 200px;
    transition: all 0.2s;
}}
.header-search input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-light); }}
.header-search button {{
    padding: 8px 14px;
    background: var(--primary);
    color: #fff;
    border: none;
    border-radius: 20px;
    font-size: 0.88em;
    cursor: pointer;
}}

/* ==================== CTA BANNERS ==================== */
/* 상세 페이지 하단 CTA 배너 */
.detail-cta-banner {{
    background: linear-gradient(135deg, #1a73e8, #4285f4);
    border-radius: var(--radius-lg);
    padding: 28px 24px;
    margin: 24px 0;
    color: #fff;
    text-align: center;
    position: relative;
    overflow: hidden;
}}
.detail-cta-banner::before {{
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 200px;
    height: 200px;
    background: rgba(255,255,255,0.1);
    border-radius: 50%;
}}
.detail-cta-banner h3 {{
    font-size: 1.3em;
    margin-bottom: 8px;
}}
.detail-cta-banner p {{
    opacity: 0.9;
    margin-bottom: 16px;
    font-size: 0.95em;
}}
.detail-cta-features {{
    display: flex;
    justify-content: center;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 20px;
}}
.detail-cta-features span {{
    background: rgba(255,255,255,0.2);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.85em;
}}
.detail-cta-phone {{
    display: inline-block;
    background: var(--cta-orange);
    color: #fff;
    padding: 14px 40px;
    border-radius: 30px;
    text-decoration: none;
    font-weight: 700;
    font-size: 1.3em;
    transition: all 0.2s;
    box-shadow: 0 4px 15px rgba(255,109,0,0.4);
}}
.detail-cta-phone:hover {{
    background: var(--cta-orange-dark);
    transform: translateY(-2px);
    text-decoration: none;
    color: #fff;
}}
.detail-cta-sub {{
    font-size: 0.8em;
    opacity: 0.7;
    margin-top: 8px;
}}

/* 메인 컨설팅 섹션 */
.consulting-section {{
    background: linear-gradient(135deg, #fff3e0, #ffe0b2);
    border: 2px solid var(--cta-orange);
    border-radius: var(--radius-lg);
    padding: 32px;
    margin: 32px auto;
    max-width: 800px;
    text-align: center;
}}
.consulting-section h2 {{
    font-size: 1.5em;
    margin-bottom: 16px;
    color: var(--cta-orange-dark);
}}
.consulting-features {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin: 20px 0;
    text-align: left;
}}
.consulting-feature {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.95em;
}}
.consulting-feature .icon {{
    color: var(--cta-orange);
    font-size: 1.2em;
}}
.consulting-phone-box {{
    background: #fff;
    border-radius: var(--radius-lg);
    padding: 24px;
    margin: 20px 0;
    box-shadow: var(--shadow);
}}
.consulting-phone-number {{
    font-size: 2em;
    font-weight: 800;
    color: var(--cta-orange);
    text-decoration: none;
    display: block;
    margin: 8px 0;
}}
.consulting-phone-number:hover {{ color: var(--cta-orange-dark); text-decoration: none; }}
.consulting-phone-label {{
    color: var(--gray-500);
    font-size: 0.9em;
}}
.consulting-cta-btn {{
    display: inline-block;
    background: var(--cta-orange);
    color: #fff;
    padding: 16px 48px;
    border-radius: 30px;
    text-decoration: none;
    font-weight: 700;
    font-size: 1.2em;
    margin-top: 12px;
    transition: all 0.2s;
    box-shadow: 0 4px 15px rgba(255,109,0,0.3);
}}
.consulting-cta-btn:hover {{
    background: var(--cta-orange-dark);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(255,109,0,0.4);
    text-decoration: none;
    color: #fff;
}}
.consulting-note {{
    font-size: 0.85em;
    color: var(--gray-500);
    margin-top: 12px;
}}

/* ==================== RELATED ITEMS ==================== */
.related-section {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--gray-200); }}
.related-section h3 {{ font-size: 1.2em; font-weight: 700; margin-bottom: 16px; color: var(--gray-700); }}
.related-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 16px;
}}
.related-card {{
    background: #fff;
    border-radius: var(--radius-lg);
    padding: 16px 20px;
    box-shadow: var(--shadow-sm);
    text-decoration: none;
    color: inherit;
    transition: all 0.2s;
    display: block;
    border: 1px solid var(--gray-200);
}}
.related-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--primary-light); text-decoration: none; }}
.related-card .rc-title {{ font-weight: 700; font-size: 0.9em; color: var(--primary); margin-bottom: 6px; }}
.related-card .rc-addr {{ font-size: 0.85em; color: var(--gray-500); margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.related-card .rc-price {{ font-size: 0.85em; color: var(--danger); font-weight: 700; }}

/* ==================== MOBILE BOTTOM NAV ==================== */
.mobile-bottom-nav {{
    display: none;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--cta-orange);
    color: #fff;
    padding: 12px 16px;
    z-index: 200;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.2);
}}
.mobile-bottom-nav a {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    text-decoration: none;
    color: #fff;
    font-weight: 700;
    font-size: 1.1em;
}}
.mobile-bottom-nav a:hover {{ text-decoration: none; }}
.mobile-bottom-nav .pulse {{
    width: 12px;
    height: 12px;
    background: #4caf50;
    border-radius: 50%;
    animation: pulse 1.5s infinite;
}}
@keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 rgba(76,175,80,0.7); }}
    70% {{ box-shadow: 0 0 0 10px rgba(76,175,80,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(76,175,80,0); }}
}}

/* ==================== REGION GRID ==================== */
.region-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 16px;
    padding: 20px 0;
}}
.region-card {{
    background: #fff;
    border-radius: var(--radius-lg);
    padding: 24px;
    text-align: center;
    box-shadow: var(--shadow);
    text-decoration: none;
    color: inherit;
    transition: all 0.2s;
    border: 1px solid var(--gray-200);
}}
.region-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-lg); text-decoration: none; border-color: var(--primary-light); }}
.region-card .region-name {{ font-weight: 700; font-size: 1.1em; }}
.region-card .region-count {{ color: var(--gray-400); font-size: 0.85em; margin-top: 4px; }}

/* ==================== FOOTER ==================== */
.site-footer {{
    background: var(--gray-900);
    color: #fff;
    padding: 48px 0;
    margin-top: 48px;
}}
.footer-links {{ display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 20px; }}
.footer-links a {{ color: var(--gray-400); text-decoration: none; font-size: 0.9em; transition: color 0.15s; }}
.footer-links a:hover {{ color: #fff; }}
.footer-copy {{ color: var(--gray-500); font-size: 0.85em; }}

/* Landing */
/* Update Status Section */
.update-status-section {{ padding: 20px 0; }}
.update-status-card {{ background: #fff; border-radius: var(--radius-xl); padding: 24px; box-shadow: var(--shadow); border: 1px solid var(--gray-200); }}
.update-status-card h2 {{ font-size: 1.1em; margin-bottom: 16px; color: var(--gray-700); }}
.update-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }}
.update-item {{ background: var(--gray-50); border-radius: var(--radius); padding: 12px 16px; display: flex; flex-direction: column; gap: 4px; }}
.update-label {{ font-size: 0.78em; color: var(--gray-400); font-weight: 600; }}
.update-value {{ font-size: 0.95em; font-weight: 700; color: var(--gray-800); }}

.landing-hero {{ padding: 40px 0; text-align: center; }}
.landing-hero h1 {{ font-size: 1.8em; margin-bottom: 8px; }}
.section-title {{ font-size: 1.3em; font-weight: 600; margin: 24px 0 12px; }}

.info-tag {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.85em; margin-right: 4px; }}

/* ==================== RESPONSIVE ==================== */
@media (max-width: 768px) {{
    .item-grid {{ grid-template-columns: 1fr; }}
    .hero {{ padding: 36px 0; }}
    .hero h1 {{ font-size: 1.6em; }}
    .stats-bar {{ gap: 8px; }}
    .stat-card {{ min-width: 100px; padding: 14px; }}
    .stat-card .num {{ font-size: 1.5em; }}
    .search-box {{ flex-direction: column; }}
    .nav {{ gap: 2px; }}
    .nav-link {{ font-size: 0.78em; padding: 6px 10px; }}
    .detail-container {{ padding: 16px; }}
    .detail-card {{ padding: 20px; }}
    .detail-table th {{ width: 110px; font-size: 0.82em; }}
    .detail-table td {{ font-size: 0.92em; }}
    .price-summary {{ grid-template-columns: 1fr; gap: 10px; }}
    .price-card {{ padding: 16px; }}
    .price-card .pc-value {{ font-size: 1.3em; }}
    .region-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .mobile-bottom-nav {{ display: block; }}
    body {{ padding-bottom: 64px; }}
    .related-grid {{ grid-template-columns: 1fr; }}
    .header-search {{ display: none; }}
    .container {{ padding: 0 16px; }}
    .header-cta-btn {{ display: none; }}
    .header-phone {{ font-size: 0.95em; }}
    .consulting-features {{ grid-template-columns: 1fr; }}
    .consulting-phone-number {{ font-size: 1.6em; }}
    .detail-cta-features {{ gap: 8px; }}
    .detail-cta-features span {{ font-size: 0.8em; padding: 3px 8px; }}
}}
'''

# ======================================
# 메인 index.html
# ======================================
def generate_index_html(stats, crawl_info=None):
    head = get_head(
        f'JAuction ㅣ 전국 법원 경매 부동산 정보',
        f'전국 법원 경매 부동산 {stats["total"]:,}건 - 아파트, 토지, 상업용 부동산 경매 정보 제공. 경매컨설팅 상담: {PHONE_NUMBER}',
        f'{SITE_URL}/',
        additional_meta='''<meta name="naver-site-verification" content="3bf2b707098dc68bbe5e8db7aad10955cad77bc0" />
<meta name="google-site-verification" content="S4l-oN4_HbEy6dMoYED7Q645H9LF-8DOkM7_hkgyha4" />''',
        use_legacy_google_verification=False,
    )

    # 업데이트 현황 (작게 표시)
    update_text = ''
    if crawl_info:
        last_crawl = crawl_info.get('last_crawl', '')
        if last_crawl:
            # 날짜만 추출
            date_only = last_crawl[:10] if len(last_crawl) >= 10 else last_crawl
            update_text = f'<span style="color:var(--gray-400);font-size:0.8em;">최종 업데이트: {date_only}</span>'

    return f'''{head}
<body>
{get_header('/', show_search=True)}

<section class="hero">
<div class="container">
<h1 style="font-size:1.8em;font-weight:800;margin-bottom:8px;">전국 법원 경매 정보</h1>
<p style="opacity:0.85;font-size:1em;">아파트·토지·상업용 부동산 {stats["total"]:,}건 실시간 제공</p>
<div class="stats-bar">
<div class="stat-card"><div class="num">{stats["total"]:,}</div><div class="label">전체 물건</div></div>
<div class="stat-card"><div class="num">{stats.get("주거용 부동산", 0):,}</div><div class="label">주거용</div></div>
<div class="stat-card"><div class="num">{stats.get("토지", 0):,}</div><div class="label">토지</div></div>
<div class="stat-card"><div class="num">{stats.get("상업용 부동산", 0):,}</div><div class="label">상업용</div></div>
</div>
</div>
</section>

<section class="search-section">
<div class="container">
<div class="search-box">
<input type="text" id="searchInput" placeholder="사건번호, 주소, 법원명으로 검색..." onkeyup="handleSearch(event)">
<button onclick="doSearch()">검색</button>
</div>
<div class="filters" id="filters">
<a href="#" class="filter-btn active" data-cat="all" onclick="filterCategory('all');return false">전체</a>
<a href="#" class="filter-btn" data-cat="주거용 부동산" onclick="filterCategory('주거용 부동산');return false">주거용</a>
<a href="#" class="filter-btn" data-cat="토지" onclick="filterCategory('토지');return false">토지</a>
<a href="#" class="filter-btn" data-cat="상업용 부동산" onclick="filterCategory('상업용 부동산');return false">상업용</a>
<a href="#" class="filter-btn" data-cat="기타" onclick="filterCategory('기타');return false">기타</a>
</div>
<div style="text-align:center;margin-top:8px;">{update_text}</div>
</div>
</section>

<main class="container">
<div class="item-grid" id="itemGrid">
<div style="text-align:center;padding:60px 0;color:var(--gray-400);">
<div style="font-size:2em;margin-bottom:12px;">⏳</div>
<div>물건 정보를 불러오는 중...</div>
</div>
</div>
<div class="pagination" id="pagination"></div>
<div id="resultCount" style="text-align:center;color:var(--gray-400);font-size:0.9em;padding:8px 0;"></div>
</main>

{get_footer()}

<!-- 모바일 플로팅 CTA -->
<div class="mobile-bottom-nav">
<a href="tel:{PHONE_NUMBER}"><span class="pulse"></span> 📞 무료 경매 상담 {PHONE_NUMBER}</a>
</div>

<script>
const ITEMS_PER_PAGE = 30;
let allItems = [];
let filteredItems = [];
let currentPage = 1;

async function loadData() {{
    try {{
        const resp = await fetch('data.json');
        if (!resp.ok) throw new Error('data.json 로드 실패');
        allItems = await resp.json();
        filteredItems = allItems;
        document.getElementById('resultCount').textContent = '총 ' + allItems.length.toLocaleString() + '건';
        renderPage(1);
    }} catch(e) {{
        document.getElementById('itemGrid').innerHTML = '<div style="text-align:center;padding:60px;color:var(--danger);">⚠️ 데이터를 불러오지 못했습니다. 페이지를 새로고침해주세요.</div>';
        console.error(e);
    }}
}}

function doSearch() {{
    const q = document.getElementById('searchInput').value.toLowerCase().trim();
    if (!q) {{
        filteredItems = allItems;
    }} else {{
        filteredItems = allItems.filter(item =>
            (item.cn || '').toLowerCase().includes(q) ||
            (item.addr || '').toLowerCase().includes(q) ||
            (item.court || '').toLowerCase().includes(q) ||
            (item.sido || '').toLowerCase().includes(q)
        );
    }}
    document.getElementById('resultCount').textContent = '검색결과 ' + filteredItems.length.toLocaleString() + '건';
    renderPage(1);
}}

function handleSearch(e) {{
    if (e.key === 'Enter') doSearch();
}}

function filterCategory(cat) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector('[data-cat="'+cat+'"]');
    if (btn) btn.classList.add('active');
    filteredItems = cat === 'all' ? allItems : allItems.filter(i => i.cat === cat);
    document.getElementById('resultCount').textContent = (cat === 'all' ? '총 ' : cat + ' ') + filteredItems.length.toLocaleString() + '건';
    renderPage(1);
}}

function formatPrice(p) {{
    if (!p) return '-';
    if (p >= 100000000) return (p/100000000).toFixed(1) + '억';
    if (p >= 10000) return (p/10000).toFixed(0) + '만';
    return p.toLocaleString();
}}

function getRate(ap, mp) {{
    if (!ap || !mp) return '';
    return Math.round(mp / ap * 100) + '%';
}}

function getCatBadge(cat) {{
    const m = {{'주거용 부동산':'badge-residential','토지':'badge-land','상업용 부동산':'badge-commercial','기타':'badge-other'}};
    return m[cat] || 'badge-other';
}}

function getCatShort(cat) {{
    const m = {{'주거용 부동산':'주거','토지':'토지','상업용 부동산':'상업','기타':'기타'}};
    return m[cat] || '기타';
}}

function getStatusBadge(s) {{
    const m = {{'진행':'status-proceeding','낙찰':'status-bid','재진행':'status-proceeding','정지':'status-stop','취하':'status-cancel','기각':'status-cancel','신건':'status-new'}};
    return m[s] || 'status-other';
}}

function renderPage(page) {{
    currentPage = page;
    const start = (page - 1) * ITEMS_PER_PAGE;
    const items = filteredItems.slice(start, start + ITEMS_PER_PAGE);
    const grid = document.getElementById('itemGrid');

    if (items.length === 0) {{
        grid.innerHTML = '<div style="text-align:center;padding:60px;color:var(--gray-400);">🔍 검색 결과가 없습니다</div>';
        document.getElementById('pagination').innerHTML = '';
        return;
    }}

    grid.innerHTML = items.map(i => {{
        const rate = getRate(i.ap, i.mp);
        const rateColor = rate ? (parseInt(rate) <= 40 ? '#dc2626' : parseInt(rate) <= 60 ? '#f59e0b' : '#16a34a') : '#6b7280';
        return `
        <a href="auction/${{i.id}}.html" class="item-card">
            <div class="card-header">
                <span class="case-num">${{i.cn || '-'}}</span>
                <span class="category-badge ${{getCatBadge(i.cat)}}">${{getCatShort(i.cat)}}</span>
            </div>
            <div class="card-body">
                <div class="address">${{i.addr || '주소 미확인'}}</div>
                <div class="price-row">
                    <div class="price-item"><div class="price-label">감정가</div><div class="price-value">${{formatPrice(i.ap)}}</div></div>
                    <div class="price-item"><div class="price-label">최저가</div><div class="price-value accent">${{formatPrice(i.mp)}}</div></div>
                    <div class="price-item"><div class="price-label">최저가율</div><div class="price-value" style="color:${{rateColor}};font-weight:800">${{rate || '-'}}</div></div>
                </div>
            </div>
            <div class="card-footer">
                <span>${{i.court || '-'}} ${{i.sd ? '· ' + i.sd : ''}}</span>
                <span class="status-badge ${{getStatusBadge(i.st)}}">${{i.st || '-'}}</span>
            </div>
        </a>`;
    }}).join('');

    const totalPages = Math.ceil(filteredItems.length / ITEMS_PER_PAGE);
    const pg = document.getElementById('pagination');
    if (totalPages <= 1) {{ pg.innerHTML = ''; return; }}
    let html = '';
    if (page > 1) html += `<a href="#" onclick="renderPage(${{page-1}});return false">이전</a>`;
    for (let p = Math.max(1,page-3); p <= Math.min(totalPages,page+3); p++) {{
        html += p === page ? `<span class="active">${{p}}</span>` : `<a href="#" onclick="renderPage(${{p}});return false">${{p}}</a>`;
    }}
    if (page < totalPages) html += `<a href="#" onclick="renderPage(${{page+1}});return false">다음</a>`;
    pg.innerHTML = html;
    window.scrollTo(0, 0);
}}

loadData();
</script>
</body>'''

# ======================================
# 전문가 분석 섹션 HTML
# ======================================
def generate_expert_section(item):
    """전문가 분석 코멘트를 HTML 섹션으로 생성"""
    try:
        comment = generate_expert_comment(item)
    except Exception:
        return ''

    risk = comment.get('risk_level', 'low')
    risk_colors = {'high': '#dc2626', 'medium': '#f59e0b', 'low': '#16a34a'}
    risk_labels = {'high': '고위험', 'medium': '보통', 'low': '낮은위험'}
    risk_bgs = {'high': '#fef2f2', 'medium': '#fffbeb', 'low': '#f0fdf4'}
    risk_borders = {'high': '#fecaca', 'medium': '#fde68a', 'low': '#bbf7d0'}

    color = risk_colors.get(risk, '#6b7280')
    label = risk_labels.get(risk, '분석')
    bg = risk_bgs.get(risk, '#f9fafb')
    border = risk_borders.get(risk, '#e5e7eb')

    summary = html.escape(comment.get('summary', ''))
    opportunity = comment.get('opportunity', '')
    risk_factors = comment.get('risk_factors', '')
    market = comment.get('market', '')
    rec_target = html.escape(comment.get('rec_target', ''))
    rec_tip = html.escape(comment.get('rec_tip', ''))
    cta_msg = html.escape(comment.get('cta_message', ''))

    opp_html = ''
    if opportunity:
        for line in opportunity.strip().split('\n'):
            if line.strip():
                opp_html += f'<div style="padding:4px 0;font-size:13px;color:#15803d;">✅ {html.escape(line.replace("• ",""))}</div>'

    risk_html = ''
    if risk_factors:
        for line in risk_factors.strip().split('\n'):
            if line.strip():
                risk_html += f'<div style="padding:4px 0;font-size:13px;color:#b45309;">⚠️ {html.escape(line.replace("• ",""))}</div>'

    market_html = ''
    if market:
        market_html = f'''<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;padding:10px 14px;margin-top:10px;font-size:13px;color:#0369a1;">
📊 {html.escape(market)}
</div>'''

    return f'''
<div style="background:{bg};border:1px solid {border};border-radius:12px;padding:20px;margin:16px 0;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <span style="background:{color};color:#fff;padding:3px 12px;border-radius:12px;font-size:12px;font-weight:700;">🔍 전문가 분석</span>
        <span style="background:{color}22;color:{color};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{label}</span>
    </div>
    <div style="font-size:15px;font-weight:600;color:#1f2937;margin-bottom:12px;line-height:1.6;">{summary}</div>
    {opp_html}
    {risk_html}
    {market_html}
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:12px 14px;margin-top:12px;">
        <div style="font-size:12px;color:#6b7280;font-weight:600;margin-bottom:4px;">💡 추천 대상</div>
        <div style="font-size:13px;color:#374151;">{rec_target}</div>
        <div style="font-size:13px;color:#6b7280;margin-top:4px;">{rec_tip}</div>
    </div>
    <div style="text-align:center;margin-top:14px;">
        <a href="tel:{PHONE_NUMBER}" style="display:inline-block;background:#ff6d00;color:#fff;padding:10px 28px;border-radius:20px;text-decoration:none;font-weight:700;font-size:14px;box-shadow:0 2px 8px rgba(255,109,0,0.3);">{cta_msg}</a>
    </div>
</div>
'''

# ======================================
# 상세 HTML 페이지
# ======================================
def generate_detail_html(item):
    """개별 경매 물건 상세 페이지 - 자립형 (인라인 CSS, 외부 의존 없음)"""
    iid = item['internal_id']
    cn = item.get('case_number', '')
    court = item.get('court', '')
    addr = item.get('address', '')
    cat = item.get('category', '')
    item_type = item.get('item_type', '')
    status = item.get('status', '')
    ap = item.get('appraisal_price', 0)
    mp = item.get('min_price', 0)
    sp = item.get('sale_price', 0)
    sd = item.get('sale_date', '')
    min_rate = item.get('min_rate', '')

    # 사건번호 포맷: 2026-30059 → 2026타경30059
    def fmt_cn(cn):
        if not cn: return '-'
        if '-' in cn:
            return cn.replace('-', '타경', 1)
        return cn

    def fmt(p):
        if not p: return '-'
        return f'{p:,}원'

    def fmt_big(p):
        if not p: return '-'
        won = f'{p:,}원'
        if p >= 100000000: return f'{p/100000000:.1f}억원 ({won})'
        if p >= 10000: return f'{p/10000:.0f}만원 ({won})'
        return won

    cn_display = fmt_cn(cn)
    title = f'{cn_display} {court} {item_type} 경매 - {SITE_NAME}' if cn else f'경매 물건 {iid} - {SITE_NAME}'
    desc = f'{court} {item_type} 경매 - {addr} 감정가 {fmt_big(ap)} 최저가 {fmt_big(mp)}'

    # 상태 뱃지 클래스
    status_badge_map = {
        '신건': 'badge-new', '진행': 'badge-proceed', '재진행': 'badge-proceed',
        '유찰': 'badge-fail', '낙찰': 'badge-bid', '매각': 'badge-bid',
        '정지': 'badge-stop', '취하': 'badge-cancel', '기각': 'badge-cancel',
        '변경': 'badge-change'
    }
    badge_cls = status_badge_map.get(status, 'badge-proceed')

    def row(label, value, css=''):
        v = html.escape(str(value or '-'))
        return f'<tr><td>{label}</td><td class="{css}">{v}</td></tr>'

    def row_long(label, value):
        v = html_escape_formatted_long_text(value or '')
        return f'<tr><td>{html.escape(label)}</td><td class="text-long-wrap">{v}</td></tr>'

    # 기본정보 섹션
    # gfauction 원본 링크
    gf_link_row = ''
    if cn and '-' in cn:
        sno, tno = cn.split('-', 1)
        gf_url = f'https://gfauction.co.kr/search/search_list.php?aresult=all&sno={sno}&tno={tno}'
        gf_link_row = f'<tr><td>원본</td><td><a href="{gf_url}" target="_blank" rel="noopener" style="color:#1a73e8;font-weight:600;text-decoration:none;">법원경매 무료 정보검색 바로가기 🔗</a></td></tr>'

    basic_rows = ''
    basic_rows += row('사건번호', cn_display)
    basic_rows += gf_link_row
    basic_rows += row('법원', court)
    basic_rows += row('물건종류', item_type)
    basic_rows += row('카테고리', cat)
    basic_rows += row('경매종류', item.get('auction_type'))
    basic_rows += row('매각일', sd)
    basic_rows += f'<tr><td>상태</td><td><span class="badge {badge_cls}">{html.escape(status or "-")}</span></td></tr>'

    # 소재지 섹션
    addr_rows = ''
    addr_rows += f'<tr><td>주소</td><td style="font-size:15px;line-height:1.7;">{format_address_html(addr)}</td></tr>'
    addr_rows += row('시도', item.get('address_sido'))

    # 가격정보 섹션
    price_rows = ''
    price_rows += row('감정가', fmt_big(ap), 'price')
    price_rows += row('최저가', fmt_big(mp), 'price')
    price_rows += row('최저가율', min_rate)
    if sp: price_rows += row('매각가', fmt_big(sp), 'price')
    price_rows += row('청구금액', fmt_big(item.get('claim_amount', 0)))
    price_rows += row('보증금', fmt(item.get('deposit', 0)))

    # 면적정보 섹션
    area_html = ''
    if item.get('land_area') or item.get('building_area'):
        area_rows = ''
        if item.get('land_area'): area_rows += row('토지면적', item['land_area'])
        if item.get('building_area'): area_rows += row('건물면적', item['building_area'])
        area_html = f'''<div class="section"><h2>📐 면적정보</h2><table>{area_rows}</table></div>'''

    # 건물정보 섹션 (건물스펙, 난방, 주차, 승강기, 도로, 승인일, 세대수, 점유, 난이도)
    building_html = ''
    building_rows = ''
    if item.get('building_structure'): building_rows += row('건물구조', item['building_structure'])
    if item.get('building_roof'): building_rows += row('지붕구조', item['building_roof'])
    if item.get('total_floors'):
        floor_text = f'{item["total_floors"]}층'
        if item.get('target_floor'): floor_text += f' (해당 {item["target_floor"]}층)'
        building_rows += row('총층수', floor_text)
    if item.get('heating_type'): building_rows += row('난방방식', item['heating_type'])
    if item.get('parking_available'): building_rows += row('주차', '가능' if item['parking_available'] else '-')
    if item.get('elevator_available'): building_rows += row('승강기', '있음' if item['elevator_available'] else '-')
    if item.get('road_access'): building_rows += row('도로접면', item['road_access'])
    if item.get('approval_date'): building_rows += row('사용승인일', item['approval_date'])
    if item.get('total_households'): building_rows += row('세대수', f'{item["total_households"]}세대')
    if item.get('occupancy_status'): building_rows += row('점유현황', item['occupancy_status'])
    if item.get('land_use_plan'): building_rows += row('토지이용계획', item['land_use_plan'][:200])

    # 난이도 등급
    difficulty = item.get('difficulty_grade', '')
    if difficulty:
        diff_colors = {'A': '#16a34a', 'B': '#2563eb', 'C': '#f59e0b', 'D': '#dc2626'}
        diff_labels = {'A': 'A 초보추천', 'B': 'B 보통', 'C': 'C 주의', 'D': 'D 고난도'}
        dc = diff_colors.get(difficulty, '#6b7280')
        dl = diff_labels.get(difficulty, difficulty)
        building_rows += f'<tr><td>난이도</td><td><span style="background:{dc};color:#fff;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:700;">{html.escape(dl)}</span></td></tr>'

    # 리스크 키워드
    risk_raw = item.get('risk_keywords', '')
    if risk_raw:
        try:
            risk_kws = json.loads(risk_raw) if isinstance(risk_raw, str) else risk_raw
            if risk_kws:
                risk_tags = ' '.join(f'<span style="background:#fef2f2;color:#dc2626;padding:2px 8px;border-radius:8px;font-size:12px;margin:2px;display:inline-block;">{html.escape(kw)}</span>' for kw in risk_kws[:6])
                building_rows += f'<tr><td>리스크</td><td>{risk_tags}</td></tr>'
        except Exception:
            pass

    if building_rows:
        building_html = f'''<div class="section"><h2>🏗️ 건물/시설 정보</h2><table>{building_rows}</table></div>'''

    # 당사자정보 섹션
    party_html = ''
    if item.get('creditor') or item.get('debtor') or item.get('owner'):
        party_rows = ''
        if item.get('creditor'): party_rows += row('채권자', item['creditor'])
        if item.get('debtor'): party_rows += row('채무자', item['debtor'])
        if item.get('owner'): party_rows += row('소유자', item['owner'])
        party_html = f'''<div class="section"><h2>👤 당사자정보</h2><table>{party_rows}</table></div>'''

    # 참고사항 섹션
    notes_html = ''
    if item.get('notes'):
        notes_html = f'''<div class="section"><h2>📝 참고사항</h2><div class="note">{html_escape_formatted_long_text(item["notes"])}</div></div>'''

    # 관련사건
    related_case_html = ''
    if item.get('related_case'):
        related_formatted = format_related_cases_with_links(item['related_case'])
        related_case_html = f'''<div class="section"><h2>🔗 관련사건</h2><table><tr><td>관련사건</td><td class="text-long-wrap">{related_formatted}</td></tr></table></div>'''

    # 임차/권리정보 섹션
    rights_html = ''
    if item.get('tenant_info') or item.get('non_extinguishable_rights') or item.get('non_extinguishable_easement'):
        rights_rows = ''
        if item.get('tenant_info'): rights_rows += row_long('임차내역', item['tenant_info'])
        if item.get('non_extinguishable_rights'): rights_rows += row_long('소멸되지않는권리', item['non_extinguishable_rights'])
        if item.get('non_extinguishable_easement'): rights_rows += row_long('소멸되지않는지상권', item['non_extinguishable_easement'])
        rights_html = f'''<div class="section"><h2>🏠 임차/권리정보</h2><table>{rights_rows}</table></div>'''

    # 차량정보 섹션
    vehicle_html = ''
    vehicle_fields = [('vehicle_name','차명'),('vehicle_year','연식'),('vehicle_maker','제조사'),
                      ('vehicle_fuel','연료'),('vehicle_transmission','변속기'),('vehicle_reg_number','등록번호'),
                      ('vehicle_mileage','주행거리'),('vehicle_displacement','배기량'),('vehicle_vin','차대번호')]
    has_vehicle = any(item.get(f) for f, _ in vehicle_fields)
    if has_vehicle:
        v_rows = ''
        for field, label in vehicle_fields:
            v_rows += row(label, item.get(field, '-'))
        if item.get('vehicle_storage'): v_rows += row('보관장소', item['vehicle_storage'])
        vehicle_html = f'''<div class="section"><h2>🚗 차량정보</h2><table>{v_rows}</table></div>'''

    # 입찰이력
    bid_html = ''
    bid_data = item.get('bid_history', '')
    if bid_data:
        try:
            bids = json.loads(bid_data) if isinstance(bid_data, str) else bid_data
            if bids:
                bid_rows = '<tr style="background:#37474F;color:#fff;"><td>회차</td><td>날짜</td><td>최저가</td><td>결과</td></tr>'
                for b in bids:
                    raw_price = b.get('min_bid_price', 0)
                    formatted_price = format_bid_price(raw_price)
                    if formatted_price is None:
                        continue  # 0인 행 건너뛰기
                    bid_rows += f'<tr><td>{html.escape(str(b.get("bid_round","")))}</td><td>{html.escape(str(b.get("bid_date","")))}</td><td style="font-weight:700;text-align:right;">{html.escape(formatted_price)}</td><td>{html.escape(str(b.get("result","")))}</td></tr>'
                bid_html = f'''<div class="section"><h2>📊 입찰이력</h2><table class="bid-table">{bid_rows}</table></div>'''
        except Exception:
            pass

    # 통계 섹션
    stats_html = ''
    for period, field in [('3개월','stats_3m'),('6개월','stats_6m'),('12개월','stats_12m')]:
        raw = item.get(field, '')
        if raw:
            try:
                s = json.loads(raw) if isinstance(raw, str) else raw
                stats_html += f'<tr><td>{period}</td><td>건수: {s.get("count","-")} / 평균감정가: {s.get("avg_appraisal","-")} / 평균매각가: {s.get("avg_sale","-")} / 실패: {s.get("fail_count","-")}</td></tr>'
            except Exception:
                pass
    stats_section = ''
    if stats_html:
        stats_section = f'''<div class="section"><h2>📊 경매 통계</h2><table>{stats_html}</table></div>'''

    # 이미지 섹션
    img_html = ''
    thumb = item.get('thumbnail_url', '')
    photo_urls_raw = item.get('photo_urls', '')
    photo_urls = []
    if photo_urls_raw:
        try:
            photo_urls = json.loads(photo_urls_raw) if isinstance(photo_urls_raw, str) else photo_urls_raw
        except Exception:
            photo_urls = []

    if photo_urls:
        images_tags = ''
        for purl in photo_urls[:5]:
            images_tags += f'<img src="{html.escape(purl)}" alt="{html.escape(title)}" style="max-width:100%;border-radius:8px;margin:4px" loading="lazy" onerror="this.style.display=\'none\'">\n'
        img_html = f'''<div class="section"><h2>📷 이미지</h2><div style="text-align:center">{images_tags}</div></div>'''
    elif thumb:
        img_html = f'''<div class="section"><h2>📷 이미지</h2><div style="text-align:center"><img src="{thumb}" alt="{html.escape(title)}" style="max-width:100%;border-radius:8px" loading="lazy" onerror="this.style.display=\'none\'"></div></div>'''
    else:
        img_html = '''<div class="section"><h2>📷 이미지</h2><p style="color:#999;text-align:center;padding:20px;">이미지를 불러올 수 없습니다</p></div>'''

    # Schema.org
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "RealEstateListing",
        "name": title,
        "description": desc,
        "url": f'{SITE_URL}/auction/{iid}.html',
        "datePosted": sd,
        "address": {"@type": "PostalAddress", "addressLocality": item.get('address_sido', ''), "streetAddress": addr, "addressCountry": "KR"},
        "offers": {"@type": "Offer", "price": mp, "priceCurrency": "KRW"}
    }, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta name="keywords" content="법원경매,부동산경매,경매물건,{html.escape(title)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:site_name" content="{SITE_NAME}">
<link rel="canonical" href="{SITE_URL}/auction/{iid}.html">
<meta name="google-site-verification" content="VNMGQ8RFZK8mPlJU1cM00-lW4PwxPrA9ZAYGv_cEm_M" />
<meta name="NaverBot" content="All"/>
<meta name="NaverBot" content="index,follow"/>
<meta name="Yeti" content="All"/>
<meta name="Yeti" content="index,follow"/>
<style>
body {{ font-family: 'Malgun Gothic', 'Noto Sans KR', -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
h1 {{ color: #1a237e; border-bottom: 3px solid #1a237e; padding-bottom: 10px; font-size: 22px; }}
.badge {{ display: inline-block; padding: 4px 14px; border-radius: 12px; color: #fff; font-weight: bold; font-size: 14px; }}
.badge-new {{ background: #4CAF50; }}
.badge-proceed {{ background: #2196F3; }}
.badge-fail {{ background: #FF9800; }}
.badge-bid {{ background: #9C27B0; }}
.badge-stop {{ background: #795548; }}
.badge-cancel {{ background: #f44336; }}
.badge-change {{ background: #00BCD4; }}

.section {{ background: #fff; border-radius: 10px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }}
.section h2 {{ font-size: 16px; color: #37474F; margin-bottom: 12px; border-left: 4px solid #2196F3; padding-left: 10px; }}

table {{ width: 100%; border-collapse: collapse; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
td:first-child {{ font-weight: bold; color: #555; width: 140px; background: #fafafa; }}
td:last-child {{ color: #222; }}

/* 입찰이력 테이블 - 모든 셀 동일 너비 */
.bid-table td {{ width: auto; background: transparent; text-align: center; }}
.bid-table td:first-child {{ width: auto; background: transparent; }}

.price {{ color: #1B5E20; font-weight: bold; font-size: 16px; }}
.note {{ background: #FFF3E0; padding: 12px; border-radius: 6px; margin-top: 8px; font-size: 13px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere; }}
td.text-long-wrap {{ white-space: pre-wrap; line-height: 1.7; word-break: break-word; overflow-wrap: anywhere; vertical-align: top; }}

a {{ color: #1565C0; }}
a:hover {{ text-decoration: underline; }}

/* CTA 배너 */
.detail-cta-banner {{
    background: linear-gradient(135deg, #1a73e8, #4285f4);
    border-radius: 12px;
    padding: 28px 24px;
    margin: 24px 0;
    color: #fff;
    text-align: center;
    position: relative;
    overflow: hidden;
}}
.detail-cta-banner h3 {{ font-size: 1.3em; margin-bottom: 8px; }}
.detail-cta-banner p {{ opacity: 0.9; margin-bottom: 16px; font-size: 0.95em; }}
.detail-cta-features {{ display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
.detail-cta-features span {{ background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 16px; font-size: 0.85em; }}
.detail-cta-phone {{
    display: inline-block; background: #ff6d00; color: #fff; padding: 14px 40px;
    border-radius: 30px; text-decoration: none; font-weight: 700; font-size: 1.3em;
    box-shadow: 0 4px 15px rgba(255,109,0,0.4);
}}
.detail-cta-phone:hover {{ background: #e65100; transform: translateY(-2px); text-decoration: none; color: #fff; }}
.detail-cta-sub {{ font-size: 0.8em; opacity: 0.7; margin-top: 8px; }}

/* 모바일 플로팅 CTA */
.mobile-floating-cta {{
    display: none; position: fixed; bottom: 0; left: 0; right: 0;
    background: #ff6d00; color: #fff; padding: 14px 16px; z-index: 1000;
    text-align: center; font-weight: 700; font-size: 1.1em;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.2);
}}
.mobile-floating-cta a {{ color: #fff; text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 8px; }}
.mobile-floating-cta .pulse {{ width: 12px; height: 12px; background: #4caf50; border-radius: 50%; animation: pulse 1.5s infinite; }}
@keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 rgba(76,175,80,0.7); }}
    70% {{ box-shadow: 0 0 0 10px rgba(76,175,80,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(76,175,80,0); }}
}}

@media (max-width: 600px) {{
    body {{ padding: 12px; padding-bottom: 70px; }}
    h1 {{ font-size: 18px; }}
    td:first-child {{ width: 100px; font-size: 13px; }}
    td:last-child {{ font-size: 13px; }}
    .mobile-floating-cta {{ display: block; }}
    .detail-cta-features {{ gap: 8px; }}
    .detail-cta-features span {{ font-size: 0.8em; padding: 3px 8px; }}
}}
</style>
</head>
<body>

<h1>{html.escape(cn_display)} <span class="badge {badge_cls}">{html.escape(status or "-")}</span></h1>

<!-- 전문가 분석 -->
{generate_expert_section(item)}

<!-- 상단 CTA 바 -->
<div style="background:#1a73e8;color:#fff;text-align:center;padding:10px 16px;border-radius:8px;margin-bottom:16px;font-size:15px;">
<a href="tel:{PHONE_NUMBER}" style="color:#fff;text-decoration:none;font-weight:700;">📞 이 물건 전문가 분석 문의 {PHONE_NUMBER}</a>
</div>

<div class="section">
<h2>📋 기본정보</h2>
<table>
{basic_rows}
</table>
</div>

<div class="section">
<h2>📍 소재지</h2>
<table>
{addr_rows}
</table>
</div>

<div class="section">
<h2>💰 가격정보</h2>
<table>
{price_rows}
</table>
</div>

<!-- 중간 CTA 카드 -->
<div style="background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:20px 0;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
<div style="font-size:16px;font-weight:700;color:#333;margin-bottom:12px;">💡 이 물건 투자 가치가 궁금하신가요?</div>
<div style="display:flex;justify-content:center;gap:16px;margin-bottom:16px;flex-wrap:wrap;">
<span style="background:#e8f0fe;color:#1a73e8;padding:4px 12px;border-radius:16px;font-size:13px;">✅ 권리관계 분석</span>
<span style="background:#e8f0fe;color:#1a73e8;padding:4px 12px;border-radius:16px;font-size:13px;">✅ 시세 비교</span>
</div>
<a href="tel:{PHONE_NUMBER}" style="display:inline-block;background:#ff6d00;color:#fff;padding:12px 36px;border-radius:24px;text-decoration:none;font-weight:700;font-size:18px;">📞 {PHONE_NUMBER}</a>
<div style="font-size:12px;color:#999;margin-top:8px;">경매컨설팅 상담 (무료)</div>
</div>

{area_html}
{building_html}
{party_html}
{notes_html}
{related_case_html}
{rights_html}
{vehicle_html}
{bid_html}
{stats_section}
{img_html}

<!-- 문의 -->
<div style="text-align:center;padding:20px 0;margin-top:16px;border-top:1px solid #eee;color:#666;font-size:14px;">
경매 물건 문의: <a href="tel:{PHONE_NUMBER}" style="font-weight:700;color:#1a73e8;">📞 {PHONE_NUMBER}</a>
</div>

<!-- 모바일 플로팅 CTA -->
<div class="mobile-floating-cta">
<a href="tel:{PHONE_NUMBER}"><span class="pulse"></span> 📞 무료 경매 상담 {PHONE_NUMBER}</a>
</div>

<script type="application/ld+json">
{schema}
</script>
</body>
</html>'''

# ======================================
# 랜딩 페이지 생성
# ======================================
def generate_category_landing(cat_key, cat_name, cat_korean, items_data):
    """카테고리 랜딩 페이지"""
    title = f'{cat_name} 경매 물건 - {SITE_NAME}'
    desc = f'전국 {cat_name} 경매 물건 {len(items_data):,}건 - 최저가, 감정가, 매각일정 실시간 제공'
    canonical = f'{SITE_URL}/{cat_key}/'

    head = get_head(title, desc, canonical, css_path='../style.css')

    items_html = ''
    for i in items_data[:60]:
        def fmt(p):
            if not p: return '-'
            if p >= 100000000: return f'{p/100000000:.1f}억'
            return f'{p/10000:.0f}만'

        items_html += f'''
        <a href="../auction/{i["id"]}.html" class="item-card">
            <div class="card-header">
                <span class="case-num">{i.get("cn","-")}</span>
                <span class="status-badge status-proceeding">{i.get("st","-")}</span>
            </div>
            <div class="card-body">
                <div class="address">{html.escape(i.get("addr","")[:60])}</div>
                <div class="price-row">
                    <div class="price-item"><div class="price-label">감정가</div><div class="price-value">{fmt(i.get("ap",0))}</div></div>
                    <div class="price-item"><div class="price-label">최저가</div><div class="price-value accent">{fmt(i.get("mp",0))}</div></div>
                    <div class="price-item"><div class="price-label">매각일</div><div class="price-value">{i.get("sd","-")}</div></div>
                </div>
            </div>
            <div class="card-footer"><span>{i.get("court","-")}</span></div>
        </a>'''

    return f'''{head}
<body>
{get_header(f'/{cat_key}/', base_path='../')}
<section class="hero">
<div class="container">
<h1>{cat_name} 경매 물건</h1>
<p>전국 {cat_name} 경매 {len(items_data):,}건</p>
</div>
</section>
<main class="container">
<div class="item-grid">{items_html}</div>
</main>
{get_footer(base_path='../')}
<div class="mobile-bottom-nav">
<a href="tel:{PHONE_NUMBER}"><span class="pulse"></span> 📞 무료 경매 상담 {PHONE_NUMBER}</a>
</div>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"CollectionPage","name":"{cat_name} 경매","description":"{desc}","url":"{canonical}","numberOfItems":{len(items_data)}}}
</script>
</body>'''

def generate_region_landing(region_key, region_name, items_data):
    """지역 랜딩 페이지"""
    title = f'{region_name} 경매 부동산 - {SITE_NAME}'
    desc = f'{region_name} 경매 부동산 {len(items_data):,}건 - 아파트, 토지, 상업용 경매 정보'
    canonical = f'{SITE_URL}/region/{region_key}/'

    head = get_head(title, desc, canonical, css_path='../../style.css')

    items_html = ''
    for i in items_data[:60]:
        def fmt(p):
            if not p: return '-'
            if p >= 100000000: return f'{p/100000000:.1f}억'
            return f'{p/10000:.0f}만'

        items_html += f'''
        <a href="../../auction/{i["id"]}.html" class="item-card">
            <div class="card-header">
                <span class="case-num">{i.get("cn","-")}</span>
                <span class="category-badge badge-residential">{i.get("cat","")}</span>
            </div>
            <div class="card-body">
                <div class="address">{html.escape(i.get("addr","")[:60])}</div>
                <div class="price-row">
                    <div class="price-item"><div class="price-label">감정가</div><div class="price-value">{fmt(i.get("ap",0))}</div></div>
                    <div class="price-item"><div class="price-label">최저가</div><div class="price-value accent">{fmt(i.get("mp",0))}</div></div>
                </div>
            </div>
        </a>'''

    return f'''{head}
<body>
{get_header('/region/', base_path='../../')}
<section class="hero">
<div class="container">
<h1>{region_name} 경매 부동산</h1>
<p>{region_name} 지역 경매 물건 {len(items_data):,}건</p>
</div>
</section>
<main class="container">
<div class="item-grid">{items_html}</div>
</main>
{get_footer(base_path='../../')}
<div class="mobile-bottom-nav">
<a href="tel:{PHONE_NUMBER}"><span class="pulse"></span> 📞 무료 경매 상담 {PHONE_NUMBER}</a>
</div>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"CollectionPage","name":"{region_name} 경매","description":"{desc}","url":"{canonical}","numberOfItems":{len(items_data)}}}
</script>
</body>'''

def generate_region_index_html(sido_items):
    """지역별 인덱스 페이지 (region/index.html)"""
    title = f'지역별 경매 부동산 - {SITE_NAME}'
    desc = '전국 시도별 법원 경매 부동산 정보 - 서울, 경기, 부산, 인천 등 지역별 경매 물건 검색'
    canonical = f'{SITE_URL}/region/'

    head = get_head(title, desc, canonical, css_path='../style.css')

    region_cards = ''
    for sido, slug in REGION_MAP.items():
        count = len(sido_items.get(sido, []))
        region_name = REGION_TITLE.get(slug, sido)
        region_cards += f'''
        <a href="{slug}/" class="region-card">
            <div class="region-name">{region_name}</div>
            <div class="region-count">{count:,}건</div>
        </a>'''

    return f'''{head}
<body>
{get_header('region/', base_path='../')}

<section class="hero" style="padding:40px 0">
<div class="container">
<h1 style="font-size:1.8em;font-weight:800;margin-bottom:8px;">🗺️ 지역별 경매 부동산</h1>
<p style="opacity:0.85;font-size:1em;">전국 17개 시도 경매 물건을 한눈에</p>
</div>
</section>

<main class="container">
<div class="region-grid">{region_cards}</div>
</main>

{get_footer(base_path='../')}

<div class="mobile-bottom-nav">
<a href="tel:{PHONE_NUMBER}"><span class="pulse"></span> 📞 무료 경매 상담 {PHONE_NUMBER}</a>
</div>

<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"CollectionPage","name":"지역별 경매 부동산","description":"{desc}","url":"{canonical}"}}
</script>
</body>'''

# ======================================
# 정적 페이지 전용 인라인 CSS 및 헬퍼
# ======================================
_STATIC_CSS = """
:root{--primary:#2563eb;--primary-dark:#1d4ed8;--primary-light:#dbeafe;--gray-50:#f9fafb;--gray-100:#f3f4f6;--gray-200:#e5e7eb;--gray-300:#d1d5db;--gray-400:#9ca3af;--gray-500:#6b7280;--gray-600:#4b5563;--gray-700:#374151;--gray-800:#1f2937;--gray-900:#111827;--cta-orange:#ff6d00;--cta-orange-dark:#e65100;--danger:#dc2626;--shadow:0 1px 3px rgba(0,0,0,.1);--shadow-lg:0 10px 15px -3px rgba(0,0,0,.1);--radius:8px;--radius-lg:12px;--radius-xl:16px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",sans-serif;color:var(--gray-800);background:var(--gray-50);line-height:1.7;font-size:16px}
a{color:var(--primary);text-decoration:none}a:hover{text-decoration:underline}
.container{max-width:1200px;margin:0 auto;padding:0 24px}
.site-header{background:#fff;border-bottom:1px solid var(--gray-200);position:sticky;top:0;z-index:100;box-shadow:0 1px 2px rgba(0,0,0,.05)}
.site-header .container{display:flex;align-items:center;justify-content:space-between;height:64px;gap:16px}
.logo{font-size:1.4em;font-weight:800;color:var(--primary);text-decoration:none;white-space:nowrap}.logo:hover{text-decoration:none}
.nav{display:flex;gap:4px;align-items:center}
.nav-link{padding:8px 14px;border-radius:8px;text-decoration:none;color:var(--gray-600);font-size:.9em;font-weight:500;white-space:nowrap;transition:all .15s}
.nav-link:hover{background:var(--gray-100);color:var(--gray-900);text-decoration:none}
.header-phone{display:flex;align-items:center;gap:6px;text-decoration:none;color:var(--cta-orange);font-weight:700;font-size:1.1em}.header-phone:hover{color:var(--cta-orange-dark);text-decoration:none}
.header-phone-icon{background:var(--cta-orange);color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center}
.detail-container{max-width:900px;margin:0 auto;padding:32px 24px}
.detail-card{background:#fff;border-radius:var(--radius-xl);box-shadow:var(--shadow);padding:28px 32px;margin-bottom:20px;border:1px solid var(--gray-200)}
.detail-card h2{font-size:1.4em;font-weight:700;margin-bottom:20px;padding-bottom:12px;border-bottom:2px solid var(--gray-100);color:var(--gray-800)}
.detail-card ul,.detail-card ol{padding-left:24px;line-height:2}
.detail-card p{margin-bottom:8px}
.site-footer{background:var(--gray-900);color:#fff;padding:48px 0;margin-top:48px}
.footer-links{display:flex;gap:24px;flex-wrap:wrap;margin-bottom:20px}
.footer-links a{color:var(--gray-400);text-decoration:none;font-size:.9em}.footer-links a:hover{color:#fff}
.footer-copy{color:var(--gray-500);font-size:.85em}
.dict-table{width:100%;border-collapse:collapse}
.dict-table td{padding:14px 16px;border-bottom:1px solid var(--gray-100);vertical-align:top}
.dict-table td:first-child{font-weight:700;width:130px;color:var(--gray-700);background:var(--gray-50);border-radius:6px}
.dict-table tr:last-child td{border-bottom:none}
.dict-table tr:hover{background:var(--gray-50)}
.tip-box{margin-top:16px;padding:16px 20px;border-radius:var(--radius-lg)}
.tip-blue{background:#e8f0fe;border-left:4px solid var(--primary)}
.tip-red{background:#fef2f2;border-left:4px solid var(--danger)}
.tip-orange{background:linear-gradient(135deg,#fff3e0,#ffe0b2);border:2px solid var(--cta-orange);text-align:center;border-radius:12px;padding:24px}
.cta-btn{display:inline-block;background:var(--cta-orange);color:#fff;padding:14px 36px;border-radius:24px;text-decoration:none!important;font-weight:700;font-size:18px;margin-top:12px;box-shadow:0 4px 15px rgba(255,109,0,.4)}.cta-btn:hover{background:var(--cta-orange-dark);color:#fff!important;text-decoration:none!important}
@media(max-width:768px){.nav{gap:2px}.nav-link{font-size:.78em;padding:6px 10px}.detail-container{padding:16px}.detail-card{padding:20px}.container{padding:0 16px}}
"""

def _static_head(title, desc, canonical):
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta name="keywords" content="법원경매,부동산경매,경매물건,jauction,{html.escape(title)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:image" content="{SITE_URL}/images/kakao_img.png">
<link rel="canonical" href="{canonical}">
<meta name="NaverBot" content="All"/>
<meta name="NaverBot" content="index,follow"/>
<meta name="Yeti" content="All"/>
<meta name="Yeti" content="index,follow"/>
<meta name="google-site-verification" content="VNMGQ8RFZK8mPlJU1cM00-lW4PwxPrA9ZAYGv_cEm_M" />
<style>{_STATIC_CSS}</style>
</head>'''

def _static_header():
    nav = '<a href="../" class="nav-link">홈</a>\n<a href="../apartment/" class="nav-link">아파트/주거</a>\n<a href="../land/" class="nav-link">토지</a>\n<a href="../commercial/" class="nav-link">상업용</a>\n<a href="../region/" class="nav-link">지역별</a>\n<a href="../faq/" class="nav-link">FAQ</a>'
    return f'''<header class="site-header">
<div class="container">
<a href="../" class="logo">🏷️ {SITE_NAME}</a>
<a href="tel:{PHONE_NUMBER}" class="header-phone">
<span class="header-phone-icon">📞</span>{PHONE_NUMBER}
</a>
<nav class="nav">{nav}</nav>
</div>
</header>'''

def _static_footer():
    return f'''<footer class="site-footer">
<div class="container">
<div class="footer-links">
<a href="../guide/">경매가이드</a>
<a href="../dictionary/">용어사전</a>
<a href="../about/">사이트 소개</a>
<a href="../privacy/">개인정보처리방침</a>
<a href="../terms/">이용약관</a>
<a href="../faq/">자주묻는질문</a>
<a href="../feed.xml">RSS</a>
</div>
<p class="footer-copy">© {datetime.now().year} {SITE_NAME}. 본 사이트는 참고용이며, 실제 경매 정보는 해당 법원에서 확인하세요.</p>
<p class="footer-copy" style="margin-top:6px;font-size:0.8em;">최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
</footer>'''

# ======================================
# 정적 페이지 (FAQ, About, Privacy, Terms, Guide, Dictionary)
# ======================================
def generate_static_pages():
    pages = {
        'faq/index.html': {
            'title': f'자주 묻는 질문 - {SITE_NAME}',
            'desc': '법원 경매에 관한 자주 묻는 질문과 답변',
            'content': f'''
<h1>❓ 자주 묻는 질문</h1>

<div class="detail-card">
<h2>법원 경매란?</h2>
<p>법원 경매는 채무자가 빚을 갚지 못할 경우, 법원이 채무자의 부동산을 강제로 매각하여 채권자에게 배당하는 절차입니다. 일반인도 입찰에 참여할 수 있습니다.</p>
</div>

<div class="detail-card">
<h2>경매 참여 자격</h2>
<p>법원 경매는 누구나 참여할 수 있습니다. 개인, 법인 모두 가능하며, 특별한 자격증이나 등록이 필요하지 않습니다.</p>
</div>

<div class="detail-card">
<h2>입찰 보증금은 얼마인가요?</h2>
<p>입찰 보증금은 최저매각가격의 10%~20%입니다. 낙찰 시에는 잔금을 납부해야 하며, 미납 시 보증금은 몰수됩니다.</p>
</div>

<div class="detail-card">
<h2>감정가와 최저가의 차이는?</h2>
<p>감정가는 감정평가사가 평가한 부동산의 시장 가치입니다. 최저가는 경매에서 입찰할 수 있는 최소 가격으로, 유찰될 때마다 낮아집니다.</p>
</div>

<div class="detail-card">
<h2>낙찰 후 해야 할 일은?</h2>
<p>낙찰 후에는 지정된 기일 내에 잔금을 납부해야 합니다. 잔금 납부 후 소유권 이전등기를 완료하면 법적으로 소유자가 됩니다.</p>
</div>

<div class="detail-card">
<h2>경매 물건의 위험은?</h2>
<p>선순위 임차인, 소멸되지 않는 권리, 명도 문제 등이 있을 수 있습니다. 반드시 등기부등본과 현장을 확인하고 법률 전문가의 조언을 구하세요.</p>
<p style="margin-top:12px"><strong>전문가 상담:</strong> <a href="tel:{PHONE_NUMBER}">📞 {PHONE_NUMBER}</a> (무료상담)</p>
</div>
'''
        },
        'about/index.html': {
            'title': f'사이트 소개 - {SITE_NAME}',
            'desc': f'{SITE_NAME} 사이트 소개 - 전국 법원 경매 부동산 정보 제공',
            'content': f'''
<h1>🏷️ 사이트 소개</h1>
<div class="detail-card">
<h2>{SITE_NAME}이란?</h2>
<p>{SITE_NAME}은 전국 법원 경매 부동산 정보를 수집하여 제공하는 서비스입니다. 아파트, 토지, 상업용 부동산 등 다양한 경매 물건을 쉽게 검색하고 비교할 수 있습니다.</p>
</div>
<div class="detail-card">
<h2>제공 정보</h2>
<ul style="padding-left:20px;line-height:2">
<li>전국 법원 경매 물건 32,000건 이상</li>
<li>사건번호, 감정가, 최저가, 매각일정</li>
<li>주소, 물건종류, 법원정보</li>
<li>카테고리별, 지역별 검색</li>
</ul>
</div>
<div class="detail-card">
<h2>경매 컨설팅</h2>
<p>전문가의 컨설팅으로 안전한 경매 투자를 시작하세요.</p>
<p style="margin-top:12px"><strong>무료 상담:</strong> <a href="tel:{PHONE_NUMBER}">📞 {PHONE_NUMBER}</a></p>
</div>
<div class="detail-card">
<h2>면책 조항</h2>
<p>본 사이트의 정보는 참고용이며, 실제 경매 정보는 해당 법원의 공고에서 확인하시기 바랍니다. 정보의 정확성에 대해 책임지지 않습니다.</p>
</div>
'''
        },
        'privacy/index.html': {
            'title': f'개인정보처리방침 - {SITE_NAME}',
            'desc': f'{SITE_NAME} 개인정보처리방침',
            'content': '''
<h1>🔒 개인정보처리방침</h1>
<div class="detail-card">
<h2>1. 수집하는 개인정보</h2>
<p>본 사이트는 사용자의 개인정보를 수집하지 않습니다.</p>
</div>
<div class="detail-card">
<h2>2. 쿠키 사용</h2>
<p>본 사이트는 분석 목적으로 쿠키를 사용할 수 있습니다.</p>
</div>
<div class="detail-card">
<h2>3. 제3자 제공</h2>
<p>수집된 정보는 제3자에게 제공되지 않습니다.</p>
</div>
<div class="detail-card">
<h2>4. 문의</h2>
<p>개인정보 관련 문의는 이메일로 연락 주시기 바랍니다.</p>
</div>
'''
        },
        'guide/index.html': {
            'title': f'법원 경매 가이드 - {SITE_NAME}',
            'desc': '법원 경매 입찰 방법, 절차, 주의사항 등 초보자를 위한 종합 가이드',
            'content': f'''
<h1>📚 법원 경매 완벽 가이드</h1>

<div class="detail-card">
<h2>1. 법원 경매란?</h2>
<p>법원 경매는 채무자가 빚을 갚지 못할 경우, 법원이 채무자의 부동산을 강제로 매각하는 절차입니다. 일반인도 입찰에 참여할 수 있으며, 시세보다 저렴하게 부동산을 취득할 수 있는 기회입니다.</p>
<ul style="padding-left:20px;line-height:2;margin-top:8px">
<li><strong>강제경매</strong>: 채권자의 신청으로 진행</li>
<li><strong>임의경매</strong>: 담보권 실행으로 진행 (대부분)</li>
</ul>
</div>

<div class="detail-card">
<h2>2. 경매 진행 절차</h2>
<ol style="padding-left:20px;line-height:2.2">
<li><strong>경매개시결정</strong> → 법원이 경매 절차 시작</li>
<li><strong>현황조사</strong> → 법원이 부동산 현황 확인</li>
<li><strong>감정평가</strong> → 감정평가사가 시장가치 평가 (감정가)</li>
<li><strong>매각공고</strong> → 법원이 매각일, 최저가 공고</li>
<li><strong>입찰</strong> → 입찰자들이 가격 제출</li>
<li><strong>개찰 및 낙찰</strong> → 최고가 입찰자가 낙찰</li>
<li><strong>대금납부</strong> → 낙찰자가 잔금 납부</li>
<li><strong>소유권이전</strong> → 등기부등본에 소유자 변경</li>
</ol>
</div>

<div class="detail-card">
<h2>3. 입찰 참여 방법</h2>
<p>경매 입찰에 참여하려면 다음이 필요합니다:</p>
<ul style="padding-left:20px;line-height:2">
<li><strong>입찰보증금</strong>: 최저매각가격의 10~20%</li>
<li><strong>신분증</strong>: 주민등록증 또는 운전면허증</li>
<li><strong>도장</strong>: 본인 도장 (서명 가능)</li>
<li><strong>입찰표</strong>: 법원 비치</li>
</ul>
<p style="margin-top:12px;padding:12px;background:#e8f0fe;border-radius:8px;">💡 <strong>팁</strong>: 온라인 입찰도 가능합니다. 대법원 경매정보 사이트에서 인터넷 입찰을 이용할 수 있습니다.</p>
</div>

<div class="detail-card">
<h2>4. 유찰과 최저가</h2>
<p>입찰자가 없거나 최저가 미만으로 입찰된 경우 <strong>유찰</strong>됩니다. 유찰 시 최저가가 낮아집니다:</p>
<ul style="padding-left:20px;line-height:2">
<li>1차 매각: 감정가의 <strong>80%</strong></li>
<li>1차 유찰 후: 이전 최저가의 <strong>80%</strong></li>
<li>반복 유찰 시 최저가가 계속 하락</li>
</ul>
<p style="margin-top:12px">예: 감정가 10억 → 1차 최저가 8억 → 2차 최저가 6.4억 → 3차 최저가 5.12억</p>
</div>

<div class="detail-card">
<h2>5. 반드시 확인해야 할 것</h2>
<ul style="padding-left:20px;line-height:2">
<li>✅ <strong>등기부등본</strong>: 권리관계, 선순위 채권 확인</li>
<li>✅ <strong>현장 방문</strong>: 실제 점유자, 시설 상태 확인</li>
<li>✅ <strong>임대차 현황</strong>: 선순위 임차인, 대항력 여부</li>
<li>✅ <strong>주변 시세</strong>: 감정가 대비 실제 시세 비교</li>
<li>✅ <strong>납부 일정</strong>: 잔금 납부 기한 확인</li>
</ul>
<p style="margin-top:12px;padding:12px;background:#fef2f2;border-radius:8px;">⚠️ <strong>주의</strong>: 소멸되지 않는 권리(선순위 임차인, 유치권 등)가 있으면 낙찰 후에도 부담해야 합니다.</p>
</div>

<div class="detail-card">
<h2>6. 낙찰 후 절차</h2>
<ol style="padding-left:20px;line-height:2">
<li><strong>대금납부</strong>: 낙찰일로부터 보통 30~60일 이내</li>
<li><strong>소유권이전등기</strong>: 법원이 촉탁 (직권)</li>
<li><strong>명도</strong>: 점유자가 자진 퇴거하면 OK, 아니면 강제집행</li>
<li><strong>부담금 처리</strong>: 관리비, 세금 등 정산</li>
</ol>
</div>

<div style="text-align:center;margin:24px 0;padding:20px;background:linear-gradient(135deg,#fff3e0,#ffe0b2);border-radius:12px;border:2px solid #ff6d00;">
<h3 style="color:#e65100;margin-bottom:12px;">🎯 경매 전문가 상담</h3>
<p style="margin-bottom:16px">초보자도 안전하게 경매에 참여할 수 있습니다.<br>전문가가 권리관계 분석, 시세 비교, 입찰 전략을 도와드립니다.</p>
<a href="tel:{PHONE_NUMBER}" style="display:inline-block;background:#ff6d00;color:#fff;padding:14px 36px;border-radius:24px;text-decoration:none;font-weight:700;font-size:18px;">📞 무료 상담 {PHONE_NUMBER}</a>
</div>
'''
        },
        'dictionary/index.html': {
            'title': f'경매 용어사전 - {SITE_NAME}',
            'desc': '법원 경매 용어 정리 - 감정가, 유찰, 낙찰, 대항력 등 경매 관련 용어 모음',
            'content': f'''
<h1>📖 경매 용어사전</h1>

<div class="detail-card">
<h2>가~나</h2>
<table style="width:100%;border-collapse:collapse">
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;width:120px;background:#f8f9fa">감정가</td><td style="padding:10px">감정평가사가 평가한 부동산의 시장 가치. 경매 최저가의 기준이 됩니다.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">경매개시</td><td style="padding:10px">법원이 경매 절차를 시작한다는 결정. 채권자의 신청으로 이루어집니다.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">권리분석</td><td style="padding:10px">등기부등본과 현황조사보고서를 통해 부동산의 권리관계를 분석하는 것.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">낙찰</td><td style="padding:10px">경매에서 최고가로 입찰하여 부동산을 취득하는 것.</td></tr>
</table>
</div>

<div class="detail-card">
<h2>다~마</h2>
<table style="width:100%;border-collapse:collapse">
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;width:120px;background:#f8f9fa">대항력</td><td style="padding:10px">임차인이 주택임대차보호법에 따라 임대인 외의 제3자에게도 임대차를 주장할 수 있는 권리. 전입신고 + 확정일자 필요.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">명도</td><td style="padding:10px">낙찰 후 점유자가 부동산을 비워주는 것. 자진 명도가 안 되면 강제집행.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">매각</td><td style="padding:10px">경매에서 부동산을 판매하는 것. 낙찰과 같은 의미로 사용되기도 함.</td></tr>
</table>
</div>

<div class="detail-card">
<h2>바~사</h2>
<table style="width:100%;border-collapse:collapse">
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;width:120px;background:#f8f9fa">선순위임차인</td><td style="padding:10px">낙찰자보다 먼저 권리를 가진 임차인. 소멸되지 않으며 낙찰자가 보증금을 승계.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">소멸주의</td><td style="padding:10px">경매 낙찰 시 후순위 권리가 소멸되는 원칙. 선순위는 소멸되지 않을 수 있음.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">소유권이전</td><td style="padding:10px">낙찰 후 부동산의 소유권이 낙찰자에게 넘어가는 등기.</td></tr>
</table>
</div>

<div class="detail-card">
<h2>아~자</h2>
<table style="width:100%;border-collapse:collapse">
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;width:120px;background:#f8f9fa">유찰</td><td style="padding:10px">경매에서 입찰자가 없거나 유효한 입찰이 없어 매각이 실패하는 것. 최저가가 하락합니다.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">유치권</td><td style="padding:10px">타인의 물건에 관해 비용을 지출한 자가 그 비용의 변제를 받을 때까지 물건을 유치할 수 있는 권리. 경매에서 소멸되지 않음.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">입찰보증금</td><td style="padding:10px">입찰 시 납부하는 보증금. 최저매각가격의 10~20%. 낙찰 후 잔금에 포함.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">임의경매</td><td style="padding:10px">담보권(근저당 등)을 실행하는 경매. 대부분의 경매가 여기에 해당.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">지분경매</td><td style="padding:10px">부동산 전체가 아닌 공유지분 일부에 대한 경매. 주의 필요.</td></tr>
</table>
</div>

<div class="detail-card">
<h2>차~타</h2>
<table style="width:100%;border-collapse:collapse">
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;width:120px;background:#f8f9fa">청구금액</td><td style="padding:10px">채권자가 경매를 신청한 근거가 되는 채권 금액.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">최저가</td><td style="padding:10px">경매에서 입찰할 수 있는 최소 가격. 감정가의 80%에서 시작, 유찰 시마다 하락.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">최저가율</td><td style="padding:10px">최저가를 감정가로 나눈 비율. 낮을수록 싼 가격에 입찰 가능.</td></tr>
<tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;background:#f8f9fa">확정일자</td><td style="padding:10px">임대차계약서에 주택임대차보호법상 대항력을 갖추기 위해 확정일자를 받는 것.</td></tr>
</table>
</div>

<div style="text-align:center;margin:24px 0;padding:20px;background:linear-gradient(135deg,#e8f0fe,#dbeafe);border-radius:12px;">
<h3 style="color:#1a73e8;margin-bottom:12px;">💡 더 궁금한 점이 있으신가요?</h3>
<p style="margin-bottom:16px">경매 용어가 어려우시면 전문가에게 무료로 상담하세요.</p>
<a href="tel:{PHONE_NUMBER}" style="display:inline-block;background:#ff6d00;color:#fff;padding:14px 36px;border-radius:24px;text-decoration:none;font-weight:700;font-size:18px;">📞 무료 상담 {PHONE_NUMBER}</a>
</div>
'''
        },
        'terms/index.html': {
            'title': f'이용약관 - {SITE_NAME}',
            'desc': f'{SITE_NAME} 이용약관',
            'content': f'''
<h1>📄 이용약관</h1>
<div class="detail-card">
<h2>제1조 (목적)</h2>
<p>본 약관은 {SITE_NAME} 사이트의 이용 조건 및 절차를 규정합니다.</p>
</div>
<div class="detail-card">
<h2>제2조 (정보의 성격)</h2>
<p>본 사이트에서 제공하는 경매 정보는 참고용이며, 법적 효력이 없습니다. 정확한 정보는 해당 법원에서 확인하시기 바랍니다.</p>
</div>
<div class="detail-card">
<h2>제3조 (면책)</h2>
<p>사이트 운영자는 제공 정보의 정확성, 완전성에 대해 어떠한 보증도 하지 않으며, 정보 이용으로 발생한 손해에 대해 책임지지 않습니다.</p>
</div>
'''
        },
    }

    result = {}
    for path, data in pages.items():
        canonical = f'{SITE_URL}/{path.replace("index.html","")}'
        head = _static_head(data['title'], data['desc'], canonical)
        full_html = f'''{head}
<body>
{_static_header()}
<main class="detail-container">
{data['content']}
</main>
{_static_footer()}
</body>'''
        result[path] = full_html
    return result

# ======================================
# RSS Feed
# ======================================
def generate_rss(items_data, title, description, filename):
    """RSS XML 생성"""
    now = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0900')
    items_xml = ''
    for i in items_data[:500]:
        cn = i.get('cn', '')
        addr = i.get('addr', '')
        court = i.get('court', '')
        ap = i.get('ap', 0)
        mp = i.get('mp', 0)
        sd = i.get('sd', '')
        iid = i.get('id', '')
        cat = i.get('cat', '')

        item_title = f'[{cn}] {addr[:40]} - 감정가 {ap:,}원' if ap else f'[{cn}] {addr[:40]}'
        link = f'{SITE_URL}/auction/{iid}.html'
        item_desc = f'{court} {cat} 경매 - 소재지: {addr}, 감정가: {ap:,}원, 최저가: {mp:,}원, 매각일: {sd}'
        pub_date = sd.replace('.', '-') if sd else now

        items_xml += f'''
<item>
<title>{html.escape(item_title)}</title>
<link>{link}</link>
<description>{html.escape(item_desc)}</description>
<pubDate>{pub_date}</pubDate>
<category>{html.escape(cat)}</category>
</item>'''

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<title>{html.escape(title)}</title>
<link>{SITE_URL}</link>
<description>{html.escape(description)}</description>
<language>ko</language>
<pubDate>{now}</pubDate>
<atom:link href="{SITE_URL}/{filename}" rel="self" type="application/rss+xml"/>
{items_xml}
</channel>
</rss>'''

# ======================================
# sitemap.xml
# ======================================
def generate_sitemap(all_items):
    urls = [f'''<url><loc>{SITE_URL}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>''']

    # 카테고리
    for cat_name, (slug, name) in CATEGORY_MAP.items():
        urls.append(f'<url><loc>{SITE_URL}/{slug}/</loc><changefreq>daily</changefreq><priority>0.8</priority></url>')

    # 지역
    for sido, slug in REGION_MAP.items():
        urls.append(f'<url><loc>{SITE_URL}/region/{slug}/</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>')

    # 정적
    for p in ['faq/', 'about/', 'privacy/', 'terms/', 'guide/', 'dictionary/']:
        urls.append(f'<url><loc>{SITE_URL}/{p}</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>')

    # 개별 상세
    for item in all_items:
        iid = item.get('internal_id', '')
        sd = item.get('sale_date', '').replace('.', '-')
        urls.append(f'<url><loc>{SITE_URL}/auction/{iid}.html</loc><lastmod>{sd}</lastmod><changefreq>weekly</changefreq><priority>0.6</priority></url>')

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''

# ======================================
# 병렬 HTML 생성
# ======================================
def generate_detail_chunk(chunk_args):
    """청크 단위 상세 HTML 생성 (병렬용)"""
    items, output_dir, worker_id = chunk_args
    count = 0
    for item in items:
        try:
            iid = item['internal_id']
            filepath = os.path.join(output_dir, f'{iid}.html')
            html_content = generate_detail_html(item)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            count += 1
            if count % 500 == 0:
                print(f"  [W{worker_id}] {count}/{len(items)} 완료")
        except Exception as e:
            print(f"  [W{worker_id}] 오류 (ID={item.get('internal_id','?')}): {e}")
    return count

# ======================================
# 메인
# ======================================
def main():
    import time
    start = time.time()
    print("=" * 60)
    print(f"{SITE_NAME} 웹사이트 생성기")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 폴더 생성
    print("\n[1/7] 폴더 생성...")
    os.makedirs(os.path.join(DOCS_DIR, 'auction'), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, 'region'), exist_ok=True)
    for cat_key in ['apartment', 'land', 'commercial', 'other']:
        os.makedirs(os.path.join(DOCS_DIR, cat_key), exist_ok=True)
    for page in ['faq', 'about', 'privacy', 'terms', 'guide', 'dictionary']:
        os.makedirs(os.path.join(DOCS_DIR, page), exist_ok=True)

    # DB 로드
    print("\n[2/7] DB 로드...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM auction_items')
    all_items = [dict(r) for r in c.fetchall()]
    print(f"  {len(all_items):,}건 로드")

    # 입찰이력 로드
    print("  입찰이력 로드...")
    c.execute('SELECT internal_id, bid_round, bid_date, min_bid_price, result, sale_rate FROM auction_bid_history')
    bid_history_map = defaultdict(list)
    for row in c.fetchall():
        r = dict(row)
        iid = r['internal_id']
        bid_history_map[iid].append({
            'bid_round': r.get('bid_round', ''),
            'bid_date': r.get('bid_date', ''),
            'min_bid_price': r.get('min_bid_price', 0),
            'result': r.get('result', ''),
            'sale_info': r.get('sale_rate', ''),
        })
    print(f"  입찰이력: {len(bid_history_map):,}건")

    # 입찰이력을 아이템에 병합
    for item in all_items:
        iid = item['internal_id']
        if iid in bid_history_map:
            item['bid_history'] = json.dumps(bid_history_map[iid], ensure_ascii=False)
        else:
            item['bid_history'] = ''

    # 통계
    stats = defaultdict(int)
    for item in all_items:
        stats[item.get('category', '기타')] += 1
    stats['total'] = len(all_items)
    print(f"  카테고리: {dict(stats)}")

    # JSON 데이터 (목록용)
    print("\n[3/7] data.json 생성...")
    json_items = []
    for item in all_items:
        raw_cn = item.get('case_number', '')
        display_cn = raw_cn.replace('-', '타경', 1) if '-' in raw_cn else raw_cn
        json_items.append({
            'id': item['internal_id'],
            'cn': display_cn,
            'court': item.get('court', ''),
            'cat': item.get('category', ''),
            'addr': item.get('address', ''),
            'ap': item.get('appraisal_price', 0),
            'mp': item.get('min_price', 0),
            'sp': item.get('sale_price', 0),
            'sd': item.get('sale_date', ''),
            'st': item.get('status', ''),
            'sido': item.get('address_sido', ''),
            'sigungu': item.get('address_sigungu', ''),
            'dg': item.get('difficulty_grade', ''),
            'rs': item.get('risk_score', 0),
            'rk': item.get('risk_keywords', ''),
            'mr': item.get('min_rate', ''),
            'it': item.get('item_type', ''),
        })
    with open(os.path.join(DOCS_DIR, 'data.json'), 'w', encoding='utf-8') as f:
        json.dump(json_items, f, ensure_ascii=False)
    print(f"  data.json: {len(json_items):,}건")

    # CSS
    print("\n[4/7] style.css 생성...")
    with open(os.path.join(DOCS_DIR, 'style.css'), 'w', encoding='utf-8') as f:
        f.write(generate_css())

    # 메인 index.html
    print("  index.html 생성...")
    crawl_info = get_crawl_info(conn)
    with open(os.path.join(DOCS_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(generate_index_html(stats, crawl_info))

    # 상세 HTML 병렬 생성
    print(f"\n[5/7] 상세 HTML 병렬 생성 ({len(all_items):,}건)...")
    workers = max(1, cpu_count() - 1)
    chunk_size = len(all_items) // workers + 1
    chunks = []
    for i in range(workers):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, len(all_items))
        if start_idx < len(all_items):
            chunks.append((all_items[start_idx:end_idx], os.path.join(DOCS_DIR, 'auction'), i+1))

    print(f"  {len(chunks)}개 워커로 분할 (각 약 {chunk_size}건)")
    with Pool(len(chunks)) as pool:
        results = pool.map(generate_detail_chunk, chunks)
    total_html = sum(results)
    print(f"  ✅ HTML 생성 완료: {total_html:,}개")

    # 랜딩 페이지
    print("\n[6/7] 랜딩 페이지 생성...")

    # 카테고리별
    cat_items = defaultdict(list)
    for item in all_items:
        cat = item.get('category', '기타')
        if cat in CATEGORY_MAP:
            cat_items[cat].append({
                'id': item['internal_id'],
                'cn': item.get('case_number', ''),
                'court': item.get('court', ''),
                'cat': cat,
                'addr': item.get('address', ''),
                'ap': item.get('appraisal_price', 0),
                'mp': item.get('min_price', 0),
                'sd': item.get('sale_date', ''),
                'st': item.get('status', ''),
            })

    # 랜딩 페이지 사건번호 변환 적용
    for cat_data in cat_items.values():
        for cd in cat_data:
            raw = cd.get('cn', '')
            if '-' in raw:
                cd['cn'] = raw.replace('-', '타경', 1)

    for cat_name, (cat_key, cat_display) in CATEGORY_MAP.items():
        items = cat_items.get(cat_name, [])
        html_content = generate_category_landing(cat_key, cat_display, cat_name, items)
        filepath = os.path.join(DOCS_DIR, cat_key, 'index.html')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  {cat_display}: {len(items):,}건 → /{cat_key}/")

    # 지역별
    sido_items = defaultdict(list)
    for item in all_items:
        sido = item.get('address_sido', '')
        if sido in REGION_MAP:
            sido_items[sido].append({
                'id': item['internal_id'],
                'cn': item.get('case_number', ''),
                'court': item.get('court', ''),
                'cat': item.get('category', ''),
                'addr': item.get('address', ''),
                'ap': item.get('appraisal_price', 0),
                'mp': item.get('min_price', 0),
                'sd': item.get('sale_date', ''),
                'st': item.get('status', ''),
            })

    for sido_data in sido_items.values():
        for sd in sido_data:
            raw = sd.get('cn', '')
            if '-' in raw:
                sd['cn'] = raw.replace('-', '타경', 1)

    for sido, slug in REGION_MAP.items():
        items = sido_items.get(sido, [])
        region_name = REGION_TITLE.get(slug, sido)
        html_content = generate_region_landing(slug, region_name, items)
        filepath = os.path.join(DOCS_DIR, 'region', slug, 'index.html')
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  {region_name}: {len(items):,}건 → /region/{slug}/")

    # 지역별 인덱스 페이지
    region_index_html = generate_region_index_html(sido_items)
    region_index_path = os.path.join(DOCS_DIR, 'region', 'index.html')
    with open(region_index_path, 'w', encoding='utf-8') as f:
        f.write(region_index_html)
    print(f"  지역별 인덱스 → /region/")

    # 정적 페이지
    static_pages = generate_static_pages()
    for path, content in static_pages.items():
        filepath = os.path.join(DOCS_DIR, path)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"  정적 페이지: {len(static_pages)}개")

    # SEO 파일
    print("\n[7/7] SEO 파일 생성...")

    # robots.txt
    robots = f'''User-agent: *
Allow: /
Sitemap: {SITE_URL}/sitemap.xml
'''
    with open(os.path.join(DOCS_DIR, 'robots.txt'), 'w') as f:
        f.write(robots)

    # sitemap.xml
    print("  sitemap.xml 생성...")
    sitemap = generate_sitemap(all_items)
    with open(os.path.join(DOCS_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f"  sitemap.xml: {len(all_items)+30} URLs")

    # RSS feeds
    rss_feeds = [
        ('feed.xml', f'{SITE_NAME} - 전체 경매', '전국 법원 경매 전체', json_items),
        ('feed-new.xml', f'{SITE_NAME} - 신건 경매', '최신 경매 물건', [i for i in json_items if i.get('sd','') >= '2026.04']),
        ('feed-residential.xml', f'{SITE_NAME} - 주거용', '주거용 부동산 경매', [i for i in json_items if i.get('cat') == '주거용 부동산']),
        ('feed-land.xml', f'{SITE_NAME} - 토지', '토지 경매', [i for i in json_items if i.get('cat') == '토지']),
        ('feed-commercial.xml', f'{SITE_NAME} - 상업용', '상업용 부동산 경매', [i for i in json_items if i.get('cat') == '상업용 부동산']),
    ]

    for filename, title, desc, items in rss_feeds:
        rss = generate_rss(items, title, desc, filename)
        with open(os.path.join(DOCS_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(rss)
        print(f"  {filename}: {len(items):,}건")

    conn.close()

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"✅ 완료! 소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print(f"📁 출력: {DOCS_DIR}")
    print(f"📄 HTML: {total_html:,}개")
    print(f"{'='*60}")

# ======================================
# 증분 사이트 생성
# ======================================
def get_crawl_info(conn):
    """crawl_log에서 최신 크롤링 정보 로드"""
    try:
        c = conn.cursor()
        c.execute('SELECT started_at, new_items, updated_items, total_scanned, status FROM crawl_log ORDER BY id DESC LIMIT 1')
        row = c.fetchone()
        if row:
            r = dict(row) if hasattr(row, 'keys') else {'started_at': row[0], 'new_items': row[1], 'updated_items': row[2], 'total_scanned': row[3], 'status': row[4]}
            return {
                'last_crawl': r.get('started_at', '-'),
                'new_items': r.get('new_items', 0),
                'updated_items': r.get('updated_items', 0),
                'total_scanned': r.get('total_scanned', 0),
                'status': r.get('status', '-'),
            }
    except Exception:
        pass
    return None

def generate_incremental(changed_ids=None):
    """변경된 건만 HTML 재생성 + data.json/sitemap/RSS 갱신"""
    import time
    start = time.time()
    print("=" * 60)
    print(f"{SITE_NAME} 증분 사이트 생성기")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 폴더 확인
    auction_dir = os.path.join(DOCS_DIR, 'auction')
    if not os.path.exists(auction_dir):
        os.makedirs(auction_dir, exist_ok=True)

    # DB 로드
    print("\n[1/4] DB 로드...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 변경된 건만 로드 (지정된 ID가 있으면 해당 건만, 없으면 최근 updated_at 기준)
    if changed_ids:
        placeholders = ','.join(['?'] * len(changed_ids))
        c.execute(f'SELECT * FROM auction_items WHERE internal_id IN ({placeholders})', changed_ids)
        changed_items = [dict(r) for r in c.fetchall()]
    else:
        # 기본: 전체 로드 (data.json 등은 전체 필요)
        changed_items = []

    # 전체 아이템 로드 (data.json, sitemap, RSS용)
    c.execute('SELECT * FROM auction_items')
    all_items = [dict(r) for r in c.fetchall()]
    print(f"  전체: {len(all_items):,}건, 변경: {len(changed_items):,}건")

    # 입찰이력 로드
    print("  입찰이력 로드...")
    c.execute('SELECT internal_id, bid_round, bid_date, min_bid_price, result, sale_rate FROM auction_bid_history')
    bid_history_map = defaultdict(list)
    for row in c.fetchall():
        r = dict(row)
        iid = r['internal_id']
        bid_history_map[iid].append({
            'bid_round': r.get('bid_round', ''),
            'bid_date': r.get('bid_date', ''),
            'min_bid_price': r.get('min_bid_price', 0),
            'result': r.get('result', ''),
            'sale_info': r.get('sale_rate', ''),
        })

    # 변경 건에 입찰이력 병합
    for item in changed_items:
        iid = item['internal_id']
        if iid in bid_history_map:
            item['bid_history'] = json.dumps(bid_history_map[iid], ensure_ascii=False)
        else:
            item['bid_history'] = ''

    # 통계
    stats = defaultdict(int)
    for item in all_items:
        stats[item.get('category', '기타')] += 1
    stats['total'] = len(all_items)

    # [2/4] 변경 건 HTML만 재생성
    if changed_items:
        print(f"\n[2/4] 변경 건 HTML 재생성 ({len(changed_items)}건)...")
        html_count = 0
        for item in changed_items:
            try:
                iid = item['internal_id']
                filepath = os.path.join(DOCS_DIR, 'auction', f'{iid}.html')
                html_content = generate_detail_html(item)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                html_count += 1
            except Exception as e:
                print(f"  오류 (ID={item.get('internal_id','?')}): {e}")
        print(f"  ✅ HTML {html_count}개 재생성 완료")
    else:
        print(f"\n[2/4] 변경 건 없음. HTML 생성 건너뜀.")

    # [3/4] data.json 갱신 (항상)
    print("\n[3/4] data.json 갱신...")
    json_items = []
    for item in all_items:
        raw_cn = item.get('case_number', '')
        display_cn = raw_cn.replace('-', '타경', 1) if '-' in raw_cn else raw_cn
        json_items.append({
            'id': item['internal_id'],
            'cn': display_cn,
            'court': item.get('court', ''),
            'cat': item.get('category', ''),
            'addr': item.get('address', ''),
            'ap': item.get('appraisal_price', 0),
            'mp': item.get('min_price', 0),
            'sp': item.get('sale_price', 0),
            'sd': item.get('sale_date', ''),
            'st': item.get('status', ''),
            'sido': item.get('address_sido', ''),
            'sigungu': item.get('address_sigungu', ''),
            'dg': item.get('difficulty_grade', ''),
            'rs': item.get('risk_score', 0),
            'rk': item.get('risk_keywords', ''),
            'mr': item.get('min_rate', ''),
            'it': item.get('item_type', ''),
        })
    with open(os.path.join(DOCS_DIR, 'data.json'), 'w', encoding='utf-8') as f:
        json.dump(json_items, f, ensure_ascii=False)
    print(f"  data.json: {len(json_items):,}건")

    # index.html 갱신 (통계 변경 가능)
    print("  index.html 갱신...")
    crawl_info = get_crawl_info(conn)
    with open(os.path.join(DOCS_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(generate_index_html(stats, crawl_info))

    # [4/4] SEO 파일 갱신
    print("\n[4/4] SEO 파일 갱신...")

    # sitemap.xml
    sitemap = generate_sitemap(all_items)
    with open(os.path.join(DOCS_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap)

    # RSS feeds
    rss_feeds = [
        ('feed.xml', f'{SITE_NAME} - 전체 경매', '전국 법원 경매 전체', json_items),
        ('feed-new.xml', f'{SITE_NAME} - 신건 경매', '최신 경매 물건', [i for i in json_items if i.get('sd','') >= '2026.04']),
        ('feed-residential.xml', f'{SITE_NAME} - 주거용', '주거용 부동산 경매', [i for i in json_items if i.get('cat') == '주거용 부동산']),
        ('feed-land.xml', f'{SITE_NAME} - 토지', '토지 경매', [i for i in json_items if i.get('cat') == '토지']),
        ('feed-commercial.xml', f'{SITE_NAME} - 상업용', '상업용 부동산 경매', [i for i in json_items if i.get('cat') == '상업용 부동산']),
    ]
    for filename, title, desc, items in rss_feeds:
        rss = generate_rss(items, title, desc, filename)
        with open(os.path.join(DOCS_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(rss)

    # 카테고리 랜딩 페이지 갱신
    cat_items = defaultdict(list)
    for item in all_items:
        cat = item.get('category', '기타')
        if cat in CATEGORY_MAP:
            cat_items[cat].append({
                'id': item['internal_id'],
                'cn': item.get('case_number', ''),
                'court': item.get('court', ''),
                'cat': cat,
                'addr': item.get('address', ''),
                'ap': item.get('appraisal_price', 0),
                'mp': item.get('min_price', 0),
                'sd': item.get('sale_date', ''),
                'st': item.get('status', ''),
            })
    for cat_data in cat_items.values():
        for cd in cat_data:
            raw = cd.get('cn', '')
            if '-' in raw:
                cd['cn'] = raw.replace('-', '타경', 1)
    for cat_name, (cat_key, cat_display) in CATEGORY_MAP.items():
        items = cat_items.get(cat_name, [])
        html_content = generate_category_landing(cat_key, cat_display, cat_name, items)
        filepath = os.path.join(DOCS_DIR, cat_key, 'index.html')
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

    # 지역별 인덱스 페이지 갱신
    sido_items = defaultdict(list)
    for item in all_items:
        sido = item.get('address_sido', '')
        if sido in REGION_MAP:
            sido_items[sido].append({'id': item['internal_id']})
    region_index_html = generate_region_index_html(sido_items)
    region_index_path = os.path.join(DOCS_DIR, 'region', 'index.html')
    os.makedirs(os.path.dirname(region_index_path), exist_ok=True)
    with open(region_index_path, 'w', encoding='utf-8') as f:
        f.write(region_index_html)

    conn.close()

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"✅ 증분 생성 완료! 소요: {elapsed:.1f}초")
    print(f"  HTML 재생성: {len(changed_items)}개")
    print(f"  data.json: {len(json_items):,}건")
    print(f"{'='*60}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=f'{SITE_NAME} 사이트 생성기')
    parser.add_argument('--incremental', action='store_true', help='증분 모드 (변경 건만 HTML 재생성)')
    parser.add_argument('--ids', type=str, default='', help='재생성할 ID 목록 (콤마 구분)')
    args = parser.parse_args()

    if args.incremental:
        # --ids 옵션이 있으면 해당 ID 사용, 없으면 changed_ids.json 자동 읽기
        if args.ids:
            changed_ids = [int(x) for x in args.ids.split(',') if x.strip().isdigit()]
        else:
            # data/changed_ids.json에서 자동 로드
            changed_ids_path = os.path.join(BASE_DIR, 'data', 'changed_ids.json')
            if os.path.exists(changed_ids_path):
                with open(changed_ids_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                changed_ids = data.get('ids', [])
                print(f"  📂 changed_ids.json 로드: {len(changed_ids)}건 ({data.get('timestamp','')})")
            else:
                # 파일도 없으면 DB에서 오늘 변경된 건 자동 감지
                print(f"  ⚠️ changed_ids.json 없음. DB에서 오늘 변경 건 자동 감지...")
                changed_ids = None
        generate_incremental(changed_ids)
    else:
        main()
