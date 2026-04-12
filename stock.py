import json
import os
import streamlit as st
import requests
import pandas as pd
from io import StringIO
import FinanceDataReader as fdr
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote


st.set_page_config(page_title="기본정보", layout="wide")
st.subheader("📊 Stock")
def custom_metric(label, main_val, sub_val, delta=None, delta_color="normal"):
    # 1. main_val 포맷팅 (숫자면 천단위 콤마, 아니면 그대로)
    display_main = f"{main_val:,.0f}" if isinstance(main_val, (int, float)) else main_val
    
    # 2. sub_val 포맷팅 (숫자면 천단위 콤마, 아니면 그대로)
    display_sub = f"{sub_val:,.0f}" if isinstance(sub_val, (int, float)) else sub_val
    
    # 3. delta 색상 및 기호 설정
    color = "#31333F"  # 기본 색상 (어두운 회색)
    if delta and delta != "-":
        if delta_color == "inverse":
            color = "red" if "-" not in str(delta) else "blue"
        else:
            color = "red" if "+" in str(delta) or (isinstance(delta, (int, float)) and delta > 0) else "blue"

    # HTML 출력
    html_code = f"""
    <div style="padding: 10px; border-radius: 5px; background-color: #f0f2f6; min-height: 80px;">
        <p style="margin:0; font-size:14px; color:#555; font-weight:bold;">{label}</p>
        <p style="margin:0; line-height: 1.2;">
            <span style="font-size:14pt; font-weight:bold; color:#111;">{display_main}</span>
            <sup style="font-size:12pt; color:#777;">({display_sub})</sup>
        </p>
        <p style="margin:0; font-size:20px; color:{color}; font-weight:500;">{delta if delta else ""}</p>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)
def color_format(val):
    color = "red" if val < 0 else "black"
    return f'<span style="color:{color}">{val:+.1f}%</span>'
#################################################################################
STORAGE_FILE = "stock_data.json"

def load_data():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"ref_prices": {}, "memos": {}}

def save_data(category, stock_name, value):
    data = load_data()
    data[category][stock_name] = value
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    st.toast(f"'{stock_name}' 정보 저장 완료!", icon="💾")

db = load_data()
#################################################################################

df = pd.read_json('stock.json', encoding='utf-8')
if 'selected_name' not in st.session_state:
    st.session_state['selected_name'] = df['Name'].iloc[0]

def update_stock():

    new_name = st.session_state['stock_selector']
    selected_row = df[df['Name'] == new_name].iloc[0]
    st.session_state['selected_code'] = selected_row['Code']
    st.session_state['selected_name'] = new_name

# 3. Selectbox 구성
cool = st.columns([2, 1.5, 2, 2, 3])

# 현재 저장된 이름의 인덱스 찾기
try:
    current_index = df['Name'].tolist().index(st.session_state['selected_name'])
except ValueError:
    current_index = 0

#################### item  #################################################################
item = cool[0].selectbox("Choice", df['Name'].tolist(), index=current_index,
    key='stock_selector',  # 세션 키 지정
    on_change=update_stock)# 값이 바뀔 때 즉시 함수 실행 

if 'selected_code' not in st.session_state:
    st.session_state['selected_code'] = df[df['Name'] == st.session_state['selected_name']].iloc[0]['Code']

code = st.session_state['selected_code']

##############################################################################################
@st.cache_data(ttl=600)  # 10분 동안 캐시 유지
def get_stock_data(code):
    return fdr.DataReader(code).tail(60)

# 사용 시
ts = get_stock_data(code)
if not ts.empty:
    CC = ts['Close'].iloc[-1]
    high_1w = ts['Close'].tail(5).max() if len(ts) >= 1 else ""
    high_1m = ts['Close'].tail(20).max() if len(ts) >= 1 else ""
    high_3m = ts['Close'].max() if len(ts) >= 1 else ""
    
    low_1w = ts['Close'].tail(5).min() if len(ts) >= 1 else ""
    low_1m = ts['Close'].tail(20).min() if len(ts) >= 1 else ""
    low_3m = ts['Close'].min() if len(ts) >= 1 else ""
    changes = [ts['Change'].iloc[-1] * 100, ts['Change'].iloc[-2] * 100, ts['Change'].iloc[-3] * 100]

###################################################################################
kk = 2
if kk == 1 :
    @st.cache_data(ttl=6000)  # 텍스트 정보이므로 1시간 정도 캐시해도 무방
    
    def get_thinkpool_data(code):
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # GUI 없이 실행
        chrome_options.add_argument('--window-size=1920x1080')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('user-agent=Mozilla/5.0')
    
        # 드라이버 실행 (자동 설치 및 설정)
        try : 
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            from webdriver_manager.chrome import ChromeDriverManager
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.implicitly_wait(2)
        try:
            url = f'https://www.thinkpool.com/item/{code}'
            driver.get(url)
            element1 = driver.find_element(By.CSS_SELECTOR, '#content > div > div.sub-content > div > div > div.left > div:nth-child(1) > a:nth-child(1) > div > strong')
            return element1.text, url
        except:
            return None, None
        finally:
            driver.quit()
    
    el1, url = get_thinkpool_data(code)
    # 6. 결과 표시 (두 번째 컬럼: 값 표시)
    if el1:
        with cool[1]:
            sub_left, sub_mid, sub_right = st.columns([1, 2, 1])
    
            with sub_mid:
                st.link_button(label=el1, url=url)
                st.write(f'{CC}')
    else:
        cool[1].info("데이터 없음")
if kk == 2 :
    url = f'https://www.thinkpool.com/item/{code}'
    with cool[1]:
        sub_left, sub_mid, sub_right = st.columns([1, 2, 1])
    
        with sub_mid:
            st.link_button(label=Think, url=url)
            st.write(f'{CC}')
            
###################################################################################
with cool[2]:
    sub1, sub2, sub3 = st.columns([1, 1, 1])

    with sub1:
        st.markdown(f"##### 그제  {color_format(changes[2])}", unsafe_allow_html=True)
    with sub2:
        st.markdown(f"##### 어제  {color_format(changes[1])}", unsafe_allow_html=True)
    with sub3:
        st.markdown(f"##### 오늘  {color_format(changes[0])}", unsafe_allow_html=True)

@st.cache_data(ttl=6000)
def MM (code) :
    target = df[df['Code'] == code].iloc[0]    
    m_rank = target['순위']
    a_rank = target['거래순위']
    m_won = target['거래대금']
    amm = target['시가총액']

    headers = {"User-Agent": "Mozilla/5.0"}
    url = f'https://finance.naver.com/item/frgn.naver?code={code}'
    res = requests.get(url, headers=headers)

    try:
        fk = pd.read_html(StringIO(res.text))[2]
        fk = fk.dropna()
        fk.columns = ['날짜','종가','전일비','등락률','거래량','기관','외국인','보유량','보유율']
    except:
        fk = pd.read_html(StringIO(res.text))[3]
        fk = fk.dropna()
        fk.columns = ['날짜','종가','전일비','등락률','거래량','기관','외국인','보유량','보유율']
        
    fk['개인'] = -(fk['외국인'] + fk['기관'])
    if fk['보유율'].dtype == 'O':
        fk['보유율'] = fk['보유율'].str.replace('%', '').astype(float)

    dk = fk.head(10).reset_index(drop=True)
    FO = int((dk['외국인'] > 0).sum())
    GV = int((dk['기관'] > 0).sum())
    IN = int((dk['개인'] > 0).sum())
    FC = dk['보유율'].iloc[0] # 가장 최근 날짜
    return f"{m_rank}위/ {amm}천억",f"{m_won}억", f"외인:{FO}/기관:{GV}/개인:{IN}(보유:{FC})", dk

info1, info2, info3, info4 = MM(code)
with cool[3]:
    st.subheader(info1)
    st.caption(info2)
with cool[4]:
    ss1, ss2, ss3 = st.columns([1, 1, 1])
    with ss1:
        st.link_button(label=' Tr', url= f'https://kr.tradingview.com/chart/Y3Tq45pg/?symbol=KRX%3A{code}')
    with ss2:
        st.link_button(label=' Fn ', url= f'https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?gicode=A{code}')
    with ss3:
        st.link_button(label='Nv ', url= f'https://m.stock.naver.com/domestic/stock/{code}/research')

    st.link_button(label=' 투자자 ', url= f'https://www.samsungpop.com/mbw/trading/domesticStock.do?cmd=stockInvestorList')

#####################################################################################################################################

cols = st.columns([1.5, 2, 2, 2, 2, 2, 2, 2])
with cols[0] :
    saved_ref = db["ref_prices"].get(item, "")
    ref_input = st.text_input("기준가", value=saved_ref, key=f"ref_{item}", 
                                on_change=lambda: save_data("ref_prices", item, st.session_state[f"ref_{item}"]))
    
    if ref_input.replace('.', '', 1).isdigit() and float(ref_input) > 0:
        diff = ((CC - float(ref_input)) / float(ref_input)) * 100
        color = "blue" if diff >= 0 else "red"
        st.markdown(f"  {CC-float(ref_input):,.0f} ( :{color}[{diff:+.2f}%])")
        # st.caption(f"현재가: {CC-float(ref_input):,.0f}원")
with cols[1]:
    difh_1w = high_1w - CC
    p_h1w = (difh_1w / CC) * 100
    custom_metric("1주최고", high_1w, difh_1w, f"-{p_h1w:.1f}%", "inverse")

with cols[2]:
    difl_1w = CC - low_1w
    p_l1w = (difl_1w / low_1w) * 100
    custom_metric("1주최저", low_1w, difl_1w, f"+{p_l1w:.1f}%")

with cols[3]:
    difh_1m = high_1m - CC
    p_h1m = (difh_1m / CC) * 100
    custom_metric("1달최고", high_1m, difh_1m, f"-{p_h1m:.1f}%", "inverse")

with cols[4]:
    difl_1m = CC - low_1m
    p_l1m = (difl_1m / low_1m) * 100
    custom_metric("1달최저", low_1m, difl_1m, f"+{p_l1m:.1f}%")

with cols[5]:
    difh_3m = high_3m - CC
    p_h3m = (difh_3m / CC) * 100
    custom_metric("분기최고", high_3m, difh_3m, f"-{p_h3m:.1f}%", "inverse")

with cols[6]:
    difl_3m = CC - low_3m
    p_l3m = (difl_3m / low_3m) * 100
    custom_metric("분기최저", low_3m, difl_3m, f"+{p_l3m:.1f}%")

with cols[7]:
    co1, co2 = st.columns(2)    
    co1.link_button(label= 'google', url = f"https://news.google.com/search?q={quote(item)}&hl=ko&gl=KR&ceid=KR:ko")
    co1.link_button(label= 'naver', url = f"https://m.stock.naver.com/domestic/stock/{code}/discussion")
    


oneday = f'https://webchart.thinkpool.com/2021ReNew/CumulationSelling/A{code}.png' ## 투자자
week = f'https://ssl.pstatic.net/imgfinance/chart/item/area/week/{code}.png?sidcode=1692943560017'  ## 5일주가
sbuy = f'https://webchart.thinkpool.com/2021ReNew/stock1day_volume/A{code}.png' ## 매몰도

cols1 = st.columns([2, 2, 2]) 

with cols1[0]:
    st.image(oneday, width = 'stretch', caption="투자자")
with cols1[1]:
    st.image(week, width = 'stretch', caption="5일 주가")
with cols1[2]:
    st.image(sbuy, width = 'stretch', caption="매몰도")

#########################################################################################################
st.divider()
tab1, tab2 = st.columns([1.2, 2])
with tab1:
    display_df = info4[['날짜','종가','등락률','외국인', '기관', '개인', '보유율']].copy()
    display_df['날짜'] = display_df['날짜'].str.slice(5) 
    display_df['종가'] = pd.to_numeric(display_df['종가'], errors='coerce').fillna(0).astype(int)   
    display_df['등락률'] = display_df['등락률'].str.replace('%', '').astype(float)

    # 4. 수급 데이터 단위 변경 (K 단위)
    for col in ['외국인', '기관', '개인']:
        display_df[col] = pd.to_numeric(display_df[col], errors='coerce') / 1000
    # display_df = display_df[::-1].copy()
    # 5. 스타일 적용
    styled = (display_df.style.hide(axis="index")
        .map(lambda v: 'background-color: #FFD1DC' if isinstance(v, (int, float)) and v > 0 else '', 
                subset=['등락률','외국인', '기관', '개인'])
        .format(precision=1)
        .set_properties(**{'text-align': 'center'})
        .set_table_styles([
            {'selector': 'th', 'props': [('text-align', 'center')]},
            {'selector': 'td', 'props': [('text-align', 'center')]}]))

    st.markdown(styled.to_html(), unsafe_allow_html=True)

with tab2:

    cols = st.columns([2, 2, 2, 2, 1])
    st.markdown(f""" <p style="font-size: 21px; font-weight: bold; color: #31333F; padding-top: 10px;"> {info3} </p> """, unsafe_allow_html=True)

    labels = ['등락률', "외국인", "기관", "개인"]
    for col, label in zip(cols, labels):
        val = display_df[label].sum()
        
        # 수치에 따른 색상 결정 (양수: 파랑, 음수: 빨강, 0: 검정)
        color = "#0000FF" if val > 0 else "#FF0000" if val < 0 else "#000000"        
        # HTML로 출력
        col.markdown(f"**{label}**") # 라벨
        col.markdown(f"<h2 style='color:{color}; margin-top:-15px;'>{val:,.0f}</h2>", unsafe_allow_html=True)
    st.divider()

    cl1, cl2, cl3, cl4 = st.columns([2, 2, 2, 1])
    M3 = f'https://cdn.fnguide.com/SVO2/chartImg/01_01/A{code}_3M_02.png'
    Y1 = f'https://cdn.fnguide.com/SVO2/chartImg/01_01/A{code}_1Y_02.png'
    Y3 = f'https://cdn.fnguide.com/SVO2/chartImg/01_01/A{code}_3Y_02.png'
    with cl1:
        st.image(M3, width=250, caption="3개월")
    with cl2:
        st.image(Y1, width=250, caption="1년")
    with cl3:
        st.image(Y3, width=250, caption="3년")


# --- 메모 UI 섹션 ---
st.subheader("📝 Memo")
saved_memo = db["memos"].get(item, "")
st.text_area("종목 메모", value=saved_memo, key=f"memo_{item}", height=100,
                on_change=lambda: save_data("memos", item, st.session_state[f"memo_{item}"]))



