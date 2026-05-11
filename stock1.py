import os
import requests
import pandas as pd
from io import StringIO
from pymongo import MongoClient
import matplotlib
import matplotlib.pyplot as plt
import streamlit as st
import FinanceDataReader as fdr
from urllib.parse import quote
import matplotlib.font_manager as fm
import koreanize_matplotlib

# 기본 설정
matplotlib.rcParams['axes.unicode_minus'] = False
st.set_page_config(page_title="주식 분석 대시보드", layout="wide")
st.subheader("📊 Stock Information System")

# ─────────────────────────────────────────
# 유틸리티 함수
# ─────────────────────────────────────────
def custom_metric(label, main_val, sub_val, delta=None, delta_color="normal"):
    display_main = f"{main_val:,.0f}" if isinstance(main_val, (int, float)) else main_val
    display_sub  = f"{sub_val:,.0f}"  if isinstance(sub_val,  (int, float)) else sub_val
    color = "#31333F"
    if delta and delta != "-":
        if delta_color == "inverse":
            color = "red" if "-" not in str(delta) else "blue"
        else:
            color = "red" if "+" in str(delta) or (isinstance(delta, (int, float)) and delta > 0) else "blue"
    
    st.markdown(f"""
    <div style="padding:10px;border-radius:5px;background-color:#f0f2f6;min-height:80px;">
        <p style="margin:0;font-size:14px;color:#555;font-weight:bold;">{label}</p>
        <p style="margin:0;line-height:1.2;">
            <span style="font-size:14pt;font-weight:bold;color:#111;">{display_main}</span>
            <sup style="font-size:12pt;color:#777;">({display_sub})</sup>
        </p>
        <p style="margin:0;font-size:20px;color:{color};font-weight:500;">{delta if delta else ""}</p>
    </div>""", unsafe_allow_html=True)

def color_format(val):
    color = "red" if val > 0 else "blue" if val < 0 else "black"
    return f'<span style="color:{color}">{val:+.1f}%</span>'

def set_korean_font():
    plt.rcParams['axes.unicode_minus'] = False
    font_path = '/tmp/NanumGothic.ttf'
    font_url  = 'https://github.com/googlefonts/nanum-gothic/raw/main/fonts/ttf/NanumGothic.ttf'
    if not os.path.exists(font_path):
        try:
            import urllib.request
            urllib.request.urlretrieve(font_url, font_path)
        except: return
    fm.fontManager.addfont(font_path)
    plt.rc('font', family='NanumGothic')

# ─────────────────────────────────────────
# 데이터 로드 및 저장 (MongoDB)
# ─────────────────────────────────────────
def get_mongo_col():
    MONGO_URL = st.secrets["mongo_uri"]
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000, tls=True, tlsInsecure=True)
    return client, client.forin.stock_info

@st.cache_data(ttl=30)
def load_mongo():
    client, col = get_mongo_col()
    with client:
        df = pd.DataFrame(col.find({}, {"_id": 0}))
    if df.empty:
        st.error("데이터를 불러올 수 없습니다.")
        st.stop()

    df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
    df['기준값']   = df['기준값'].fillna(0).astype(int)
    df['Memo']    = df['Memo'].fillna('')
    df['관심']    = df['관심'].fillna(0).astype(int)

    # 숫자 변환
    num_cols = ['매출_24','매출_25','매출_26','영익_24','영익_25','영익_26',
                '영익률_24','영익률_25','영익률_26','PER','ROE','유통']
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df

def save_data(category, stock_name, value):
    client, col = get_mongo_col()
    with client:
        if category == "ref_prices":
            value = int(float(value)) if str(value).replace('.','',1).isdigit() else 0
            col.update_one({"종목명": stock_name}, {"$set": {"기준값": value}})
        elif category == "memos":
            col.update_one({"종목명": stock_name}, {"$set": {"Memo": value}})
        elif category == "interest":
            col.update_one({"종목명": stock_name}, {"$set": {"관심": int(value)}})
    st.cache_data.clear()
    st.toast(f"저장 완료: {stock_name}")

# ─────────────────────────────────────────
# 수급 및 주가 분석 함수
# ─────────────────────────────────────────
@st.cache_data(ttl=6000)
def fetch_supply_data(stock_name, stock_code, _df_full):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(f'https://finance.naver.com/item/frgn.naver?code={stock_code}', headers=headers)
    try:
        fk = pd.read_html(StringIO(res.text))[2].dropna()
        if fk.shape[1] < 9: raise ValueError
    except:
        fk = pd.read_html(StringIO(res.text))[3].dropna()

    fk.columns = ['날짜','종가','전일비','등락률','거래량','기관','외국인','보유량','보유율']
    fk['개인'] = -(fk['외국인'] + fk['기관'])
    if fk['보유율'].dtype == 'O':
        fk['보유율'] = fk['보유율'].str.replace('%','').astype(float)

    dk = fk.head(10).reset_index(drop=True)
    target = _df_full[_df_full['종목코드'] == stock_code].iloc[0]
    
    info1 = f"{target['순위']} / {target['시총']}천억"
    info3 = f"외인:{int((dk['외국인']>0).sum())} / 기관:{int((dk['기관']>0).sum())} / 개인:{int((dk['개인']>0).sum())} (보유:{dk['보유율'].iloc[0]}%)"
    
    plot_df = dk[['날짜','종가','보유율']].copy()
    plot_df['날짜'] = pd.to_datetime(plot_df['날짜'])
    plot_df['일자'] = plot_df['날짜'].dt.strftime('%m.%d')
    
    return info1, info3, dk, plot_df.sort_values('날짜')

def plot_stock_st(df, stock_name):
    set_korean_font()
    fig, ax1 = plt.subplots(figsize=(10, 4.5))
    x = range(len(df))
    ax1.plot(x, df['보유율'], marker='o', color='royalblue', label='보유율')
    ax1.set_ylabel("보유율 (%)", color='royalblue')
    ax1.set_xticks(x)
    ax1.set_xticklabels(df['일자'], rotation=45)
    ax2 = ax1.twinx()
    ax2.plot(x, df['종가'], linestyle='--', color='crimson', marker='s', label='종가')
    ax2.set_ylabel("종가 (원)", color='crimson')
    plt.title(f"{stock_name} 수급 및 주가 추이")
    st.pyplot(fig)
    plt.close(fig)

# ─────────────────────────────────────────
# 메인 로직 시작
# ─────────────────────────────────────────
df = load_mongo()

if 'selected_name' not in st.session_state:
    st.session_state['selected_name'] = df['종목명'].iloc[0]

# 상단 레이아웃 (1단)
cool = st.columns([2, 1.2, 2.5, 1.8, 3.5])

with cool[0]:
    filt = st.selectbox("관심 필터", options=list(range(8)), 
                        format_func=lambda x: "전체 목록" if x == 0 else f"관심 {x}", label_visibility='collapsed')
    
    name_list = df[df['관심'] == filt]['종목명'].tolist() if filt != 0 else df['종목명'].tolist()
    if not name_list: name_list = df['종목명'].tolist()
    
    if st.session_state['selected_name'] not in name_list:
        st.session_state['selected_name'] = name_list[0]
        
    idx = name_list.index(st.session_state['selected_name'])
    item = st.selectbox("종목 선택", name_list, index=idx, key='stock_selector', label_visibility='collapsed')
    
    row_data = df[df['종목명'] == item].iloc[0]
    code = row_data['종목코드']
    
    cur_int = int(row_data['관심'])
    if st.checkbox(f"⭐ 관심 {cur_int}" if cur_int > 0 else "☆ 관심 등록", value=(cur_int > 0)):
        new_int = min(cur_int + 1, 7) if cur_int < 7 else 1
        if cur_int == 0: new_int = 1
    else:
        new_int = 0
    if new_int != cur_int:
        save_data("interest", item, new_int)

def _get(col, suffix='', fmt="{:.2f}"):
    v = row_data.get(col)
    if pd.isna(v) or v == '': return ''
    try: return fmt.format(float(v)) + suffix
    except: return str(v)

with cool[1]:
    st.markdown(f"""
        <div style="font-size:13px; line-height:2.4; padding-top:4px;">
            <b>유통</b>&nbsp; {_get('유통', '%')}<br>
            <b>PER</b>&nbsp;&nbsp; {_get('PER')}<br>
            <b>ROE</b>&nbsp;&nbsp; {_get('ROE', '%')}
        </div>
    """, unsafe_allow_html=True)

# 주가 데이터 가져오기
ts = fdr.DataReader(code).tail(60)
CC = ts['Close'].iloc[-1]
changes = [ts['Change'].iloc[-1]*100, ts['Change'].iloc[-2]*100, ts['Change'].iloc[-3]*100]
vol_3d = " / ".join([f"{int((ts['Close'].iloc[i]*ts['Volume'].iloc[i])/1e8)}억" for i in range(-5, 0)])
info1, info3, dk, plot_df = fetch_supply_data(item, code, df)

with cool[2]:
    st.markdown(f"""
        <div style="padding-top:2px;">
            <span style="font-size:18px; font-weight:bold;">{CC:,.0f}</span>&nbsp;&nbsp;
            <small>오늘 {color_format(changes[0])} 어제 {color_format(changes[1])}</small>
        </div>
        <p style='font-size:14px; font-weight:bold; margin:4px 0;'>{info1}</p>
        <p style='font-size:11px; color:#666; margin:0;'>{vol_3d}</p>
    """, unsafe_allow_html=True)

with cool[3]:
    btn_style = "padding:3px 8px; border:1px solid #bbb; border-radius:4px; text-decoration:none; font-size:11px; margin:2px;"
    st.markdown(f"""
        <a href="https://www.thinkpool.com/item/{code}" target="_blank" style="{btn_style}">Think</a>
        <a href="https://kr.tradingview.com/chart/?symbol=KRX:{code}" target="_blank" style="{btn_style}">Tr</a><br>
        <a href="https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?gicode=A{code}" target="_blank" style="{btn_style}">Fn</a>
        <a href="https://m.stock.naver.com/domestic/stock/{code}/research" target="_blank" style="{btn_style}">Nv</a>
    """, unsafe_allow_html=True)

with cool[4]:
    fin_df = pd.DataFrame({
        '구분': ['매출', '영익', '익율'],
        '24년': [_get('매출_24', fmt='{:.0f}'), _get('영익_24', fmt='{:.0f}'), _get('영익률_24')],
        '25년': [_get('매출_25', fmt='{:.0f}'), _get('영익_25', fmt='{:.0f}'), _get('영익률_25')],
        '26년': [_get('매출_26', fmt='{:.0f}'), _get('영익_26', fmt='{:.0f}'), _get('영익률_26')],
    }).set_index('구분')
    st.dataframe(fin_df, use_container_width=True, height=120)

st.divider()

# 2단 레이아웃 (기준가, 고저가, 지분율)
cols = st.columns([1.5, 2, 2, 2, 2, 2, 2, 2])

with cols[0]:
    ref_val = st.text_input("기준가", value=str(row_data['기준값']) if row_data['기준값']!=0 else "", key=f"ref_{item}")
    if ref_val.isdigit() and int(ref_val) > 0:
        diff = ((CC - int(ref_val)) / int(ref_val)) * 100
        st.markdown(f"**{diff:+.1f}%**")

# 메트릭 섹션
metrics = [
    ("1주최고", ts['Close'].tail(5).max(), "inverse"), ("1주최저", ts['Close'].tail(5).min(), "normal"),
    ("1달최고", ts['Close'].tail(20).max(), "inverse"), ("1달최저", ts['Close'].tail(20).min(), "normal"),
    ("3달최고", ts['Close'].max(), "inverse"), ("3달최저", ts['Close'].min(), "normal")
]
for i, (label, val, c_type) in enumerate(metrics):
    with cols[i+1]:
        delta_val = val - CC if "최고" in label else CC - val
        delta_pct = (delta_val / (CC if "최고" in label else val)) * 100
        custom_metric(label, val, delta_val, f"{'+' if delta_val>0 else ''}{delta_pct:.1f}%", c_type)

with cols[7]:
    # 지분율 줄바꿈 처리
    jibun_raw = row_data.get('지분율', '')
    parts = [p.strip() for p in str(jibun_raw).split('/') if p.strip()]
    html_jibun = "<br>".join([f"<span style='font-size:11px;'>{p}</span>" for p in parts[:3]])
    st.markdown(f"<div style='line-height:1.6; padding-top:5px;'><b>지분율</b><br>{html_jibun}</div>", unsafe_allow_html=True)

# 하단 차트 및 테이블
st.divider()
t1, t2 = st.columns([1.2, 2])
with t1:
    st.markdown(f"**최근 수급 현황** <small>({info3})</small>", unsafe_allow_html=True)
    dk_disp = dk[['날짜','종가','등락률','외국인','기관','개인']].copy()
    dk_disp['외/기/개'] = dk_disp.apply(lambda x: f"{x['외국인']/1e3:.0f}/{x['기관']/1e3:.0f}/{x['개인']/1e3:.0f}", axis=1)
    st.dataframe(dk_disp[['날짜','종가','등락률','외/기/개']], use_container_width=True, hide_index=True)

with t2:
    plot_stock_st(plot_df, item)

# 메모
memo_val = st.text_area("📝 종목 메모", value=row_data['Memo'], height=100)
if st.button("💾 메모 저장"):
    save_data("memos", item, memo_val)
