"""
경매 데이터 SQLite DB 초기 설정 v2
- 물건종류 코드 체계 포함
- 리스트 + 상세 통합 테이블
- 이미지 테이블 (로컬 경로)
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'auction.db')

# 물건종류 코드 매핑
ITEM_TYPE_MAP = {
    # 주거용 부동산 (1xx)
    '101': '아파트', '102': '주택', '103': '다세대(빌라)', '104': '다가구주택',
    '105': '근린주택', '106': '오피스텔', '107': '도시형생활주택',
    # 상업용 부동산 (2xx)
    '201': '근린시설', '202': '근린상가', '203': '상가', '204': '공장',
    '205': '아파트형공장', '206': '숙박시설', '207': '주유소', '208': '병원',
    '209': '아파트상가', '210': '창고', '211': '목욕시설', '212': '콘도(호텔)',
    '213': '운동시설', '214': '휴게시설', '215': '노유자시설', '216': '자동차관련시설',
    '217': '펜션(캠핑장)', '218': '교육시설', '219': '장례관련시설',
    # 토지 (3xx)
    '301': '대지', '302': '임야', '303': '전', '304': '답', '305': '과수원',
    '306': '잡종지', '307': '공장용지', '308': '도로', '309': '목장용지',
    '310': '창고용지', '311': '유지', '312': '하천', '313': '구거',
    '314': '기타토지', '404': '주차장', '405': '묘지',
    # 기타 (4xx)
    '401': '축사(농가시설)', '403': '학교', '406': '광업권', '407': '어업권',
    '408': '양어장', '409': '종교시설', '410': '기타', '411': '선박',
    '412': '차량', '413': '중장비',
}

# 대분류 매핑
CATEGORY_MAP = {
    '주거용 부동산': ['101','102','103','104','105','106','107'],
    '상업용 부동산': ['201','202','203','204','205','206','207','208','209','210','211','212','213','214','215','216','217','218','219'],
    '토지': ['301','302','303','304','305','306','307','308','309','310','311','312','313','314','404','405'],
    '기타': ['401','403','406','407','408','409','410','411','412','413'],
}

def init_db(drop=False):
    """DB 테이블 생성/초기화 (drop=True면 기존 데이터 삭제)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if drop:
        # 기존 테이블 삭제 (깨끗하게 재시작)
        cursor.execute('DROP TABLE IF EXISTS auction_items')
        cursor.execute('DROP TABLE IF EXISTS auction_bid_history')
        cursor.execute('DROP TABLE IF EXISTS auction_images')
    
    # 1. 메인 물건 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auction_items (
            internal_id INTEGER PRIMARY KEY,
            case_number TEXT,
            case_year TEXT,
            case_seq TEXT,
            court TEXT,
            court_code TEXT,
            item_type_code TEXT,
            item_type TEXT,
            category TEXT,
            address TEXT,
            address_sido TEXT,
            address_sigungu TEXT,
            -- 가격 정보
            appraisal_price INTEGER DEFAULT 0,
            min_price INTEGER DEFAULT 0,
            sale_price INTEGER DEFAULT 0,
            min_rate TEXT,
            sale_rate TEXT,
            claim_amount INTEGER DEFAULT 0,
            deposit INTEGER DEFAULT 0,
            deposit_rate TEXT,
            -- 날짜/상태
            sale_date TEXT,
            status TEXT,
            fail_count INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            -- 경매 정보
            auction_type TEXT,
            creditor TEXT,
            debtor TEXT,
            owner TEXT,
            -- 면적
            land_area TEXT,
            building_area TEXT,
            -- 상세 설명
            summary TEXT,
            notes TEXT,
            related_case TEXT,
            tenant_info TEXT,
            non_extinguishable_rights TEXT,
            non_extinguishable_easement TEXT,
            -- 차량 정보
            vehicle_name TEXT,
            vehicle_year TEXT,
            vehicle_maker TEXT,
            vehicle_fuel TEXT,
            vehicle_transmission TEXT,
            vehicle_reg_number TEXT,
            vehicle_engine_type TEXT,
            vehicle_mileage TEXT,
            vehicle_displacement TEXT,
            vehicle_approval_number TEXT,
            vehicle_vin TEXT,
            vehicle_storage TEXT,
            -- 통계
            stats_3m TEXT,
            stats_6m TEXT,
            stats_12m TEXT,
            -- 사진
            thumbnail_url TEXT,
            photo_urls TEXT,
            -- 메타
            detail_scraped INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', '+9 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+9 hours'))
        )
    ''')
    
    # 2. 입찰 이력 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auction_bid_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            internal_id INTEGER,
            bid_round TEXT,
            bid_date TEXT,
            min_bid_price INTEGER DEFAULT 0,
            result TEXT,
            sale_price INTEGER DEFAULT 0,
            sale_rate TEXT,
            FOREIGN KEY (internal_id) REFERENCES auction_items(internal_id)
        )
    ''')
    
    # 3. 이미지 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auction_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            internal_id INTEGER,
            image_url TEXT,
            image_order INTEGER DEFAULT 0,
            local_path TEXT,
            downloaded INTEGER DEFAULT 0,
            FOREIGN KEY (internal_id) REFERENCES auction_items(internal_id)
        )
    ''')
    
    # 4. 크롤링 로그 테이블 (증분 크롤링용)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crawl_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_type TEXT,
            started_at TEXT,
            finished_at TEXT,
            new_items INTEGER DEFAULT 0,
            updated_items INTEGER DEFAULT 0,
            total_scanned INTEGER DEFAULT 0,
            detail_scraped INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            error_message TEXT
        )
    ''')
    
    # 5. 변경 이력 테이블 (어떤 물건이 어떻게 변경되었는지 추적)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS item_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            internal_id INTEGER,
            change_type TEXT,
            old_value TEXT,
            new_value TEXT,
            changed_at TEXT DEFAULT (datetime('now', '+9 hours')),
            FOREIGN KEY (internal_id) REFERENCES auction_items(internal_id)
        )
    ''')
    
    # 인덱스
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_case ON auction_items(case_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_court ON auction_items(court)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_type ON auction_items(item_type_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_category ON auction_items(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_status ON auction_items(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_date ON auction_items(sale_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_sido ON auction_items(address_sido)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_updated ON auction_items(updated_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bid_internal ON auction_bid_history(internal_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_img_internal ON auction_images(internal_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_internal ON item_changes(internal_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_type ON item_changes(change_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_date ON item_changes(changed_at)')
    
    conn.commit()
    conn.close()
    print(f"✅ DB 초기화 완료: {DB_PATH}")

def get_item_type_name(code):
    """코드로 물건종류명 반환"""
    return ITEM_TYPE_MAP.get(str(code), '')

def get_category(item_type_code):
    """물건종류코드로 대분류 반환"""
    code = str(item_type_code)
    for cat, codes in CATEGORY_MAP.items():
        if code in codes:
            return cat
    return '기타'

if __name__ == '__main__':
    init_db()
    print(f"물건종류 코드 수: {len(ITEM_TYPE_MAP)}")
    print(f"대분류: {list(CATEGORY_MAP.keys())}")