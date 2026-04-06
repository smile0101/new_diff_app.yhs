import pandas as pd
import FinanceDataReader as fdr
import numpy as np
import streamlit as st
from urllib.parse import quote


st.set_page_config(layout="wide")
df = pd.read_excel('Target.xlsx', dtype={'code': str})

results = []
for idx, row in df.iterrows():
    code = row['code']
    item = row['item']
    try:
        dd = fdr.DataReader(code).tail(20).reset_index()
        curr = dd['Close'].iloc[-1]
        target = row['Target']
        
        ratio = (curr - target) / target * 100
        chg = dd['Change'].tail(5).values * 100
        c1, c2, c3, c4, c5 = chg[-1], chg[-2], chg[-3], chg[-4], chg[-5]
        w_sum = sum(chg)
        
        h_val = dd['Close'].max()
        l_val = dd['Close'].min()
        hh = (h_val - curr) / curr * 100
        ll = (curr - l_val) / l_val * 100
        
        # 1번 조건: 클릭 시 웹페이지가 열리는 HTML 태그 생성
        url = f'https://www.thinkpool.com/item/{code}'
        link_tag = f'<a href="{url}" target="_blank" style="text-decoration: none; color: #3498db; font-weight: bold;">link</a>'
        goo = f"https://news.google.com/search?q={quote(item)}&hl=ko&gl=KR&ceid=KR:ko"
        google = f'<a href="{goo}" target="_blank" style="text-decoration: none; color: #3498db; font-weight: bold;">구글</a>'

        results.append({
            'item': row['item'], 'Target': target, '현재': curr,
            '비율': ratio, '오늘': c1, '어제': c2, '그제': c3, '4일': c4, '5일': c5,
            '1주': w_sum, 'HH': hh, 'LL': ll, 'Rank': row['Rank'], 
            'link': link_tag, '구글' : google, 'Memo': row['Memo']
        })
    except:
        continue

dfv = pd.DataFrame(results)
dfv['Target'] = dfv['Target'].fillna(0).astype(int)
dfv['Rank'] = dfv['Rank'].astype('Int64')

# --- 스타일링 함수 정의 ---

# 수익률 색상 (빨강/파랑)
def color_returns(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #e74c3c; font-weight: bold;'
        elif val < 0: return 'color: #3498db; font-weight: bold;'
    return ''

# 2번 조건: 비율 2 이하일 때 분홍색 배경
def highlight_ratio(val):
    return 'background-color: #ffc0cb;' if val <= 2 else ''

# 3번 조건: HH, LL 5 이하일 때 분홍색 배경
def highlight_low_vol(val):
    return 'background-color: #ffc0cb;' if val <= 5 else ''

# 4. Pandas Styler 설정
styled_html = dfv.style\
    .map(color_returns, subset=["오늘", "어제", "그제", "4일", "5일", "1주"])\
    .map(highlight_ratio, subset=["비율"])\
    .map(highlight_low_vol, subset=["HH", "LL"])\
    .set_properties(**{'background-color': '#ffff00'}, subset=["오늘", "1주"]) \
    .format({
        "Target": "{:,}", "현재": "{:,}", 
        "비율": "{:.1f}%", "HH": "{:.1f}%", "LL": "{:.1f}%",
        "오늘": "{:+.1f}%", "어제": "{:+.1f}%", "그제": "{:+.1f}%", 
        "4일": "{:+.1f}%", "5일": "{:+.1f}%", "1주": "{:+.1f}%"
    })\
    .set_properties(**{
        'text-align': 'center', 
        'font-size': '15px', 
        'padding': '12px'
    })\
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('font-size', '16px'), 
            ('text-align', 'center'), 
            ('background-color', '#2c3e50'), 
            ('color', 'white'),
            ('padding', '15px')
        ]},
        {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]},
        {'selector': 'tr:hover', 'props': [('background-color', '#f5f6fa')]}
    ])\
    .hide(axis='index')\
    .to_html(escape=False)


st.title("📊 주식 리포트")
st.markdown(styled_html, unsafe_allow_html=True)
