"""
원스톱 데이터 보완 스크립트
1. 주소 시/군/구 분리 (address_sigungu)
2. 리스크 태깅 재실행 (risk_keywords, risk_score)
3. 낙찰가율 계산 (sale_rate)
4. 건물 스펙 후처리 파싱 (appraisal_report에서 추출)
5. 난이도 등급 산정 (difficulty_grade)
"""
import sqlite3
import re
import json
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'auction.db')

# ========================================
# 1. 주소 시/군/구 분리
# ========================================
SIGUNGU_PATTERNS = [
    # 특별시/광역시 구
    (r'(서울)\s*(\w+구)', '서울'),
    (r'(부산)\s*(\w+구|군)', '부산'),
    (r'(대구)\s*(\w+구|군)', '대구'),
    (r'(인천)\s*(\w+구|군)', '인천'),
    (r'(광주)\s*(\w+구)', '광주'),
    (r'(대전)\s*(\w+구)', '대전'),
    (r'(울산)\s*(\w+구|군)', '울산'),
    (r'(세종)\s*(특별자치시|시)', '세종'),
    # 도 + 시/군/구
    (r'(경기)\s*(\w+시|군)', '경기'),
    (r'(강원)\s*(\w+시|군)', '강원'),
    (r'(충북)\s*(\w+시|군)', '충북'),
    (r'(충남)\s*(\w+시|군)', '충남'),
    (r'(전북)\s*(\w+시|군)', '전북'),
    (r'(전남)\s*(\w+시|군)', '전남'),
    (r'(경북)\s*(\w+시|군)', '경북'),
    (r'(경남)\s*(\w+시|군)', '경남'),
    (r'(제주)\s*(\w+시)', '제주'),
]

# 광역시/특별시 표기 없이 "OO구"로 오는 경우
DIRECT_GU_PATTERNS = [
    (r'^(강남구|강동구|강북구|강서구|관악구|광진구|구로구|금천구|노원구|도봉구|동대문구|동작구|마포구|서대문구|서초구|성동구|성북구|송파구|양천구|영등포구|용산구|은평구|종로구|중구|중랑구)', '서울'),
    (r'^(해운대구|부산진구|동래구|남구|북구|사하구|금정구|연제구|수영구|사상구|기장군|동구|서구|중구|영도구|강서구)', '부산'),
    (r'^(수성구|달서구|달성군|중구|동구|서구|남구|북구|군위군)', '대구'),
    (r'^(계양구|남동구|부평구|서구|연수구|중구|동구|미추홀구|강화군|옹진군)', '인천'),
    (r'^(광산구|남구|동구|북구|서구)', '광주'),
    (r'^(대덕구|동구|서구|유성구|중구)', '대전'),
    (r'^(남구|동구|북구|중구|울주군)', '울산'),
]

# 시/도 표기가 포함된 주소 패턴 (예: "경기 성남시 분당구")
FULL_ADDR_PATTERNS = [
    r'((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)(?:특별시|광역시|특별자치시|도|특별자치도)?)\s*((?:\w+시|구|군)\s*(?:\w+구|읍|면|동)?)',
]


def extract_sigungu(address, address_sido=''):
    """주소에서 시/군/구 추출"""
    if not address:
        return '', ''
    
    # 이미 시/도가 있는 경우
    sido = address_sido or ''
    
    # 광역시/특별시 + 구 패턴 (예: "서울 강남구")
    sido_map_full = {
        '서울': ['서울특별시', '서울'],
        '부산': ['부산광역시', '부산'],
        '대구': ['대구광역시', '대구'],
        '인천': ['인천광역시', '인천'],
        '광주': ['광주광역시', '광주'],
        '대전': ['대전광역시', '대전'],
        '울산': ['울산광역시', '울산'],
        '세종': ['세종특별자치시', '세종'],
        '경기': ['경기도', '경기'],
        '강원': ['강원특별자치도', '강원도', '강원'],
        '충북': ['충청북도', '충북'],
        '충남': ['충청남도', '충남'],
        '전북': ['전북특별자치도', '전라북도', '전북'],
        '전남': ['전라남도', '전남'],
        '경북': ['경상북도', '경북'],
        '경남': ['경상남도', '경남'],
        '제주': ['제주특별자치도', '제주'],
    }
    
    # 주소에서 시/도+시군구 매칭
    for sido_key, patterns in sido_map_full.items():
        for p in patterns:
            # "서울특별시 강남구" 또는 "서울 강남구" 패턴
            m = re.search(re.escape(p) + r'\s*(\w+(?:구|시|군))', address)
            if m:
                sigungu = m.group(1)
                # 구 뒤에 더 상세한 주소가 있으면 구까지만
                if sido_key in ['서울', '부산', '대구', '인천', '광주', '대전', '울산']:
                    # 광역시는 구까지만
                    return sido_key, sigungu
                else:
                    # 도는 시/군/구
                    return sido_key, sigungu
    
    # 시/도만 있고 시군구가 없는 경우 (예: "세종특별자치시 ...")
    for sido_key, patterns in sido_map_full.items():
        for p in patterns:
            if p in address:
                return sido_key, sido_key + '시' if sido_key == '세종' else ''
    
    return sido, ''


def fix_address_sigungu():
    """address_sigungu 컬럼 채우기"""
    print("\n" + "="*60)
    print("1️⃣ 주소 시/군/구 분리 시작")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT internal_id, address, address_sido FROM auction_items WHERE address_sigungu IS NULL OR address_sigungu = \'\'')
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    for internal_id, address, address_sido in rows:
        sido, sigungu = extract_sigungu(address, address_sido)
        
        if sigungu:
            batch.append((sigungu, sido or address_sido, internal_id))
            updated += 1
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET address_sigungu = ?, address_sido = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated:,}건 업데이트...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET address_sigungu = ?, address_sido = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    print(f"  ✅ 완료: {updated:,}건 시/군/구 분리됨")
    
    # 통계
    cursor.execute('SELECT COUNT(*) FROM auction_items WHERE address_sigungu IS NOT NULL AND address_sigungu != \'\'')
    total_filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    print(f"  📊 충족률: {total_filled:,}/{total:,} ({total_filled/total*100:.1f}%)")
    
    conn.close()
    return updated


# ========================================
# 2. 리스크 태깅 재실행
# ========================================
RISK_KEYWORDS = {
    '유치권': 30,
    '법정지상권': 25,
    '위반건축물': 20,
    '지분경매': 15,
    '토지별도등기': 20,
    '농지취득자격': 10,
    '선순위임차인': 25,
    '대항력': 15,
    '공유지분': 15,
    '분묘기지권': 15,
    '맹지': 10,
    '미등기건물': 20,
    '불법증축': 15,
    '도로미접': 15,
}

def fix_risk_tagger():
    """리스크 키워드 분석 재실행"""
    print("\n" + "="*60)
    print("2️⃣ 리스크 태깅 재실행")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 리스크 태깅이 안된 물건 + 기존 태깅된 물건 모두 재분석
    cursor.execute('''
        SELECT internal_id, notes, non_extinguishable_rights, non_extinguishable_easement,
               appraisal_report, status_report
        FROM auction_items
        WHERE detail_scraped = 1
    ''')
    
    items = cursor.fetchall()
    print(f"  대상: {len(items):,}건")
    
    updated_count = 0
    batch = []
    
    for row in items:
        internal_id = row[0]
        notes = row[1] or ""
        rights = row[2] or ""
        easement = row[3] or ""
        appraisal = row[4] or ""
        status_rpt = row[5] or ""
        
        # 더 많은 텍스트 소스 포함
        full_text = f"{notes} {rights} {easement} {appraisal} {status_rpt}"
        
        found_keywords = []
        total_score = 0
        
        for kw, score in RISK_KEYWORDS.items():
            if kw in full_text:
                found_keywords.append(kw)
                total_score += score
        
        # 대항력의 경우 임차인 테이블도 확인
        cursor.execute("SELECT has_opposing_power FROM auction_tenants WHERE internal_id = ?", (internal_id,))
        tenants = cursor.fetchall()
        for t in tenants:
            if t[0] and ('O' in t[0] or '여' in t[0] or '있음' in t[0]):
                if '대항력' not in found_keywords:
                    found_keywords.append('대항력')
                    total_score += RISK_KEYWORDS['대항력']
                break
        
        risk_json = json.dumps(found_keywords, ensure_ascii=False) if found_keywords else None
        batch.append((risk_json, total_score if found_keywords else 0, internal_id))
        
        if found_keywords:
            updated_count += 1
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET risk_keywords = ?, risk_score = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated_count:,}건 리스크 감지...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET risk_keywords = ?, risk_score = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    # 통계
    cursor.execute('SELECT COUNT(*) FROM auction_items WHERE risk_keywords IS NOT NULL AND risk_keywords != \'\' AND risk_keywords != \'[]\'')
    total_filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    
    print(f"  ✅ 완료: {updated_count:,}건에 리스크 키워드 감지됨")
    print(f"  📊 충족률: {total_filled:,}/{total:,} ({total_filled/total*100:.1f}%)")
    
    conn.close()
    return updated_count


# ========================================
# 3. 낙찰가율 계산
# ========================================
def fix_sale_rate():
    """낙찰 건의 낙찰가율 계산"""
    print("\n" + "="*60)
    print("3️⃣ 낙찰가율 계산")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 낙찰 건 (sale_price > 0, appraisal_price > 0) 대상
    cursor.execute('''
        SELECT internal_id, sale_price, appraisal_price
        FROM auction_items
        WHERE sale_price > 0 AND appraisal_price > 0
          AND (sale_rate IS NULL OR sale_rate = '' OR sale_rate = '0')
    ''')
    
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    for internal_id, sale_price, appraisal_price in rows:
        if appraisal_price > 0:
            rate = round(sale_price / appraisal_price * 100, 1)
            batch.append((f'{rate}%', internal_id))
            updated += 1
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET sale_rate = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated:,}건...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET sale_rate = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    # 통계
    cursor.execute("SELECT COUNT(*) FROM auction_items WHERE sale_rate IS NOT NULL AND sale_rate != ''")
    total_filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    
    print(f"  ✅ 완료: {updated:,}건 낙찰가율 계산됨")
    print(f"  📊 충족률: {total_filled:,}/{total:,} ({total_filled/total*100:.1f}%)")
    
    conn.close()
    return updated


# ========================================
# 4. 건물 스펙 후처리 파싱 (appraisal_report에서 추출)
# ========================================
def fix_building_specs():
    """appraisal_report에서 건물 스펙 후처리 추출"""
    print("\n" + "="*60)
    print("4️⃣ 건물 스펙 후처리 파싱")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 건물 스펙이 비어있고 appraisal_report가 있는 물건
    cursor.execute('''
        SELECT internal_id, appraisal_report
        FROM auction_items
        WHERE appraisal_report IS NOT NULL AND appraisal_report != ''
          AND (building_structure IS NULL OR building_structure = '')
    ''')
    
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated_structure = 0
    updated_roof = 0
    updated_floors = 0
    updated_heating = 0
    updated_parking = 0
    updated_elevator = 0
    updated_land_use = 0
    
    batch = []
    
    for internal_id, report_text in rows:
        if not report_text:
            continue
        
        updates = {}
        
        # 건물구조 + 지붕 + 층수 (예: "철근콘크리트조 슬래브지붕 14층 건물 내 10층")
        struct_match = re.search(r'([가-힣]+조)\s+([가-힣]*지붕)?\s*(\d+)층\s*건물\s*내\s*(\d+)층', report_text)
        if struct_match:
            updates['building_structure'] = struct_match.group(1)
            if struct_match.group(2):
                updates['building_roof'] = struct_match.group(2)
            updates['total_floors'] = int(struct_match.group(3))
            updates['target_floor'] = int(struct_match.group(4))
        
        # 구조만 있는 경우 (예: "철근콘크리트조")
        if 'building_structure' not in updates:
            struct_match2 = re.search(r'([가-힣]+(?:조|구조))', report_text[:500] if report_text else '')
            if struct_match2:
                updates['building_structure'] = struct_match2.group(1)
        
        # 난방
        if '개별난방' in report_text:
            updates['heating_type'] = '개별난방'
        elif '중앙난방' in report_text:
            updates['heating_type'] = '중앙난방'
        elif '난방' in report_text:
            heat_match = re.search(r'(\w*난방\w*)', report_text)
            if heat_match:
                updates['heating_type'] = heat_match.group(1)
        
        # 주차
        if '주차장' in report_text or '주차시설' in report_text or '주차가능' in report_text:
            updates['parking_available'] = 1
        
        # 승강기
        if '승강기' in report_text or '엘리베이터' in report_text:
            updates['elevator_available'] = 1
        
        # 토지이용계획
        land_match = re.search(r'8\)\s*토지이용계획.*?=\s*(.*?)(?=\n\n|\n9\)|$)', report_text, re.DOTALL)
        if land_match:
            land_text = land_match.group(1).strip()
            if land_text:
                updates['land_use_plan'] = land_text[:500]  # 너무 길면 자름
        
        if updates:
            batch.append((internal_id, updates))
        
        if len(batch) >= 5000:
            _apply_building_batch(cursor, batch)
            conn.commit()
            print(f"  진행: {len(batch):,}건 처리...")
            batch = []
    
    if batch:
        _apply_building_batch(cursor, batch)
        conn.commit()
    
    # 통계 출력
    for col, label in [
        ('building_structure', '건물구조'),
        ('building_roof', '지붕구조'),
        ('total_floors', '총층수'),
        ('target_floor', '해당층'),
        ('heating_type', '난방방식'),
        ('parking_available', '주차가능'),
        ('elevator_available', '승강기'),
        ('land_use_plan', '토지이용계획'),
    ]:
        cursor.execute(f"SELECT COUNT(*) FROM auction_items WHERE [{col}] IS NOT NULL AND [{col}] != '' AND [{col}] != 0")
        filled = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM auction_items')
        total = cursor.fetchone()[0]
        print(f"  📊 {label} ({col}): {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    
    conn.close()
    return len(batch)


def _apply_building_batch(cursor, batch):
    """건물 스펙 배치 업데이트"""
    for internal_id, updates in batch:
        set_clauses = []
        values = []
        
        for col, val in updates.items():
            if col in ('total_floors', 'target_floor', 'parking_available', 'elevator_available'):
                set_clauses.append(f"{col} = CASE WHEN {col} = 0 OR {col} IS NULL THEN ? ELSE {col} END")
            else:
                set_clauses.append(f"{col} = COALESCE(NULLIF(?, ''), {col})")
            values.append(val)
        
        values.append(internal_id)
        sql = f"UPDATE auction_items SET {', '.join(set_clauses)} WHERE internal_id = ?"
        cursor.execute(sql, values)


# ========================================
# 5. 난이도 등급 산정
# ========================================
def fix_difficulty_grade():
    """물건 난이도 등급 산정"""
    print("\n" + "="*60)
    print("5️⃣ 난이도 등급 산정")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # difficulty_grade 컬럼이 없으면 추가
    try:
        cursor.execute('ALTER TABLE auction_items ADD COLUMN difficulty_grade TEXT')
        conn.commit()
        print("  difficulty_grade 컬럼 추가됨")
    except:
        pass  # 이미 존재
    
    cursor.execute('''
        SELECT a.internal_id, a.risk_score, a.risk_keywords,
               (SELECT COUNT(*) FROM auction_tenants t WHERE t.internal_id = a.internal_id) as tenant_count,
               (SELECT COUNT(*) FROM auction_tenants t WHERE t.internal_id = a.internal_id AND (t.has_opposing_power LIKE '%O%' OR t.has_opposing_power LIKE '%있음%')) as opposing_count
        FROM auction_items a
        WHERE a.detail_scraped = 1
    ''')
    
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    batch = []
    
    for row in rows:
        internal_id = row[0]
        risk_score = row[1] or 0
        risk_keywords = row[2] or '[]'
        tenant_count = row[3] or 0
        opposing_count = row[4] or 0
        
        # 등급 산정
        high_risk_kw = ['유치권', '법정지상권', '미등기건물']
        has_high_risk = any(kw in str(risk_keywords) for kw in high_risk_kw)
        
        if risk_score <= 10 and tenant_count == 0 and not has_high_risk:
            grade = 'A'
        elif risk_score <= 25 and tenant_count <= 1 and opposing_count == 0:
            grade = 'B'
        elif risk_score <= 50 or opposing_count > 0:
            grade = 'C'
        else:
            grade = 'D'
        
        grades[grade] += 1
        batch.append((grade, internal_id))
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET difficulty_grade = ? WHERE internal_id = ?', batch)
            conn.commit()
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET difficulty_grade = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    print(f"  ✅ 등급 분포: A(초보추천)={grades['A']:,} B(보통)={grades['B']:,} C(주의)={grades['C']:,} D(고난도)={grades['D']:,}")
    
    conn.close()


# ========================================
# 메인 실행
# ========================================
if __name__ == '__main__':
    print("🚀 제이옥션 원스톱 데이터 보완 시작!")
    print(f"📁 DB: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ DB 파일 없음: {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    conn.close()
    print(f"📊 총 물건: {total:,}건\n")
    
    # 1. 주소 시/군/구 분리
    fix_address_sigungu()
    
    # 2. 리스크 태깅 재실행
    fix_risk_tagger()
    
    # 3. 낙찰가율 계산
    fix_sale_rate()
    
    # 4. 건물 스펙 후처리
    fix_building_specs()
    
    # 5. 난이도 등급
    fix_difficulty_grade()
    
    print("\n" + "="*60)
    print("🎉 원스톱 데이터 보완 완료!")
    print("="*60)