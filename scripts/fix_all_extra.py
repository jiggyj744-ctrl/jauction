"""
추가 데이터 파싱 스크립트 (기존 DB 텍스트에서 정규식 개선)
1. 토지이용계획 regex 개선 (1.8% → ~89%)
2. 지붕구조 regex 개선 (2.6% → ~66%)
3. 층수 regex 개선 (2.6% → ~32%)
4. 도로접면 추출 (신규)
5. 사용승인일 추출 (신규)
6. 세대수 추출 (신규)
7. 주차 향상
"""
import sqlite3
import re
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'auction.db')

def fix_land_use_plan():
    """토지이용계획 regex 개선 — 1.8% → 목표 ~89%"""
    print("\n" + "="*60)
    print("1️⃣ 토지이용계획 추출 개선")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 아직 land_use_plan이 비어있고 appraisal_report가 있는 건
    cursor.execute('''
        SELECT internal_id, appraisal_report
        FROM auction_items
        WHERE (land_use_plan IS NULL OR land_use_plan = '')
          AND appraisal_report IS NOT NULL AND appraisal_report != ''
    ''')
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    
    for internal_id, report in rows:
        land_text = ''
        
        # 패턴 1: "8) 토지이용계획 = ..."
        m = re.search(r'8\)\s*토지이용계획\s*=\s*(.*?)(?=\n\n|\n9\)|$)', report, re.DOTALL)
        if m:
            land_text = m.group(1).strip()
        
        # 패턴 2: "토지이용계횸 ..." (오타 포함)
        if not land_text:
            m = re.search(r'토지이용계획[^\n]*\n?\s*(.*?)(?=\n\n|\n\d+\)|$)', report, re.DOTALL)
            if m:
                land_text = m.group(1).strip()
        
        # 패턴 3: "용도지역" 직접 검색
        if not land_text:
            m = re.search(r'(?:용도지역|지역지구)\s*[:=]?\s*(.*?)(?=\n\n|\n\d+\)|$)', report, re.DOTALL)
            if m:
                land_text = m.group(1).strip()
        
        if land_text:
            land_text = land_text[:500]
            batch.append((land_text, internal_id))
            updated += 1
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET land_use_plan = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated:,}건...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET land_use_plan = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM auction_items WHERE land_use_plan IS NOT NULL AND land_use_plan != ''")
    filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    print(f"  ✅ 완료: {updated:,}건 추가. 총 충족률: {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    conn.close()


def fix_roof_structure():
    """지붕구조 regex 개선 — 2.6% → 목표 ~66%"""
    print("\n" + "="*60)
    print("2️⃣ 지붕구조 추출 개선")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT internal_id, appraisal_report
        FROM auction_items
        WHERE (building_roof IS NULL OR building_roof = '')
          AND appraisal_report IS NOT NULL AND appraisal_report != ''
    ''')
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    
    roof_patterns = [
        r'([가-힣]+지붕)',                    # 슬래브지붕, 기와지붕 등
        r'지붕\s*[:=]\s*([가-힣]+)',          # 지붕: 슬래브
        r'지붕구조\s*[:=]?\s*([가-힣]+)',     # 지붕구조: 철골
    ]
    
    for internal_id, report in rows:
        roof = ''
        
        for pattern in roof_patterns:
            m = re.search(pattern, report)
            if m:
                roof = m.group(1)
                break
        
        if roof:
            batch.append((roof, internal_id))
            updated += 1
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET building_roof = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated:,}건...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET building_roof = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM auction_items WHERE building_roof IS NOT NULL AND building_roof != ''")
    filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    print(f"  ✅ 완료: {updated:,}건 추가. 총 충족률: {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    conn.close()


def fix_floors():
    """층수 regex 개선 — 2.6% → 목표 ~32%"""
    print("\n" + "="*60)
    print("3️⃣ 층수 추출 개선")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT internal_id, appraisal_report
        FROM auction_items
        WHERE (total_floors IS NULL OR total_floors = 0)
          AND appraisal_report IS NOT NULL AND appraisal_report != ''
    ''')
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    
    floor_patterns = [
        # "철근콘크리트조 슬래브지붕 14층 건물 내 10층"
        r'(\d+)층\s*건물\s*내\s*(\d+)층',
        # "지상 14층 지하 2층"
        r'지상\s*(\d+)\s*층',
        # "14층 건물"
        r'(\d+)\s*층\s*건물',
        # "건물의 층수 14층"
        r'층수\s*[:=]?\s*(\d+)',
    ]
    
    for internal_id, report in rows:
        total_f = 0
        target_f = 0
        
        # 패턴 1: "N층 건물 내 M층"
        m = re.search(r'(\d+)\s*층\s*건물\s*내\s*(\d+)\s*층', report)
        if m:
            total_f = int(m.group(1))
            target_f = int(m.group(2))
        else:
            # 패턴 2: "지상 N층"
            m = re.search(r'지상\s*(\d+)\s*층', report)
            if m:
                total_f = int(m.group(1))
        
        if total_f > 0:
            batch.append((total_f, target_f, internal_id))
            updated += 1
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET total_floors = ?, target_floor = CASE WHEN ? > 0 THEN ? ELSE target_floor END WHERE internal_id = ?', 
                             [(tf, tgt, tgt, iid) for tf, tgt, iid in batch])
            conn.commit()
            print(f"  진행: {updated:,}건...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET total_floors = ?, target_floor = CASE WHEN ? > 0 THEN ? ELSE target_floor END WHERE internal_id = ?', 
                         [(tf, tgt, tgt, iid) for tf, tgt, iid in batch])
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM auction_items WHERE total_floors IS NOT NULL AND total_floors != 0")
    filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    print(f"  ✅ 완료: {updated:,}건 추가. 총 충족률: {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    conn.close()


def add_new_columns():
    """신규 컬럼 추가"""
    print("\n" + "="*60)
    print("4️⃣ 신규 컬럼 추가")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_cols = [
        ('road_access', 'TEXT'),        # 도로접면
        ('approval_date', 'TEXT'),       # 사용승인일
        ('total_households', 'INTEGER'), # 세대수
        ('occupancy_status', 'TEXT'),    # 점유현황 요약
    ]
    
    for col_name, col_type in new_cols:
        try:
            cursor.execute(f'ALTER TABLE auction_items ADD COLUMN {col_name} {col_type}')
            conn.commit()
            print(f"  ✅ {col_name} ({col_type}) 컬럼 추가됨")
        except Exception as e:
            if 'duplicate' in str(e).lower():
                print(f"  ⏭️ {col_name} 이미 존재")
            else:
                print(f"  ❓ {col_name}: {e}")
    
    conn.close()


def fix_road_access():
    """도로접면 추출 (신규)"""
    print("\n" + "="*60)
    print("5️⃣ 도로접면 추출")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT internal_id, appraisal_report
        FROM auction_items
        WHERE appraisal_report IS NOT NULL AND appraisal_report != ''
          AND appraisal_report LIKE '%도로%'
    ''')
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    
    for internal_id, report in rows:
        road = ''
        
        # 패턴: "도로에 ~m 접함", "도로접면 ~m", "접도로 ~m"
        m = re.search(r'(?:도로에?\s*(?:접|면)\s*|접도로\s*|도로접면\s*)[:=]?\s*(\d+\.?\d*)\s*m', report)
        if m:
            road = f'{m.group(1)}m'
        else:
            # 패턴: "~도로에 접함"
            m = re.search(r'(\d+\.?\d*)\s*m\s*도로에?\s*접', report)
            if m:
                road = f'{m.group(1)}m'
            else:
                # 패턴: "도로 (포장/미포장) ~m"
                m = re.search(r'도로\s*\(?(\w+도로)?\)?\s*(\d+\.?\d*)\s*m', report)
                if m:
                    road = f'{m.group(2)}m'
        
        if road:
            batch.append((road, internal_id))
            updated += 1
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET road_access = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated:,}건...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET road_access = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM auction_items WHERE road_access IS NOT NULL AND road_access != ''")
    filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    print(f"  ✅ 완료: {updated:,}건. 충족률: {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    conn.close()


def fix_approval_date():
    """사용승인일 추출 (신규)"""
    print("\n" + "="*60)
    print("6️⃣ 사용승인일 추출")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT internal_id, appraisal_report
        FROM auction_items
        WHERE (approval_date IS NULL OR approval_date = '')
          AND (appraisal_report LIKE '%사용승인%' OR appraisal_report LIKE '%사용검사%')
    ''')
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    
    date_patterns = [
        r'사용승인일?\s*[:=]?\s*(\d{4}[\./-]\d{1,2}[\./-]\d{1,2})',
        r'사용검사일?\s*[:=]?\s*(\d{4}[\./-]\d{1,2}[\./-]\d{1,2})',
        r'사용승인\s*.*?(\d{4}[\./]\d{1,2}[\./]\d{1,2})',
        r'사용검사\s*.*?(\d{4}[\./]\d{1,2}[\./]\d{1,2})',
        r'준공일?\s*[:=]?\s*(\d{4}[\./-]\d{1,2}[\./-]\d{1,2})',
    ]
    
    for internal_id, report in rows:
        date_val = ''
        
        for pattern in date_patterns:
            m = re.search(pattern, report)
            if m:
                date_val = m.group(1).replace('.', '-').replace('/', '-')
                break
        
        if date_val:
            batch.append((date_val, internal_id))
            updated += 1
        
        if len(batch) >= 1000:
            cursor.executemany('UPDATE auction_items SET approval_date = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated:,}건...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET approval_date = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM auction_items WHERE approval_date IS NOT NULL AND approval_date != ''")
    filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    print(f"  ✅ 완료: {updated:,}건. 충족률: {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    conn.close()


def fix_households():
    """세대수 추출 (신규)"""
    print("\n" + "="*60)
    print("7️⃣ 세대수 추출")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT internal_id, appraisal_report
        FROM auction_items
        WHERE (total_households IS NULL OR total_households = 0)
          AND appraisal_report LIKE '%세대%'
    ''')
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    
    household_patterns = [
        r'총\s*(\d+)\s*세대',
        r'(\d+)\s*세대\s*(?:주택|아파트|오피스텔|빌라)',
        r'세대수\s*[:=]?\s*(\d+)',
        r'(\d+)\s*세대\s*(?:중|중\s*\d+)',
    ]
    
    for internal_id, report in rows:
        households = 0
        
        for pattern in household_patterns:
            m = re.search(pattern, report)
            if m:
                households = int(m.group(1))
                if households > 0 and households < 10000:  # 상식적 범위
                    break
                households = 0
        
        if households > 0:
            batch.append((households, internal_id))
            updated += 1
        
        if len(batch) >= 1000:
            cursor.executemany('UPDATE auction_items SET total_households = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated:,}건...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET total_households = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM auction_items WHERE total_households IS NOT NULL AND total_households != 0")
    filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    print(f"  ✅ 완료: {updated:,}건. 충족률: {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    conn.close()


def fix_occupancy_status():
    """점유현황 요약 추출 (신규) — status_report에서"""
    print("\n" + "="*60)
    print("8️⃣ 점유현황 요약 추출")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT internal_id, status_report
        FROM auction_items
        WHERE (occupancy_status IS NULL OR occupancy_status = '')
          AND status_report IS NOT NULL AND status_report != ''
          AND (status_report LIKE '%점유%' OR status_report LIKE '%거주%' OR status_report LIKE '%임대%' OR status_report LIKE '%공실%')
    ''')
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    
    for internal_id, report in rows:
        status = ''
        
        # 점유 패턴 추출
        if '공실' in report:
            status = '공실'
        elif '자택거주' in report:
            status = '소유자 거주'
        elif '임대차' in report:
            m = re.search(r'임대차.*?보증금\s*([0-9,]+)', report)
            status = f'임대차' + (f' (보증금 {m.group(1)})' if m else '')
        elif '거주' in report:
            status = '거주'
        elif '점유' in report:
            status = '점유'
        elif '임대' in report:
            status = '임대'
        
        if status:
            batch.append((status[:100], internal_id))
            updated += 1
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET occupancy_status = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated:,}건...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET occupancy_status = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM auction_items WHERE occupancy_status IS NOT NULL AND occupancy_status != ''")
    filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    print(f"  ✅ 완료: {updated:,}건. 충족률: {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    conn.close()


def fix_parking_improved():
    """주차 향상"""
    print("\n" + "="*60)
    print("9️⃣ 주차 향상")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT internal_id, appraisal_report
        FROM auction_items
        WHERE parking_available = 0 OR parking_available IS NULL
          AND appraisal_report IS NOT NULL AND appraisal_report != ''
          AND (appraisal_report LIKE '%주차%' OR appraisal_report LIKE '%차고%')
    ''')
    rows = cursor.fetchall()
    print(f"  대상: {len(rows):,}건")
    
    updated = 0
    batch = []
    
    for internal_id, report in rows:
        if '주차' in report or '차고' in report or '주차장' in report or '주차가능' in report:
            batch.append((1, internal_id))
            updated += 1
        
        if len(batch) >= 5000:
            cursor.executemany('UPDATE auction_items SET parking_available = ? WHERE internal_id = ?', batch)
            conn.commit()
            print(f"  진행: {updated:,}건...")
            batch = []
    
    if batch:
        cursor.executemany('UPDATE auction_items SET parking_available = ? WHERE internal_id = ?', batch)
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM auction_items WHERE parking_available IS NOT NULL AND parking_available != 0")
    filled = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    print(f"  ✅ 완료: {updated:,}건 추가. 총 충족률: {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    conn.close()


# ========================================
# 메인 실행
# ========================================
if __name__ == '__main__':
    print("🚀 추가 데이터 파싱 시작!")
    print(f"📁 DB: {DB_PATH}")
    
    # 신규 컬럼 추가
    add_new_columns()
    
    # 기존 데이터 개선
    fix_land_use_plan()
    fix_roof_structure()
    fix_floors()
    
    # 신규 추출
    fix_road_access()
    fix_approval_date()
    fix_households()
    fix_occupancy_status()
    fix_parking_improved()
    
    # 최종 통계
    print("\n" + "="*60)
    print("🎉 추가 파싱 완료! 최종 충족률:")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    
    for col, label in [
        ('building_structure', '건물구조'),
        ('building_roof', '지붕구조'),
        ('total_floors', '총층수'),
        ('target_floor', '해당층'),
        ('heating_type', '난방방식'),
        ('parking_available', '주차가능'),
        ('elevator_available', '승강기'),
        ('land_use_plan', '토지이용계획'),
        ('road_access', '도로접면'),
        ('approval_date', '사용승인일'),
        ('total_households', '세대수'),
        ('occupancy_status', '점유현황'),
        ('address_sigungu', '시군구'),
        ('risk_keywords', '리스크'),
        ('difficulty_grade', '난이도'),
        ('sale_rate', '낙찰가율'),
    ]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM auction_items WHERE [{col}] IS NOT NULL AND [{col}] != '' AND [{col}] != 0")
            filled = cursor.fetchone()[0]
            pct = filled/total*100
            bar = '█' * int(pct/5) + '░' * (20 - int(pct/5))
            print(f"  {label:12} ({col:20}): {filled:>6,}/{total:,} ({pct:5.1f}%) {bar}")
        except Exception as e:
            print(f"  {label:12} ({col:20}): 오류 ({e})")
    
    conn.close()