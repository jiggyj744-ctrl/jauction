#!/usr/bin/env python3
"""
SEO 사이트맵 최적화 시스템 (3개 도메인 지원)
- 카테고리 기반 사이트맵 분할 (키워드 명명)
- Today 사이트맵 (매일 150~200개 순환 노출)
- lastmod 전략적 갱신 (경매임박 > 유찰변경 > 최근등록)
- RSS Feed 최적화 (최근 50개)
- HTML 사이트맵 자동 생성

Usage:
  python seo_sitemap_optimizer.py              # bid (기본)
  python seo_sitemap_optimizer.py --site bid   # bid.recoverylab.co.kr
  python seo_sitemap_optimizer.py --site info  # info.recoverylab.co.kr
  python seo_sitemap_optimizer.py --site a     # a.recoverylab.co.kr
  python seo_sitemap_optimizer.py --site all   # 3개 동시 실행
"""
import sqlite3
import os
import sys
import html
import argparse
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'auction.db')
TODAY_COUNT = 200

# 사이트 설정
SITE_CONFIG = {
    'bid': {
        'name': 'bid.recoverylab.co.kr',
        'domain': 'https://bid.recoverylab.co.kr',
        'output_dir': os.path.join(BASE_DIR, 'docs-bid'),
        'html_subdir': 'auction',
        'title': '경매 낙찰 분석',
        'description': '최신 법원경매 낙찰 분석 정보 - 공장, 상가, 아파트, 토지 경매',
        'use_internal_id': False,  # case_number 기반 파일명
    },
    'info': {
        'name': 'info.recoverylab.co.kr',
        'domain': 'https://info.recoverylab.co.kr',
        'output_dir': os.path.join(BASE_DIR, 'docs'),
        'html_subdir': 'auction',
        'title': '경매 정보',
        'description': '최신 법원경매 정보 - 아파트, 토지, 상업용 부동산 경매',
        'use_internal_id': True,  # internal_id 기반 파일명
    },
    'a': {
        'name': 'a.recoverylab.co.kr',
        'domain': 'https://a.recoverylab.co.kr',
        'output_dir': os.path.join(BASE_DIR, 'docs', 'site1'),
        'html_subdir': 'item',
        'title': '경매 물건 상세',
        'description': '법원경매 물건 상세 정보 - 공장, 상가, 아파트, 토지 경매',
        'use_internal_id': True,  # internal_id 기반 파일명
    },
}

# item_type -> 카테고리 매핑
CATEGORY_MAP = {
    'apartment': {
        'name': '아파트/오피스텔 경매',
        'types': ['아파트', '오피스텔', '아파트형공장'],
        'keywords': 'apartment',
    },
    'residential': {
        'name': '주택/빌라 경매',
        'types': ['주택', '근린주택', '다세대(빌라)', '다가구주택', '도시형생활주택'],
        'keywords': 'residential',
    },
    'commercial': {
        'name': '상가/근린상가 경매',
        'types': ['상가', '근린상가'],
        'keywords': 'commercial',
    },
    'factory': {
        'name': '공장/공장용지 경매',
        'types': ['공장', '공장용지'],
        'keywords': 'factory',
    },
    'land': {
        'name': '토지/대지 경매',
        'types': ['전', '답', '대지', '잡종지', '기타토지', '임야', '과수원', '목장용지', '양어장'],
        'keywords': 'land',
    },
    'building': {
        'name': '건물/시설 경매',
        'types': ['근린시설', '숙박시설', '창고', '자동차관련시설', '종교시설',
                  '교육시설', '병원', '주유소', '주차장', '운동시설', '목욕시설',
                  '장례관련시설', '노유자시설', '펜션(캠핑장)', '콘도(호텔)', '축사(농가시설)'],
        'keywords': 'building',
    },
    'vehicle': {
        'name': '차량/중장비 경매',
        'types': ['차량', '중장비', '선박'],
        'keywords': 'vehicle',
    },
    'other': {
        'name': '기타 경매',
        'types': ['기타', '하천', '도로', '유지', '구거', '어업권', '창고용지', '묘지'],
        'keywords': 'other',
    },
}


def get_type_to_category():
    mapping = {}
    for cat_key, cat_info in CATEGORY_MAP.items():
        for t in cat_info['types']:
            mapping[t] = cat_key
    return mapping


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA encoding = 'UTF-8'")
    return conn


def get_all_bid_items():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT internal_id, case_number, item_type, sale_date, status, fail_count,
               min_price, updated_at, created_at, bid_dday, address
        FROM auction_items
        WHERE detail_scraped = 1
          AND case_number IS NOT NULL
        ORDER BY case_number
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_existing_html_files(config):
    auction_dir = os.path.join(config['output_dir'], config['html_subdir'])
    if not os.path.exists(auction_dir):
        return set()
    files = set()
    for f in os.listdir(auction_dir):
        if f.endswith('.html'):
            files.add(f.replace('.html', ''))
    return files


def build_id_mapping(items, config):
    """internal_id 기반 사이트를 위해 internal_id→item 매핑 구축"""
    if not config.get('use_internal_id'):
        return items  # bid 사이트는 그대로 사용

    # HTML 파일명(internal_id)으로 매핑
    id_map = {}
    for item in items:
        iid = str(item.get('internal_id', ''))
        if iid:
            id_map[iid] = item
    return id_map


def get_item_file_id(item, config):
    """아이템의 파일 식별자 반환 (case_number 또는 internal_id)"""
    if config.get('use_internal_id'):
        return str(item.get('internal_id', ''))
    return item['case_number']


def compute_lastmod(item):
    today = datetime.now()
    bid_dday = item.get('bid_dday')
    if bid_dday is not None:
        try:
            d = int(bid_dday)
            if 0 <= d <= 7:
                return today.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            pass

    fail_count = item.get('fail_count', 0) or 0
    if fail_count > 0:
        updated = item.get('updated_at', '')
        if updated:
            try:
                if isinstance(updated, (int, float)):
                    return datetime.fromtimestamp(updated).strftime('%Y-%m-%d')
                return str(updated)[:10]
            except Exception:
                pass

    created = item.get('created_at', '')
    if created:
        try:
            if isinstance(created, (int, float)):
                created_date = datetime.fromtimestamp(created)
            else:
                created_date = datetime.strptime(str(created)[:10], '%Y-%m-%d')
            if (today - created_date).days <= 30:
                return created_date.strftime('%Y-%m-%d')
        except Exception:
            pass

    if created:
        try:
            if isinstance(created, (int, float)):
                return datetime.fromtimestamp(created).strftime('%Y-%m-%d')
            return str(created)[:10]
        except Exception:
            pass

    return today.strftime('%Y-%m-%d')


def compute_priority(item):
    bid_dday = item.get('bid_dday')
    if bid_dday is not None:
        try:
            d = int(bid_dday)
            if 0 <= d <= 3:
                return '0.9'
            if 4 <= d <= 7:
                return '0.8'
        except Exception:
            pass

    fail_count = item.get('fail_count', 0) or 0
    if fail_count > 0:
        return '0.7'

    return '0.6'


def make_url(case_number, config):
    return config['domain'] + '/' + config['html_subdir'] + '/' + case_number + '.html'


def xml_escape(text):
    if not text:
        return ''
    return html.escape(str(text), quote=True)


def write_xml_sitemap(urls, filepath):
    urlset = Element('urlset')
    urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

    for url_info in urls:
        url_elem = SubElement(urlset, 'url')
        loc = SubElement(url_elem, 'loc')
        loc.text = url_info['loc']
        if url_info.get('lastmod'):
            lm = SubElement(url_elem, 'lastmod')
            lm.text = url_info['lastmod']
        if url_info.get('changefreq'):
            cf = SubElement(url_elem, 'changefreq')
            cf.text = url_info['changefreq']
        if url_info.get('priority'):
            pr = SubElement(url_elem, 'priority')
            pr.text = url_info['priority']

    rough = tostring(urlset, encoding='utf-8')
    pretty = minidom.parseString(rough).toprettyxml(indent='', encoding='utf-8')

    with open(filepath, 'wb') as f:
        f.write(pretty)


def generate_category_sitemaps(items, existing_files, config):
    type_to_cat = get_type_to_category()
    cat_urls = defaultdict(list)
    domain = config['domain']
    sitemaps_dir = os.path.join(config['output_dir'], 'sitemaps')

    for item in items:
        file_id = get_item_file_id(item, config)
        if file_id not in existing_files:
            continue

        cat_key = type_to_cat.get(item.get('item_type', ''), 'other')
        lastmod = compute_lastmod(item)
        priority = compute_priority(item)

        url_info = {
            'loc': make_url(file_id, config),
            'lastmod': lastmod,
            'changefreq': 'weekly',
            'priority': priority,
        }
        cat_urls[cat_key].append(url_info)

    os.makedirs(sitemaps_dir, exist_ok=True)

    sitemap_files = []

    for cat_key, cat_info in CATEGORY_MAP.items():
        urls = cat_urls.get(cat_key, [])
        if not urls:
            continue

        chunk_idx = 1
        for i in range(0, len(urls), 1000):
            chunk = urls[i:i + 1000]
            if len(urls) <= 1000:
                filename = 'sitemap-' + cat_info['keywords'] + '.xml'
            else:
                filename = 'sitemap-' + cat_info['keywords'] + '-' + str(chunk_idx) + '.xml'

            filepath = os.path.join(sitemaps_dir, filename)
            write_xml_sitemap(chunk, filepath)
            sitemap_files.append({
                'filename': filename,
                'url': domain + '/sitemaps/' + filename,
                'count': len(chunk),
                'category': cat_info['name'],
            })
            chunk_idx += 1
            print('  ' + filename + ': ' + str(len(chunk)) + ' URL (' + cat_info['name'] + ')')

    return sitemap_files


def generate_today_sitemap(items, existing_files, config):
    today = datetime.now()
    domain = config['domain']
    sitemaps_dir = os.path.join(config['output_dir'], 'sitemaps')

    valid_items = []
    for item in items:
        file_id = get_item_file_id(item, config)
        if file_id in existing_files:
            valid_items.append(item)

    if not valid_items:
        return None

    def sort_key(item):
        bid_dday = item.get('bid_dday')
        if bid_dday is not None:
            try:
                d = int(bid_dday)
                if 0 <= d <= 7:
                    return (0, d)
            except Exception:
                pass

        fail_count = item.get('fail_count', 0) or 0
        if fail_count > 0:
            return (1, -fail_count)

        return (2, 0)

    valid_items.sort(key=sort_key)

    priority_items = valid_items[:100]

    day_seed = int(today.strftime('%Y%m%d'))
    general_items = valid_items[100:]

    if general_items:
        start_idx = day_seed % len(general_items)
        cycle_items = []
        for i in range(min(TODAY_COUNT - len(priority_items), len(general_items))):
            idx = (start_idx + i) % len(general_items)
            cycle_items.append(general_items[idx])
        selected = priority_items + cycle_items
    else:
        selected = priority_items[:TODAY_COUNT]

    urls = []
    for item in selected:
        urls.append({
            'loc': make_url(get_item_file_id(item, config), config),
            'lastmod': today.strftime('%Y-%m-%d'),
            'changefreq': 'daily',
            'priority': compute_priority(item),
        })

    os.makedirs(sitemaps_dir, exist_ok=True)
    filepath = os.path.join(sitemaps_dir, 'sitemap-today.xml')
    write_xml_sitemap(urls, filepath)

    print('  sitemap-today.xml: ' + str(len(urls)) + ' URL')
    return {
        'filename': 'sitemap-today.xml',
        'url': domain + '/sitemaps/sitemap-today.xml',
        'count': len(urls),
        'category': '오늘의 추천',
    }


def generate_sitemap_index(sitemap_files, today_file, config):
    domain = config['domain']
    output_dir = config['output_dir']

    index = Element('sitemapindex')
    index.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

    all_files = []
    if today_file:
        all_files.append(today_file)
    all_files.extend(sitemap_files)

    today_str = datetime.now().strftime('%Y-%m-%d')

    for sf in all_files:
        sitemap = SubElement(index, 'sitemap')
        loc = SubElement(sitemap, 'loc')
        loc.text = sf['url']
        lastmod = SubElement(sitemap, 'lastmod')
        lastmod.text = today_str

    rough = tostring(index, encoding='utf-8')
    pretty = minidom.parseString(rough).toprettyxml(indent='\t', encoding='utf-8')

    filepath = os.path.join(output_dir, 'sitemap-index.xml')
    with open(filepath, 'wb') as f:
        f.write(pretty)

    print('  sitemap-index.xml: ' + str(len(all_files)) + ' sub-sitemaps')


def generate_main_sitemap(config):
    domain = config['domain']
    output_dir = config['output_dir']
    filepath = os.path.join(output_dir, 'sitemap.xml')
    today_str = datetime.now().strftime('%Y-%m-%d')
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '<sitemap><loc>' + domain + '/sitemap-index.xml</loc><lastmod>' + today_str + '</lastmod></sitemap>',
        '</sitemapindex>',
    ]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('  sitemap.xml updated')


def update_robots_txt(config):
    domain = config['domain']
    output_dir = config['output_dir']
    filepath = os.path.join(output_dir, 'robots.txt')
    lines = [
        'User-agent: *',
        'Allow: /',
        'Crawl-delay: 1',
        '',
        '# Sitemap',
        'Sitemap: ' + domain + '/sitemap-index.xml',
        '',
    ]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('  robots.txt updated')


def generate_rss_feed(items, existing_files, config):
    domain = config['domain']
    output_dir = config['output_dir']
    today = datetime.now()

    valid_items = []
    for i in items:
        file_id = get_item_file_id(i, config)
        if file_id in existing_files:
            valid_items.append(i)

    def sort_key(item):
        bid_dday = item.get('bid_dday')
        if bid_dday is not None:
            try:
                d = int(bid_dday)
                if 0 <= d <= 7:
                    return (0, d)
            except Exception:
                pass
        return (1, 0)

    valid_items.sort(key=sort_key)
    recent_50 = valid_items[:50]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        '<channel>',
        '<title>' + xml_escape(config['title'] + ' - ' + config['name']) + '</title>',
        '<link>' + domain + '</link>',
        '<description>' + xml_escape(config['description']) + '</description>',
        '<language>ko</language>',
        '<lastBuildDate>' + today.strftime('%a, %d %b %Y %H:%M:%S +0900') + '</lastBuildDate>',
        '<atom:link href="' + domain + '/feed.xml" rel="self" type="application/rss+xml"/>',
    ]

    for item in recent_50:
        cn = get_item_file_id(item, config)
        addr = item.get('address', '') or '경매 물건'
        item_type = item.get('item_type', '')
        min_price = item.get('min_price', '')
        if isinstance(min_price, (int, float)) and min_price:
            price_str = format(min_price, ',.0f') + '원'
        else:
            price_str = ''

        title = '[' + item_type + '] ' + addr
        if price_str:
            title = title + ' - ' + price_str

        link = make_url(cn, config)
        pub_date = compute_lastmod(item)

        lines.append('<item>')
        lines.append('<title>' + xml_escape(title) + '</title>')
        lines.append('<link>' + xml_escape(link) + '</link>')
        desc = item_type + ' 경매 - ' + addr + ' ' + price_str
        lines.append('<description>' + xml_escape(desc) + '</description>')
        lines.append('<pubDate>' + pub_date + '</pubDate>')
        lines.append('<guid>' + xml_escape(link) + '</guid>')
        lines.append('</item>')

    lines.append('</channel>')
    lines.append('</rss>')

    filepath = os.path.join(output_dir, 'feed.xml')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print('  feed.xml: ' + str(len(recent_50)) + ' items (RSS)')


def generate_html_sitemap(items, existing_files, config):
    type_to_cat = get_type_to_category()
    cat_items = defaultdict(list)
    domain = config['domain']
    output_dir = config['output_dir']

    for item in items:
        file_id = get_item_file_id(item, config)
        if file_id not in existing_files:
            continue
        cat_key = type_to_cat.get(item.get('item_type', ''), 'other')
        cat_items[cat_key].append(item)

    today_str = datetime.now().strftime('%Y-%m-%d')
    total_count = len([i for i in items if get_item_file_id(i, config) in existing_files])

    parts = []
    parts.append('<!DOCTYPE html>')
    parts.append('<html lang="ko">')
    parts.append('<head>')
    parts.append('<meta charset="UTF-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    parts.append('<title>사이트맵 - 경매 물건 카테고리 | ' + config['name'] + '</title>')
    parts.append('<meta name="description" content="법원경매 물건 카테고리별 사이트맵">')
    parts.append('<meta name="robots" content="index, follow">')
    parts.append('<link rel="canonical" href="' + domain + '/sitemap-page.html">')
    parts.append('</head>')
    parts.append('<body style="font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5;">')
    parts.append('<header style="background: #1a237e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">')
    parts.append('<h1>경매 물건 사이트맵</h1>')
    parts.append('<p style="color: #bbdefb;">총 ' + str(total_count) + '건 경매 물건 | 업데이트: ' + today_str + '</p>')
    parts.append('</header>')

    for cat_key, cat_info in CATEGORY_MAP.items():
        cat_item_list = cat_items.get(cat_key, [])
        if not cat_item_list:
            continue

        parts.append('<div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 15px;">')
        parts.append('<h2 style="color: #1a237e; border-bottom: 2px solid #e8eaf6; padding-bottom: 10px;">')
        parts.append(xml_escape(cat_info['name']) + ' (' + str(len(cat_item_list)) + '건)')
        parts.append('</h2>')
        parts.append('<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px;">')

        for item in cat_item_list[:50]:
            file_id = get_item_file_id(item, config)
            addr = item.get('address', '') or item['case_number']
            min_price = item.get('min_price', '')
            if isinstance(min_price, (int, float)) and min_price:
                price_str = format(min_price, ',.0f') + '원'
            else:
                price_str = ''

            href = '/' + config['html_subdir'] + '/' + xml_escape(file_id) + '.html'
            label = xml_escape(addr[:30])
            if price_str:
                label = label + ' <small style="color:#e53935;">' + price_str + '</small>'
            parts.append('<a href="' + href + '" style="display:block; padding:8px 12px; background:#f8f9fa; border-radius:4px; text-decoration:none; color:#333; border-left:3px solid #1a237e;">' + label + '</a>')

        if len(cat_item_list) > 50:
            parts.append('<p style="color:#666; padding:8px;">... 외 ' + str(len(cat_item_list) - 50) + '건 더보기</p>')

        parts.append('</div></div>')

    parts.append('<footer style="text-align:center; padding:20px; color:#666; margin-top:20px;">')
    parts.append('<p>법원경매 정보 서비스 | <a href="' + domain + '">' + config['name'] + '</a></p>')
    parts.append('<p><small>이 사이트는 참고 자료이며, 투자 권고가 아닙니다.</small></p>')
    parts.append('</footer>')
    parts.append('</body>')
    parts.append('</html>')

    filepath = os.path.join(output_dir, 'sitemap-page.html')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))

    print('  sitemap-page.html: HTML sitemap generated')


def run_for_site(site_key):
    config = SITE_CONFIG[site_key]
    domain = config['domain']
    site_name = config['name']

    print('\n' + '=' * 60)
    print('SEO Sitemap Optimizer - ' + site_name)
    print('  Run: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print('  Output: ' + config['output_dir'])
    print('=' * 60)

    print('\nFetching items from DB...')
    items = get_all_bid_items()
    print('  Total: ' + str(len(items)))

    print('Checking HTML files...')
    existing = get_existing_html_files(config)
    print('  HTML files: ' + str(len(existing)))

    if not existing:
        print('  ⚠️ HTML 파일이 없습니다. 건너뜁니다.')
        return False

    print('\nGenerating category sitemaps...')
    sitemap_files = generate_category_sitemaps(items, existing, config)

    print('\nGenerating today sitemap...')
    today_file = generate_today_sitemap(items, existing, config)

    print('\nGenerating sitemap index...')
    generate_sitemap_index(sitemap_files, today_file, config)

    generate_main_sitemap(config)

    print('\nUpdating robots.txt...')
    update_robots_txt(config)

    print('\nGenerating RSS feed...')
    generate_rss_feed(items, existing, config)

    print('\nGenerating HTML sitemap...')
    generate_html_sitemap(items, existing, config)

    total = sum(sf['count'] for sf in sitemap_files)
    today_count = today_file['count'] if today_file else 0
    print('\n' + '-' * 60)
    print('DONE - ' + site_name)
    print('  Category sitemaps: ' + str(len(sitemap_files)) + ' files (' + str(total) + ' URLs)')
    print('  Today sitemap: ' + str(today_count) + ' URLs')
    print('  RSS Feed: 50 items')
    print('-' * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description='SEO 사이트맵 최적화')
    parser.add_argument('--site', default='bid', choices=['bid', 'info', 'a', 'all'],
                        help='대상 사이트 (bid, info, a, all)')
    args = parser.parse_args()

    if args.site == 'all':
        sites = ['bid', 'info', 'a']
    else:
        sites = [args.site]

    for site_key in sites:
        run_for_site(site_key)

    print('\n' + '=' * 60)
    print('ALL DONE! Sites processed: ' + ', '.join(sites))
    print('=' * 60)


if __name__ == '__main__':
    main()