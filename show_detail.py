import sqlite3
import json
import webbrowser
import os

conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

# 아파트 하나 가져오기
c.execute("""SELECT * FROM auction_items WHERE item_type = '아파트' LIMIT 1""")
row = c.fetchone()
col_names = [d[0] for d in c.description]

if not row:
    c.execute("""SELECT * FROM auction_items WHERE item_type = '다세대(빌라)' LIMIT 1""")
    row = c.fetchone()
    col_names = [d[0] for d in c.description]

data = dict(zip(col_names, row))

# 입찰이력
c.execute("SELECT * FROM auction_bid_history WHERE internal_id = ?", (data['internal_id'],))
bid_rows = c.fetchall()
bid_cols = [d[0] for d in c.description]
bids = [dict(zip(bid_cols, b)) for b in bid_rows]

# 이미지
c.execute("SELECT * FROM auction_images WHERE internal_id = ?", (data['internal_id'],))
img_rows = c.fetchall()
img_cols = [d[0] for d in c.description]
images = [dict(zip(img_cols, im)) for im in img_rows]

conn.close()

# 가격 포맷
def fmt(val):
    if not val:
        return '-'
    try:
        n = int(val)
        return f"{n:,}원"
    except:
        return str(val)

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>물건 상세 - {data.get('case_number','')}</title>
<style>
body {{ font-family: 'Malgun Gothic', sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
h1 {{ color: #1a237e; border-bottom: 3px solid #1a237e; padding-bottom: 10px; }}
.badge {{ display: inline-block; padding: 4px 14px; border-radius: 12px; color: #fff; font-weight: bold; font-size: 14px; }}
.badge-신건 {{ background: #4CAF50; }}
.badge-유찰 {{ background: #FF9800; }}
.badge-매각 {{ background: #9E9E9E; }}
.badge-취하 {{ background: #f44336; }}
.badge-변경 {{ background: #2196F3; }}

.section {{ background: #fff; border-radius: 10px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }}
.section h2 {{ font-size: 16px; color: #37474F; margin-bottom: 12px; border-left: 4px solid #2196F3; padding-left: 10px; }}

table {{ width: 100%; border-collapse: collapse; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
td:first-child {{ font-weight: bold; color: #555; width: 140px; background: #fafafa; }}
td:last-child {{ color: #222; }}

.price {{ color: #1B5E20; font-weight: bold; font-size: 16px; }}
.note {{ background: #FFF3E0; padding: 12px; border-radius: 6px; margin-top: 8px; font-size: 13px; line-height: 1.6; }}
</style>
</head>
<body>

<h1>{data.get('case_number','')} <span class="badge badge-{data.get('status','')}">{data.get('status','')}</span></h1>

<div class="section">
<h2>📋 기본정보</h2>
<table>
<tr><td>사건번호</td><td>{data.get('case_number','')}</td></tr>
<tr><td>법원</td><td>{data.get('court','')}</td></tr>
<tr><td>물건종류</td><td>{data.get('item_type','')}</td></tr>
<tr><td>카테고리</td><td>{data.get('category','')}</td></tr>
<tr><td>경매종류</td><td>{data.get('auction_type','')}</td></tr>
<tr><td>매각일</td><td>{data.get('sale_date','')}</td></tr>
<tr><td>상태</td><td><span class="badge badge-{data.get('status','')}">{data.get('status','')}</span></td></tr>
</table>
</div>

<div class="section">
<h2>📍 소재지</h2>
<table>
<tr><td>주소</td><td style="font-size:15px;">{data.get('address','')}</td></tr>
<tr><td>시도</td><td>{data.get('address_sido','')}</td></tr>
</table>
</div>

<div class="section">
<h2>💰 가격정보</h2>
<table>
<tr><td>감정가</td><td class="price">{fmt(data.get('appraisal_price'))}</td></tr>
<tr><td>최저가</td><td class="price">{fmt(data.get('min_price'))}</td></tr>
<tr><td>최저가율</td><td>{data.get('min_rate','')}</td></tr>
<tr><td>매각가</td><td class="price">{fmt(data.get('sale_price'))}</td></tr>
<tr><td>매각가율</td><td>{data.get('sale_rate','')}</td></tr>
<tr><td>청구금액</td><td>{fmt(data.get('claim_amount'))}</td></tr>
<tr><td>보증금</td><td>{fmt(data.get('deposit'))}</td></tr>
</table>
</div>

<div class="section">
<h2>📐 면적정보</h2>
<table>
<tr><td>토지면적</td><td>{data.get('land_area','-')}</td></tr>
<tr><td>건물면적</td><td>{data.get('building_area','-')}</td></tr>
</table>
</div>

<div class="section">
<h2>👤 당사자정보</h2>
<table>
<tr><td>채권자</td><td>{data.get('creditor','-')}</td></tr>
<tr><td>채무자</td><td>{data.get('debtor','-')}</td></tr>
<tr><td>소유자</td><td>{data.get('owner','-')}</td></tr>
</table>
</div>

<div class="section">
<h2>📝 참고사항</h2>
<div class="note">{data.get('notes','-') or '-'}</div>
</div>

<div class="section">
<h2>🔗 관련사건</h2>
<table>
<tr><td>관련사건</td><td>{data.get('related_case','-')}</td></tr>
</table>
</div>

<div class="section">
<h2>🏠 임차/권리정보</h2>
<table>
<tr><td>임차내역</td><td>{data.get('tenant_info','-') or '-'}</td></tr>
<tr><td>소멸되지않는권리</td><td>{data.get('non_extinguishable_rights','-') or '-'}</td></tr>
<tr><td>소멸되지않는지상권</td><td>{data.get('non_extinguishable_easement','-') or '-'}</td></tr>
</table>
</div>

<div class="section">
<h2>차량정보</h2>
<table>
<tr><td>차명</td><td>{data.get('vehicle_name','-') or '-'}</td></tr>
<tr><td>제조사</td><td>{data.get('vehicle_maker','-') or '-'}</td></tr>
<tr><td>연식</td><td>{data.get('vehicle_year','-') or '-'}</td></tr>
<tr><td>연료</td><td>{data.get('vehicle_fuel','-') or '-'}</td></tr>
<tr><td>변속기</td><td>{data.get('vehicle_transmission','-') or '-'}</td></tr>
<tr><td>등록번호</td><td>{data.get('vehicle_reg_number','-') or '-'}</td></tr>
</table>
</div>

"""

if bids:
    html += '<div class="section"><h2>📊 입찰이력</h2><table>'
    html += '<tr style="background:#37474F;color:#fff;"><td>회차</td><td>날짜</td><td>최저가</td><td>결과</td></tr>'
    for b in bids:
        html += f'<tr><td>{b.get("bid_round","")}</td><td>{b.get("bid_date","")}</td><td>{fmt(b.get("min_bid_price"))}</td><td>{b.get("result","")}</td></tr>'
    html += '</table></div>'

if images:
    html += '<div class="section"><h2>📷 이미지</h2>'
    for im in images:
        lp = im.get('local_path','')
        if lp and os.path.exists(lp):
            html += f'<img src="file:///{lp}" style="max-width:400px;margin:5px;border-radius:8px;">'
    if not any(im.get('local_path','') and os.path.exists(im.get('local_path','')) for im in images):
        html += '<p>이미지 파일 없음</p>'
    html += '</div>'

html += '<div class="section"><h2>🔖 전체 필드 (RAW)</h2><table>'
for k, v in data.items():
    if v:
        html += f'<tr><td>{k}</td><td>{v}</td></tr>'
html += '</table></div>'

html += '</body></html>'

outpath = os.path.join(os.path.dirname(__file__), 'view_detail.html')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(html)

webbrowser.open(outpath)
print(f"상세페이지 열기: {outpath}")