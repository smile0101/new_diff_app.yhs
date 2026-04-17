import pandas as pd
import requests
from io import StringIO
import streamlit as st

st.set_page_config(page_title="Find", layout="wide")
st.subheader("📊 Find")


df = pd.read_json('stock.json', encoding='utf-8')

codes, items = df['Code'].to_list(), df['Name'].to_list()

results = []
for i, (code, item) in enumerate(zip(codes, items)):
    print(i)
    data = []
    for i in range(1, 20):
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f'https://finance.naver.com/item/frgn.naver?code={code}&page={i}'
        res = requests.get(url, headers=headers)

        try:
            tables = pd.read_html(StringIO(res.text))
            fk = tables[2]
            if fk.shape[1] < 9:
                fk = tables[3]
                
            fk = fk.dropna()
            fk.columns = ['날짜','종가','전일비','등락률','거래량','기관','외국인','보유량','보유율']
            k = fk[['날짜', '종가', '보유율']].iloc[0] 
            data.append(k)
            
        except Exception as e:
            print(f"{i}페이지 분석 중 오류 발생: {e}")

    df = pd.DataFrame(data)
    df = df.reset_index(drop=True)
    df['보유율'] = df['보유율'].str.replace('%', '').astype(float)
    df['날짜'] = pd.to_datetime(df['날짜'])
    df = df.sort_values('날짜')
    df['날짜_str'] = df['날짜'].dt.strftime('%m-%d')

    price= df['종가'].min()
    rate = df['보유율'].min()
    HH = df['보유율'].max()
    LL = df['보유율'].min()
    cha = HH - LL

    idx_price= df['종가'].idxmin()
    idx_rate = df['보유율'].idxmin()

    price_in_range = 2 <= idx_price< 10
    rate_in_range = 2 <= idx_rate < 10

    if (cha > 5) and (price_in_range and rate_in_range)and ((df['보유율'].iloc[-1]) > (df['보유율'].iloc[-2])): 
        results.append({"종목": item, "코드": code})
results_df = pd.DataFrame(results)
file_path = 'find.json'
if not results_df.empty:
    results_df.to_json(file_path, orient='records', force_ascii=False, indent=4)