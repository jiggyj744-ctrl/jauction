import sqlite3
import json

from config import DB_PATH

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

def analyze_risks():
    print("리스크 키워드 분석 시작...")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 전체 물건을 가져와서 분석 (배치 처리)
        cursor.execute('''
            SELECT internal_id, notes, non_extinguishable_rights, non_extinguishable_easement
            FROM auction_items
            WHERE detail_scraped = 1
        ''')
        
        items = cursor.fetchall()
        updated_count = 0
        
        for row in items:
            internal_id = row[0]
            notes = row[1] or ""
            rights = row[2] or ""
            easement = row[3] or ""
            
            full_text = f"{notes} {rights} {easement}"
            
            found_keywords = []
            total_score = 0
            
            for kw, score in RISK_KEYWORDS.items():
                if kw in full_text:
                    found_keywords.append(kw)
                    total_score += score
                    
            # 대항력의 경우 임차인 테이블도 확인해야 함
            cursor.execute("SELECT has_opposing_power FROM auction_tenants WHERE internal_id = ?", (internal_id,))
            tenants = cursor.fetchall()
            for t in tenants:
                if t[0] and ('O' in t[0] or '여' in t[0] or '있음' in t[0]):
                    if '대항력' not in found_keywords:
                        found_keywords.append('대항력')
                        total_score += RISK_KEYWORDS['대항력']
                    break
                    
            risk_json = json.dumps(found_keywords, ensure_ascii=False) if found_keywords else None
            
            cursor.execute('''
                UPDATE auction_items
                SET risk_keywords = ?, risk_score = ?
                WHERE internal_id = ?
            ''', (risk_json, total_score, internal_id))
            
            if found_keywords:
                updated_count += 1
                
        conn.commit()
    print(f"리스크 분석 완료: {updated_count}건에 리스크 키워드 반영됨.")

if __name__ == '__main__':
    analyze_risks()
