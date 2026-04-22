"""
증분 데이터 보완 스크립트
- data/changed_ids.json의 변경 건만 후처리
- fix_all.py + fix_all_extra.py의 로직을 증분으로 실행
- 매일 update_daily.bat에서 호출

처리 항목:
1. 주소 시/군/구 분리 (address_sigungu)
2. 리스크 태깅 (risk_keywords, risk_score)
3. 낙찰가율 계산 (sale_rate)
4. 건물 스펙 파싱 (building_structure 등)
5. 난이도 등급 (difficulty_grade)
6. 토지이용계획, 지붕, 층수, 도로접면, 사용승인일, 세대수, 점유현황, 주차
"""
import sqlite3
import re
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'auction.db')
CHANGED_IDS_PATH = os.path.join(BASE_DIR, 'data', 'changed_ids.json')


def load_changed_ids():
    """changed_ids.json에서 변경된 ID 목록 로드"""
    if not os.path.exists(CHANGED_IDS_PATH):
        return []
    with open(CHANGED_IDS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('ids', [])


# ========================================
# 1. 주소 시/군/구 분리
# ========================================
def fix_address_sigungu(conn, ids):
    """변경 건의 address_sigungu 업데이트"""
    if not ids:
        return 0

    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'''
        SELECT internal_id, address, address_sido FROM auction_items
        WHERE internal_id IN ({placeholders})
          AND (address_sigungu IS NULL OR address_sigungu = '')
    ''', ids)
    rows = cursor.fetchall()

    sido_map = {
        '서울': ['서울특별시', '서울'], '부산': ['부산광역시', '부산'],
        '대구': ['대구광역시', '대구'], '인천': ['인천광역시', '인천'],
        '광주': ['광주광역시', '광주'], '대전': ['대전광역시', '대전'],
        '울산': ['울산광역시', '울산'], '세종': ['세종특별자치시', '세종'],
        '경기': ['경기도', '경기'], '강원': ['강원특별자치도', '강원도', '강원'],
        '충북': ['충청북도', '충북'], '충남': ['충청남도', '충남'],
        '전북': ['전북특별자치도', '전라북도', '전북'], '전남': ['전라남도', '전남'],
        '경북': ['경상북도', '경북'], '경남': ['경상남도', '경남'],
        '제주': ['제주특별자치도', '제주'],
    }

    updated = 0
    for internal_id, address, address_sido in rows:
        sido = address_sido or ''
        sigungu = ''

        for sido_key, patterns in sido_map.items():
            for p in patterns:
                m = re.search(re.escape(p) + r'\s*(\w+(?:구|시|군))', address or '')
                if m:
                    sigungu = m.group(1)
                    sido = sido_key
                    break
            if sigungu:
                break

        if sigungu:
            cursor.execute('UPDATE auction_items SET address_sigungu = ?, address_sido = ? WHERE internal_id = ?',
                         (sigungu, sido, internal_id))
            updated += 1

    conn.commit()
    print(f"  ✅ 시/군/구: {updated}/{len(rows)}건 업데이트")
    return updated


# ========================================
# 2. 리스크 태깅
# ========================================
RISK_KEYWORDS = {
    '유치권': 30, '법정지상권': 25, '위반건축물': 20, '지분경매': 15,
    '토지별도등기': 20, '농지취득자격': 10, '선순위임차인': 25, '대항력': 15,
    '공유지분': 15, '분묘기지권': 15, '맹지': 10, '미등기건물': 20,
    '불법증축': 15, '도로미접': 15,
}

def fix_risk_tagger(conn, ids):
    """변경 건의 리스크 태깅"""
    if not ids:
        return 0

    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'''
        SELECT internal_id, notes, non_extinguishable_rights, non_extinguishable_easement,
               appraisal_report, status_report
        FROM auction_items
        WHERE internal_id IN ({placeholders}) AND detail_scraped = 1
    ''', ids)
    rows = cursor.fetchall()

    updated = 0
    for row in rows:
        internal_id = row[0]
        full_text = ' '.join(str(r or '') for r in row[1:])

        found = []
        score = 0
        for kw, s in RISK_KEYWORDS.items():
            if kw in full_text:
                found.append(kw)
                score += s

        # 임차인 테이블에서 대항력 확인
        cursor.execute("SELECT has_opposing_power FROM auction_tenants WHERE internal_id = ?", (internal_id,))
        for t in cursor.fetchall():
            if t[0] and ('O' in t[0] or '여' in t[0] or '있음' in t[0]):
                if '대항력' not in found:
                    found.append('대항력')
                    score += RISK_KEYWORDS['대항력']

        risk_json = json.dumps(found, ensure_ascii=False) if found else None
        cursor.execute('UPDATE auction_items SET risk_keywords = ?, risk_score = ? WHERE internal_id = ?',
                      (risk_json, score if found else 0, internal_id))
        if found:
            updated += 1

    conn.commit()
    print(f"  ✅ 리스크 태깅: {updated}/{len(rows)}건 감지")
    return updated


# ========================================
# 3. 낙찰가율 계산
# ========================================
def fix_sale_rate(conn, ids):
    """변경 건의 낙찰가율 계산"""
    if not ids:
        return 0

    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'''
        SELECT internal_id, sale_price, appraisal_price
        FROM auction_items
        WHERE internal_id IN ({placeholders})
          AND sale_price > 0 AND appraisal_price > 0
          AND (sale_rate IS NULL OR sale_rate = '' OR sale_rate = '0')
    ''', ids)
    rows = cursor.fetchall()

    updated = 0
    for internal_id, sale_price, appraisal_price in rows:
        if appraisal_price > 0:
            rate = round(sale_price / appraisal_price * 100, 1)
            cursor.execute('UPDATE auction_items SET sale_rate = ? WHERE internal_id = ?',
                          (f'{rate}%', internal_id))
            updated += 1

    conn.commit()
    print(f"  ✅ 낙찰가율: {updated}/{len(rows)}건 계산")
    return updated


# ========================================
# 4. 건물 스펙 + 추가 파싱 (통합)
# ========================================
def fix_building_and_extras(conn, ids):
    """변경 건의 건물스펙, 토지이용계획, 도로, 승인일, 세대수, 점유, 주차 통합 처리"""
    if not ids:
        return 0

    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'''
        SELECT internal_id, appraisal_report, status_report
        FROM auction_items
        WHERE internal_id IN ({placeholders})
          AND appraisal_report IS NOT NULL AND appraisal_report != ''
    ''', ids)
    rows = cursor.fetchall()

    stats = {'structure': 0, 'roof': 0, 'floors': 0, 'heating': 0,
             'land_use': 0, 'road': 0, 'approval': 0, 'households': 0,
             'parking': 0, 'elevator': 0, 'occupancy': 0}

    for internal_id, report, status_report in rows:
        updates = {}

        # 건물구조 + 지붕 + 층수
        m = re.search(r'([가-힣]+조)\s+([가-힣]*지붕)?\s*(\d+)\s*층\s*건물\s*내\s*(\d+)\s*층', report)
        if m:
            updates['building_structure'] = m.group(1)
            if m.group(2):
                updates['building_roof'] = m.group(2)
            updates['total_floors'] = int(m.group(3))
            updates['target_floor'] = int(m.group(4))
        else:
            # 구조만
            m2 = re.search(r'([가-힣]+(?:조|구조))', report[:500])
            if m2:
                updates['building_structure'] = m2.group(1)

            # 층수만
            m3 = re.search(r'(\d+)\s*층\s*건물\s*내\s*(\d+)\s*층', report)
            if m3:
                updates['total_floors'] = int(m3.group(1))
                updates['target_floor'] = int(m3.group(2))
            else:
                m4 = re.search(r'지상\s*(\d+)\s*층', report)
                if m4:
                    updates['total_floors'] = int(m4.group(1))

        # 지붕 (별도 패턴)
        if 'building_roof' not in updates:
            for pat in [r'([가-힣]+지붕)', r'지붕\s*[:=]\s*([가-힣]+)']:
                m = re.search(pat, report)
                if m:
                    updates['building_roof'] = m.group(1)
                    break

        # 난방
        for ht in ['개별난방', '중앙난방']:
            if ht in report:
                updates['heating_type'] = ht
                break

        # 토지이용계획
        for pat in [
            r'8\)\s*토지이용계획\s*=\s*(.*?)(?=\n\n|\n9\)|$)',
            r'토지이용계획[^\n]*\n?\s*(.*?)(?=\n\n|\n\d+\)|$)',
            r'(?:용도지역|지역지구)\s*[:=]?\s*(.*?)(?=\n\n|\n\d+\)|$)',
        ]:
            m = re.search(pat, report, re.DOTALL)
            if m and m.group(1).strip():
                updates['land_use_plan'] = m.group(1).strip()[:500]
                break

        # 도로접면
        for pat in [
            r'(?:도로에?\s*(?:접|면)\s*|접도로\s*|도로접면\s*)[:=]?\s*(\d+\.?\d*)\s*m',
            r'(\d+\.?\d*)\s*m\s*도로에?\s*접',
        ]:
            m = re.search(pat, report)
            if m:
                updates['road_access'] = f'{m.group(1)}m'
                break

        # 사용승인일
        for pat in [
            r'사용승인일?\s*[:=]?\s*(\d{4}[\./-]\d{1,2}[\./-]\d{1,2})',
            r'사용검사일?\s*[:=]?\s*(\d{4}[\./-]\d{1,2}[\./-]\d{1,2})',
            r'사용승인\s*.*?(\d{4}[\./]\d{1,2}[\./]\d{1,2})',
            r'준공일?\s*[:=]?\s*(\d{4}[\./-]\d{1,2}[\./-]\d{1,2})',
        ]:
            m = re.search(pat, report)
            if m:
                updates['approval_date'] = m.group(1).replace('.', '-').replace('/', '-')
                break

        # 세대수
        for pat in [r'총\s*(\d+)\s*세대', r'(\d+)\s*세대\s*(?:주택|아파트|오피스텔)', r'세대수\s*[:=]?\s*(\d+)']:
            m = re.search(pat, report)
            if m and 0 < int(m.group(1)) < 10000:
                updates['total_households'] = int(m.group(1))
                break

        # 주차
        if '주차' in report or '차고' in report:
            updates['parking_available'] = 1

        # 승강기
        if '승강기' in report or '엘리베이터' in report:
            updates['elevator_available'] = 1

        # 점유현황 (status_report에서)
        if status_report:
            if '공실' in status_report:
                updates['occupancy_status'] = '공실'
            elif '자택거주' in status_report:
                updates['occupancy_status'] = '소유자 거주'
            elif '임대차' in status_report:
                m = re.search(r'임대차.*?보증금\s*([0-9,]+)', status_report)
                updates['occupancy_status'] = '임대차' + (f' (보증금 {m.group(1)})' if m else '')
            elif '거주' in status_report:
                updates['occupancy_status'] = '거주'
            elif '점유' in status_report:
                updates['occupancy_status'] = '점유'

        # DB 업데이트
        if updates:
            set_clauses = []
            values = []
            for col, val in updates.items():
                if col in ('total_floors', 'target_floor', 'parking_available', 'elevator_available', 'total_households'):
                    set_clauses.append(f"{col} = CASE WHEN COALESCE({col}, 0) = 0 THEN ? ELSE {col} END")
                else:
                    set_clauses.append(f"{col} = COALESCE(NULLIF(?, ''), {col})")
                values.append(val)

                # 통계 카운트
                col_map = {
                    'building_structure': 'structure', 'building_roof': 'roof',
                    'total_floors': 'floors', 'heating_type': 'heating',
                    'land_use_plan': 'land_use', 'road_access': 'road',
                    'approval_date': 'approval', 'total_households': 'households',
                    'parking_available': 'parking', 'elevator_available': 'elevator',
                    'occupancy_status': 'occupancy',
                }
                if col in col_map:
                    stats[col_map[col]] += 1

            values.append(internal_id)
            sql = f"UPDATE auction_items SET {', '.join(set_clauses)} WHERE internal_id = ?"
            cursor.execute(sql, values)

    conn.commit()
    print(f"  ✅ 건물/추가 파싱: {len(rows)}건 처리")
    for k, v in stats.items():
        if v > 0:
            print(f"     - {k}: {v}건")
    return len(rows)


# ========================================
# 5. 난이도 등급
# ========================================
def fix_difficulty_grade(conn, ids):
    """변경 건의 난이도 등급 산정"""
    if not ids:
        return 0

    cursor = conn.cursor()

    # 컬럼 존재 확인
    try:
        cursor.execute('ALTER TABLE auction_items ADD COLUMN difficulty_grade TEXT')
        conn.commit()
    except:
        pass

    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'''
        SELECT a.internal_id, a.risk_score, a.risk_keywords,
               (SELECT COUNT(*) FROM auction_tenants t WHERE t.internal_id = a.internal_id) as tenant_count,
               (SELECT COUNT(*) FROM auction_tenants t WHERE t.internal_id = a.internal_id AND (t.has_opposing_power LIKE '%O%' OR t.has_opposing_power LIKE '%있음%')) as opposing_count
        FROM auction_items a
        WHERE a.internal_id IN ({placeholders}) AND a.detail_scraped = 1
    ''', ids)
    rows = cursor.fetchall()

    grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    batch = []

    for row in rows:
        internal_id = row[0]
        risk_score = row[1] or 0
        risk_keywords = row[2] or '[]'
        tenant_count = row[3] or 0
        opposing_count = row[4] or 0

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

    for g, iid in batch:
        cursor.execute('UPDATE auction_items SET difficulty_grade = ? WHERE internal_id = ?', (g, iid))
    conn.commit()

    print(f"  ✅ 난이도: A={grades['A']} B={grades['B']} C={grades['C']} D={grades['D']}")
    return len(batch)


# ========================================
# 신규 컬럼 확인
# ========================================
def ensure_columns(conn):
    """필요한 컬럼이 있는지 확인하고 없으면 추가"""
    cursor = conn.cursor()
    new_cols = [
        ('road_access', 'TEXT'), ('approval_date', 'TEXT'),
        ('total_households', 'INTEGER'), ('occupancy_status', 'TEXT'),
        ('difficulty_grade', 'TEXT'),
    ]
    for col_name, col_type in new_cols:
        try:
            cursor.execute(f'ALTER TABLE auction_items ADD COLUMN {col_name} {col_type}')
            conn.commit()
        except:
            pass


# ========================================
# 메인
# ========================================
if __name__ == '__main__':
    import time
    from datetime import datetime

    start = time.time()
    print("=" * 60)
    print("증분 데이터 보완 시작")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"❌ DB 없음: {DB_PATH}")
        sys.exit(1)

    # 변경 ID 로드
    ids = load_changed_ids()

    # 명령행에서 ID 직접 지정도 가능
    if len(sys.argv) > 1:
        ids = [int(x) for x in sys.argv[1].split(',') if x.strip().isdigit()]

    if not ids:
        print("\n⚠️ 변경된 ID가 없습니다. 전체 처리를 진행합니다.")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT internal_id FROM auction_items WHERE detail_scraped = 1')
        ids = [r[0] for r in cursor.fetchall()]
        conn.close()

    print(f"\n대상: {len(ids):,}건\n")

    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)

    # 1. 주소 시/군/구
    print("[1/5] 주소 시/군/구 분리...")
    fix_address_sigungu(conn, ids)

    # 2. 리스크 태깅
    print("\n[2/5] 리스크 태깅...")
    fix_risk_tagger(conn, ids)

    # 3. 낙찰가율
    print("\n[3/5] 낙찰가율 계산...")
    fix_sale_rate(conn, ids)

    # 4. 건물 스펙 + 추가 파싱
    print("\n[4/5] 건물 스펙 + 추가 파싱...")
    fix_building_and_extras(conn, ids)

    # 5. 난이도 등급
    print("\n[5/5] 난이도 등급...")
    fix_difficulty_grade(conn, ids)

    conn.close()

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"✅ 증분 보완 완료! 소요: {elapsed:.1f}초")
    print(f"{'='*60}")