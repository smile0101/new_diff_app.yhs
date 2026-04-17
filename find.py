import streamlit as st
import pandas as pd
import requests
from io import StringIO

st.set_page_config(page_title="Find", layout="wide")
st.subheader("📊 Find")

# 데이터 로드
df_stock = pd.read_json('stock.json', encoding='utf-8')
codes, items = df_stock['Code'].to_list(), df_stock['Name'].to_list()

total_count = len(items)
results = []

status_text = st.empty()  # 진행 상황 텍스트용
progress_bar = st.progress(0) # 프로그레스 바 (선택 사항)

for i, (code, item) in enumerate(zip(codes, items)):
    
    if (i + 1) % 10 == 0 or (i + 1) == total_count:
        progress_val = (i + 1) / total_count
        status_text.markdown(f"### ⏳ 현재 진행률: **{i + 1}** / {total_count} ({progress_val:.1%})")
        progress_bar.progress(progress_val)

    data = []
    for page in range(1, 20):
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f'https://finance.naver.com/item/frgn.naver?code={code}&page={page}'
        
        try:
            res = requests.get(url, headers=headers)
            tables = pd.read_html(StringIO(res.text))
            fk = tables[2]
            if fk.shape[1] < 9:
                fk = tables[3]
                
            fk = fk.dropna()
            fk.columns = ['날짜','종가','전일비','등락률','거래량','기관','외국인','보유량','보유율']
            k = fk[['날짜', '종가', '보유율']].iloc[0] 
            data.append(k)
        except Exception as e:
            continue

    if data:
        df_res = pd.DataFrame(data)
        df_res = df_res.reset_index(drop=True)
        df_res['보유율'] = df_res['보유율'].str.replace('%', '').astype(float)
        df_res['날짜'] = pd.to_datetime(df_res['날짜'])
        df_res = df_res.sort_values('날짜')

        HH = df_res['보유율'].max()
        LL = df_res['보유율'].min()
        cha = HH - LL

        idx_price = df_res['종가'].idxmin()
        idx_rate = df_res['보유율'].idxmin()

        price_in_range = 2 <= idx_price < 10
        rate_in_range = 2 <= idx_rate < 10

        if (cha > 5) and (price_in_range and rate_in_range) and (df_res['보유율'].iloc[-1] > df_res['보유율'].iloc[-2]): 
            results.append({"종목": item, "코드": code})

# 결과 저장 및 출력
results_df = pd.DataFrame(results)
if not results_df.empty:
    results_df.to_json('find.json', orient='records', force_ascii=False, indent=4)
    st.success(f"✅ 분석 완료! 총 {len(results)} 종목")
    # st.dataframe(results_df)
else:
    st.info("없음.")
