"""
경매 물건 전문가 분석 코멘트 자동 생성기
- 물건별 고유 분석 (반복 방지)
- 전문성 + 신뢰성 + 의뢰율 유도
"""
import re

def parse_rate(rate_str):
    """'(34%)' → 34"""
    if not rate_str:
        return None
    m = re.search(r'(\d+)', str(rate_str))
    return int(m.group(1)) if m else None

def parse_stats(stats_str):
    """stats JSON 문자열 파싱"""
    if not stats_str:
        return None
    try:
        import json
        return json.loads(stats_str) if isinstance(stats_str, str) else stats_str
    except:
        return None

def analyze_risk(item):
    """리스크 레벨 분석 → 'high', 'medium', 'low'"""
    risks = 0
    notes = (item.get('notes') or '').lower()
    tenant = (item.get('tenant_info') or '').lower()
    rights = (item.get('non_extinguishable_rights') or '')
    
    # 리스크 요소 카운트
    if '일괄매각' in notes: risks += 2
    if '명도' in notes or '점유' in notes: risks += 2
    if '소멸' in str(rights) and len(str(rights)) > 5: risks += 2
    if tenant and '없' not in tenant and '조사된 임차' not in tenant: risks += 1
    if '농지' in notes: risks += 1
    if '환매' in notes: risks += 1
    if '가압류' in notes or '압류' in notes: risks += 1
    if '대항력' in tenant: risks += 2
    if '선순위' in tenant: risks += 2
    if '전입' in tenant: risks += 1
    if '확정일' in tenant: risks += 1
    
    # 유찰 횟수
    fail = item.get('fail_count', 0) or 0
    if fail >= 3: risks += 1
    
    if risks >= 5: return 'high'
    if risks >= 2: return 'medium'
    return 'low'

def get_risk_factors(item):
    """주요 리스크 요소 추출"""
    factors = []
    notes = item.get('notes') or ''
    tenant = item.get('tenant_info') or ''
    rights = item.get('non_extinguishable_rights') or ''
    
    if '일괄매각' in notes:
        factors.append('일괄매각 조건 — 전체 물건 동시 인수 필요')
    if '농지취득자격' in notes or '농지' in notes:
        factors.append('농지취득자격증명 제출 필요')
    if '명도' in notes:
        factors.append('명도(인도) 문제 가능성 — 현장 확인 필수')
    if '점유' in notes:
        factors.append('현재 점유 중 — 명도 소요 가능')
    if '환매' in notes:
        factors.append('환매청구권 존재 — 권리 분석 필요')
    if '대항력' in tenant:
        factors.append('대항력 있는 임차인 존재')
    if '선순위' in tenant:
        factors.append('선순위 임차인 존재 — 배당 영향 가능')
    if '전입' in tenant:
        factors.append('전입신고 된 임차인 확인')
    if rights and len(rights) > 3:
        factors.append('소멸되지 않는 권리 존재')
    if '공부상' in notes and ('불일치' in notes or '다름' in notes):
        factors.append('공부상 정보와 현황 불일치')
    if '가압류' in notes:
        factors.append('가압류 설정됨')
    if '도로' in notes and ('사설' in notes or '없' in notes):
        factors.append('접근도로 확인 필요')
    
    # 유찰
    fail = item.get('fail_count', 0) or 0
    if fail >= 3:
        factors.append(f'{fail}회 유찰 — 시장 관심 낮음')
    
    return factors[:4]  # 최대 4개

def get_opportunity(item):
    """기회 요인 분석"""
    factors = []
    rate = parse_rate(item.get('min_rate'))
    fail = item.get('fail_count', 0) or 0
    tenant = item.get('tenant_info') or ''
    notes = item.get('notes') or ''
    
    if rate and rate <= 40:
        factors.append(f'최저가율 {rate}% — 감정가 대비 {100-rate}% 할인')
    if fail >= 3:
        factors.append(f'{fail}회 유찰로 가격 많이 하락')
    if not tenant or '없' in tenant or '조사된 임차' in tenant:
        factors.append('임차인 이슈 없어 명도 용이')
    if rate and rate <= 30:
        factors.append('시장 대비 매우 낮은 진입 가격')
    
    return factors[:3]

def get_market_analysis(item):
    """시장 통계 기반 분석"""
    stats_3m = parse_stats(item.get('stats_3m'))
    stats_6m = parse_stats(item.get('stats_6m'))
    
    if not stats_3m:
        return None
    
    count = stats_3m.get('count', '-')
    avg_app = stats_3m.get('avg_appraisal', '-')
    avg_sale = stats_3m.get('avg_sale', '-')
    fail_cnt = stats_3m.get('fail_count', '-')
    
    return {
        'count': count,
        'avg_appraisal': avg_app,
        'avg_sale': avg_sale,
        'fail_count': fail_cnt
    }

def get_recommendation(item, risk_level):
    """물건 유형별 추천"""
    cat = item.get('category', '')
    item_type = item.get('item_type', '')
    rate = parse_rate(item.get('min_rate'))
    
    recs = {
        '주거용 부동산': {
            'target': '실거주 또는 투자 목적의 개인 투자자',
            'tip': '실제 내부 상태와 주변 시세 확인이 중요합니다'
        },
        '토지': {
            'target': '토지 개발 경험이 있는 투자자',
            'tip': '용도지역 확인과 개발 가능성 검토가 필수입니다'
        },
        '상업용 부동산': {
            'target': '상업 부동산 운영 경험이 있는 투자자',
            'tip': '현재 임대차 관계와 수익률 분석이 중요합니다'
        },
        '기타': {
            'target': '해당 물건 전문 지식이 있는 투자자',
            'tip': '물건 특성에 따른 전문 검토가 필요합니다'
        }
    }
    
    rec = recs.get(cat, recs['기타'])
    
    # 리스크에 따른 추가 추천
    if risk_level == 'high':
        rec['tip'] = '⚠️ 복잡한 권리관계 — 전문가 상담을 강력히 권장합니다'
    elif risk_level == 'medium':
        rec['tip'] = '💡 주의 깊은 권리 분석이 필요합니다'
    
    return rec

def get_cta_message(risk_level, rate):
    """CTA 메시지 (리스크/가격에 따라 차등)"""
    if risk_level == 'high':
        return '⚠️ 권리관계 복잡 — 반드시 전문가 상담을 받으세요'
    elif risk_level == 'medium':
        return '💡 상세 권리 분석과 시세 비교가 필요하시면 상담 가능합니다'
    elif rate and rate <= 35:
        return '🎯 저가 매물 — 투자 가치 상세 분석 도와드립니다'
    else:
        return '📊 시세 비교 및 권리 분석 상담 가능합니다'

def generate_expert_comment(item):
    """물건별 고유 전문가 코멘트 생성"""
    
    # 기본 정보
    court = item.get('court', '')
    item_type = item.get('item_type', '')
    cat = item.get('category', '')
    rate = parse_rate(item.get('min_rate'))
    fail = item.get('fail_count', 0) or 0
    status = item.get('status', '')
    notes = item.get('notes') or ''
    tenant = item.get('tenant_info') or ''
    dday = item.get('bid_dday', '')
    addr = item.get('address', '')
    sido = item.get('address_sido', '')
    
    # 분석
    risk_level = analyze_risk(item)
    risk_factors = get_risk_factors(item)
    opportunities = get_opportunity(item)
    market = get_market_analysis(item)
    recommendation = get_recommendation(item, risk_level)
    cta_msg = get_cta_message(risk_level, rate)
    
    # === 1. 핵심 요약 (1~2문장, 고유) ===
    summary_parts = []
    
    # 법원 + 물건유형
    if court and item_type:
        summary_parts.append(f'{court} 경매 {item_type} 물건')
    
    # 가격 분석
    if rate is not None:
        if rate <= 30:
            summary_parts.append(f'감정가 대비 {100-rate}% 할인된 초저가')
        elif rate <= 50:
            summary_parts.append(f'최저가율 {rate}%로 시장 평균 이하')
        elif rate <= 70:
            summary_parts.append(f'최저가율 {rate}%로 보통 수준')
        else:
            summary_parts.append(f'최저가율 {rate}%로 다소 높은 편')
    
    # 상태/유찰
    if status == '신건':
        summary_parts.append('신규 등록 물건')
    elif fail >= 3:
        summary_parts.append(f'{fail}회 유찰로 가격 많이 하락')
    elif fail >= 1:
        summary_parts.append(f'{fail}회 유찰')
    
    # D-day
    if dday and 'D-' in str(dday):
        try:
            d = int(re.search(r'(\d+)', str(dday)).group(1))
            if d <= 3:
                summary_parts.append(f'매각 {d}일 전으로 시간 촉박')
        except:
            pass
    
    summary = '. '.join(summary_parts[:3]) + '.'
    
    # === 2. 투자 포인트 (기회) ===
    opportunity_text = ''
    if opportunities:
        opportunity_text = '\n'.join(f'• {o}' for o in opportunities)
    
    # === 3. 체크포인트 (리스크) ===
    risk_text = ''
    if risk_factors:
        risk_text = '\n'.join(f'• {f}' for f in risk_factors)
    else:
        risk_text = '• 특이 리스크 요소 미발견 (기본 확인 권장)'
    
    # === 4. 시장 비교 ===
    market_text = ''
    if market:
        market_text = f'최근 3개월 동종 {market["count"]} 낙찰 | 평균 감정가 {market["avg_appraisal"]} | 평균 낙찰가 {market["avg_sale"]} | 평균 유찰 {market["fail_count"]}'
    
    # === 5. 추천 ===
    rec_target = recommendation.get('target', '')
    rec_tip = recommendation.get('tip', '')
    
    return {
        'summary': summary,
        'risk_level': risk_level,
        'opportunity': opportunity_text,
        'risk_factors': risk_text,
        'market': market_text,
        'rec_target': rec_target,
        'rec_tip': rec_tip,
        'cta_message': cta_msg,
    }