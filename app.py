import streamlit as st
import pandas as pd
import requests
import webbrowser
import numpy as np
import FinanceDataReader as fdr
import matplotlib.pyplot as plt
from io import StringIO
from datetime import datetime, timedelta, timezone
from scipy.signal import find_peaks
import matplotlib.gridspec as gridspec
from matplotlib import font_manager, rc


# 페이지 설정
st.set_page_config(page_icon="♥", page_title="증시그래프", layout="wide")

st.title("📊 증시 대시보드")

# 이미지 데이터 딕셔너리
keys = {
    '다우(1일)': 'https://ssl.pstatic.net/imgfinance/chart/world/continent/DJI@DJI.png',
    '다우(1개월)': 'https://ssl.pstatic.net/imgfinance/chart/world/month/DJI@DJI.png',
    '나스닥(1일)': 'https://ssl.pstatic.net/imgfinance/chart/world/continent/NAS@IXIC.png',
    '나스닥(1개월)': 'https://ssl.pstatic.net/imgfinance/chart/world/month/NAS@IXIC.png',
    '코스피(1일)': 'https://t1.daumcdn.net/media/finance/chart/kr/stock/d/KGG01P.png?',
    # '코스피(1일)': 'https://t1.daumcdn.net/media/finance/chart/kr/stock/d/KGG01P.png?timestamp=202602251558',
    # '코스피(1일)': 'https://ssl.pstatic.net/imgfinance/chart/sise/siseMainKOSPI.png',
    '코스피(1개월)': 'https://t1.daumcdn.net/media/finance/chart/kr/stock/m/KGG01P.png?',
    # '코스피(3개월)': 'https://ssl.pstatic.net/imgstock/chart3/day90/KOSPI.png',
    # '코스닥(1일)': 'https://ssl.pstatic.net/imgfinance/chart/sise/siseMainKOSDAQ.png',
    '코스닥(1일)':'https://t1.daumcdn.net/media/finance/chart/kr/stock/d/QGG01P.png?timestamp=202603021557',
    '코스닥(1개월)': 'https://t1.daumcdn.net/media/finance/chart/kr/stock/m/QGG01P.png'
    # '코스닥(3개월)': 'https://ssl.pstatic.net/imgstock/chart3/day90/KOSDAQ.png?sidcode=1757835720774',
}

items = list(keys.items()) # (이름, URL) 튜플 리스트로 변환
cols_per_row = 4
for i in range(0, len(items), cols_per_row):
    row_items = items[i : i + cols_per_row]
    cols = st.columns(cols_per_row)
    
    for idx, (name, url) in enumerate(row_items):
        with cols[idx]: 
            st.caption(f"**{name}**") # 이미지 위에 제목 표시
            st.image(url, width='stretch') #`width='content'

#############################################     Graph    ####################################################
def showV( item, code, T=30, N =1 ):
    def load_data(code):
        try :
            day = (datetime.now() - timedelta(days=500)).strftime("%Y%m%d") #300
            dd = fdr.DataReader(code, day).reset_index()
            # dd = fdr.DataReader(code, '20250101', '20260118').reset_index()
            if 'index' in dd.columns:
                dd = dd.rename(columns={'index': 'Date'})
            if 'Change' in dd.columns:
                dd['Change'] = round(dd['Change'] * 100, 2)
            else:
                dd['Change'] = round(dd['Close'].pct_change() * 100, 2)
            for n in [5, 10, 20, 60, 120]:
                dd[f'MA{n}'] = dd['Close'].rolling(window=n).mean()
            dd['MA5_d'] = dd['MA5'].diff()
            dd['MA10_d'] = dd['MA10'].diff()
            end_idx = -(N - 1) if N > 1 else None
            start_idx = -(T + N - 1)

            return dd.iloc[start_idx:end_idx].copy() 
        except : print(item)

    ## 이동평균선 교차점 계산
    def find_cross_points(df, col1, col2):
        cross_points = []
        for i in range(1, len(df)):
            if (df[col1].iloc[i] > df[col2].iloc[i] and df[col1].iloc[i-1] <= df[col2].iloc[i-1]) or \
            (df[col1].iloc[i] < df[col2].iloc[i] and df[col1].iloc[i-1] >= df[col2].iloc[i-1]):
                cross_points.append(i-1)
        return cross_points

    def extract_last_cross_data(df, cross_points, col1, col2):
        if cross_points:
            last_cross_index = cross_points[-1]
            last_cross_date = df['Date'].iloc[last_cross_index]
            last_cross_value = df[[col1, col2]].iloc[last_cross_index].mean()
            return last_cross_date, last_cross_value
        return None, None

    def find_extrema(values):
        peaks, _ = find_peaks(values)
        valleys, _ = find_peaks(-values)
        return peaks, valleys

    def extract_extrema_data(df, values, peaks, valleys):
        maxi = values.iloc[peaks]
        mini = values.iloc[valleys]
        max_dates = df['Date'].iloc[peaks]
        min_dates = df['Date'].iloc[valleys]
        return maxi, mini, max_dates, min_dates
  
    d = load_data(code)
    if d is None or d.empty:
        print(f"{item}")

    d['Date'] = pd.to_datetime(d['Date']).dt.strftime('%m.%d')
    dates = d['Date'].values
    ## 3달(100일) 
    max_100 = d['Close'].max()
    min_100 = d['Close'].min()

    # ## 1주일
    d5 = d.tail(5)
    CC = d5['Close'].iloc[-1]
    max_5, min_5 = d5['Close'].max(), d5['Close'].min()
    gap_up_5 = (max_5 - CC) / CC * 100
    gap_dn_5 = (CC - min_5) / CC * 100

    values_day = d['Close']
    values_5day = d['MA5'].dropna()

    peaks_day, valleys_day = find_extrema(values_day)
    peaks_5day, valleys_5day = find_extrema(values_5day)

    maxi_day, mini_day, max_dates_day, min_dates_day = extract_extrema_data(d, values_day, peaks_day, valleys_day)
    maxi_5day, mini_5day, max_dates_5day, min_dates_5day = extract_extrema_data(d, values_5day, peaks_5day, valleys_5day)

    # 마지막 교차점
    cross_close_20_points = find_cross_points(d, 'Close', 'MA20')
    last_cross_close_20_date, last_cross_close_20_value = extract_last_cross_data(d, cross_close_20_points, 'Close', 'MA20')
    cross_close_60_points = find_cross_points(d, 'Close', 'MA60')
    last_cross_close_60_date, last_cross_close_60_value = extract_last_cross_data(d, cross_close_60_points, 'Close', 'MA60')
    cross_close_120_points = find_cross_points(d, 'Close', 'MA120')
    last_cross_close_120_date, last_cross_close_120_value = extract_last_cross_data(d, cross_close_120_points, 'Close', 'MA120')

    if d['Close'].iloc[-1] > d['MA5'].iloc[-1] :
        R1 = 'M5'
    else : 
        R1 = ""
    if d['Close'].iloc[-1] > d['MA10'].iloc[-1] :
        R2 = 'M10'
    else :
        R2 = ""
    plt.rc('font', family='Malgun Gothic')
    fig = plt.figure(figsize=(16,9)) #14, 7.5
    gs = gridspec.GridSpec(3, 1, height_ratios=[0.3, 0.21, 0.21], hspace=0.01)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1) # x축 공유
    ax3 = fig.add_subplot(gs[2], sharex=ax1) # x축 공유
    manager = plt.get_current_fig_manager()
    try:
        manager.window.wm_geometry("+10+10")  ## 위치 880 / 720
    except Exception:
        pass  

    ax1.set_title(f"{item} :{R1},{R2}")

    # mm = Tmemo(code)
    # ax1.set_title(f"{item} {mm} :{R1},{R2}")
    ax1.plot(d['Date'], d['Close'], linewidth=1.4, label='Close')
    ax1.plot(d['Date'], d['High'], '--', linewidth=1.0)
    ax1.plot(d['Date'], d['Low'], '--', linewidth=1.0)

    ax1.axhline(max_100, linestyle=':', color = 'black', linewidth=1.0)
    ax1.axhline(min_100, linestyle=':', color ='black', linewidth=1.0)

###############################################################################
    d_len = len(d)

    periods_config = [   
        {'days': 20, 'text_idx': (T-19), 'color': 'black'},
        {'days': 40, 'text_idx': (T-39), 'color': 'blue',},
        {'days': 60, 'text_idx': (T-59), 'color': 'green'},
        {'days': 80, 'text_idx': (T-79), 'color': 'black'},
        {'days': 100, 'text_idx': 1, 'color': 'black'}
    ]
    if d_len > 20:
        for config in periods_config:  ## config값 가져옴
            if d_len >= config['days']:
                d_sub = d.tail(config['days'])
                p_max = d_sub['Close'].max()
                p_min = d_sub['Close'].min()
                gap_pct = (p_max - p_min) / p_min * 100
                
                x_start = d_sub['Date'].iloc[0]
                x_end = d_sub['Date'].iloc[-1]
                ax1.hlines(y=p_max, xmin=x_start, xmax=x_end, colors=config['color'], linestyles=':', linewidth=1.0)
                ax1.hlines(y=p_min, xmin=x_start, xmax=x_end, colors=config['color'], linestyles=':', linewidth=1.0)

                try:
                    x_pos = dates[config['text_idx']]
                    ax1.annotate('', xy=(x_pos, p_max), xytext=(x_pos, p_min), 
                                arrowprops=dict(arrowstyle='<->', linewidth=1.2, edgecolor=config['color']))
                    ax1.text(x_pos, (p_max + p_min) / 2, f"{gap_pct:.0f}%", 
                            ha='center', va='center', fontsize=10, bbox=dict(boxstyle='round', fc='white', ec=config['color']))
                except IndexError:
                    pass # dates 범위를 벗어날 경우 출력 생략

    if d_len > 20:
        periods = {'1M': 20, '2M': 40, '3M': 60, '4M' : 80 }
        colors = ['#FF5733', '#33FF57', '#3357FF', "#EDF51A" ]

        for i, (label, offset) in enumerate(periods.items()):
            # 데이터 길이가 offset보다 클 때만 마커 표시
            if d_len > offset:
                idx = d_len - 1 - offset
                if idx >= 0:
                    target_date = d['Date'].iloc[idx]
                    target_price = d['Close'].iloc[idx]
                    
                    # 동그라미 마커
                    ax1.plot(target_date, target_price, 'o', markersize=12, 
                            markeredgecolor='black', markerfacecolor=colors[i], zorder=5)

    ax1.text(dates[0], max_100, f' Max {int(max_100):,}', fontsize=12, va='bottom')
    ax1.text(dates[0], min_100, f' Min {int(min_100):,}', fontsize=12, va='top')

    # 1주일(5일) 상세 표시
    x5_start, x5_end = d5['Date'].iloc[0], d5['Date'].iloc[-1]
    ax1.hlines(y=max_5, xmin=x5_start, xmax=x5_end, colors='red', linestyles='--', linewidth=1.2)
    ax1.hlines(y=min_5, xmin=x5_start, xmax=x5_end, colors='red', linestyles='--', linewidth=1.2)
    
    x5_text_pos = dates[(T-7)] ## 1주 위치 30-7 = 23
    ax1.annotate('', xy=(x5_text_pos, max_5), xytext=(x5_text_pos, CC), arrowprops=dict(arrowstyle='<->', color='red'))
    ax1.text(x5_text_pos, (max_5 + CC)/2, f'+{gap_up_5:.1f}%', ha='left', fontsize=12, bbox=dict(boxstyle='round', fc='mistyrose', alpha=0.8))
    ax1.annotate('', xy=(x5_text_pos, CC), xytext=(x5_text_pos, min_5), arrowprops=dict(arrowstyle='<->', color='blue'))
    ax1.text(x5_text_pos, (CC + min_5)/2, f'-{gap_dn_5:.1f}%', ha='right', fontsize=12, bbox=dict(boxstyle='round', fc='lightcyan', alpha=0.8))
    ax1.text(d5['Date'].iloc[4], max_5, f' {int(max_5):,}', color = 'red', fontsize=10, ha='left', va='center')
    ax1.text(d5['Date'].iloc[0], min_5, f' {int(min_5):,}', color = 'red', fontsize=10, ha='right', va='top')

    # 거래 변동률
    ax1_t = ax1.twinx()
    ax1_t.bar(d['Date'], d['Change'], alpha=0.25)

    for i in [-3,-2,-1]:
        ax1_t.text( d['Date'].iloc[i], d['Change'].iloc[i] + 0.1,str(d['Change'].iloc[i]), ha='center',
            va='bottom', fontsize=11, color='black')
    ax1_t.tick_params(axis='y', labelsize=6)

    ax1.tick_params(axis='x', rotation=45, labelsize=1)
    ax1.tick_params(axis='y', labelsize=10) # 6
    pos = ax1.get_position()
    ax1.set_position([0.06, pos.y0, 0.9, pos.height])

    # 그래프2
    ax2.plot(d['Date'], d['Close'], linestyle='--', color='pink')
    ax2.plot(d['Date'], d['MA5'], linestyle='-.', color='green', label='MA5')
    ax2.plot(d['Date'], d['MA10'], linestyle='-.', color='black', label='MA10')
    ax2.plot(d['Date'], d['MA20'], linestyle='-', color='magenta', label='MA20')
    ax2.plot(d['Date'], d['MA60'], linestyle='-', color='blue', label='MA60')
    ax2.plot(d['Date'], d['MA120'], linestyle='-', color='black', label='MA120')
    ax2.axhline(round(d['Close'].mean(),1), color='orange', linestyle='--')
    ax2.plot(min_dates_day, mini_day, "o", color='purple', markersize=5)
    ax2.plot(max_dates_day, maxi_day, "o", color='orange', markersize=5)
    ax2.plot(max_dates_5day, maxi_5day, "o", color='red', markersize=11)
    ax2.plot(min_dates_5day, mini_5day, "o", color='purple', markersize=12)
    if last_cross_close_20_date: ax2.plot(last_cross_close_20_date,last_cross_close_20_value,"d",color='magenta',markersize=12)
    if last_cross_close_60_date: ax2.plot(last_cross_close_60_date,last_cross_close_60_value,"d",color='blue',markersize=12)
    if last_cross_close_120_date: ax2.plot(last_cross_close_120_date,last_cross_close_120_value,"d",color='black',markersize=11)
    ax2.tick_params(axis='x',rotation=45,labelsize=1)
    ax2.tick_params(axis='y',labelsize=6)
    pos = ax2.get_position()
    ax2.set_position([0.06, pos.y0, 0.9, pos.height])

    # 그래프3
    ax3.plot(d['Date'], d['MA5'], label='MA5', color='red', linewidth=1.5)
    ax3.plot(d['Date'], d['MA10'], label='MA10', color='blue', linewidth=1.3)    
    ax32 = ax3.twinx()
    ax32.bar(d['Date'],d['MA5_d'], color=np.where(d['MA5_d']>=0,'royalblue','salmon'), alpha=0.5)
    ax32.axhline(y=0, color='green', linestyle='--', linewidth=2)
    ax3.tick_params(axis='x',rotation=60,labelsize=8)
    ax3.tick_params(axis='y',labelsize=6)
    ax32.tick_params(axis='y',labelsize=6)
    pos = ax3.get_position()
    ax3.set_position([0.06, pos.y0, 0.9, pos.height])
    plt.setp(ax1.get_xticklabels(), visible=False) # ax1 x축 라벨 숨김
    plt.setp(ax2.get_xticklabels(), visible=False) # ax2 x축 라벨 숨김
    ax3.tick_params(axis='x', rotation=45, labelsize=8)
    return fig

kos, kod = st.columns([2, 2])

with kos:
    fig = showV('코스피', '^ks11')
    st.pyplot(fig)

with kod:
    fig = showV('코스닥', '^KQ11')
    st.pyplot(fig)
st.divider()

keys1 = {
    '투자자(코스피)' : 'https://ssl.pstatic.net/imgfinance/chart/sise/trendUitradeDayKOSPI.png?sid=1697448197552',
    '투자자(코스닥)' : 'https://ssl.pstatic.net/imgfinance/chart/sise/trendUitradeDayKOSDAQ.png?sid=1697448286377',
    '증시자금' : 'https://ssl.pstatic.net/imgfinance/chart/sise/deposit_customer_deposit.png',
    'BTC(1일)' : 'https://imagechart.upbit.com/d/mini/BTC.png',
    '환율(1개월)': 'https://ssl.pstatic.net/imgfinance/chart/marketindex/area/month/FX_USDKRW.png',
    '엔화(1개월)' : 'https://ssl.pstatic.net/imgfinance/chart/marketindex/area/month/FX_JPYKRW.png',
    'WTI(1개월)' : 'https://ssl.pstatic.net/imgfinance/chart/marketindex/area/month/OIL_CL.png',    
    '국내금' :'https://ssl.pstatic.net/imgfinance/chart/marketindex/area/month/CMDT_GC.png',
    '구리' : 'https://ssl.pstatic.net/imgfinance/chart/marketindex/area/month/CMDT_CDY.png',
    '일본중시': 'https://ssl.pstatic.net/imgfinance/chart/world/month/NII@NI225.png',
    '항생증시' : 'https://ssl.pstatic.net/imgfinance/chart/world/month/HSI@HSI.png',
    '인도증시'  : 'https://ssl.pstatic.net/imgfinance/chart/world/month3/INI@BSE30.png'}

items = list(keys1.items()) # (이름, URL) 튜플 리스트로 변환
cols_per_row = 4
for i in range(0, len(items), cols_per_row):
    row_items = items[i : i + cols_per_row]
    cols = st.columns(cols_per_row)
    
    for idx, (name, url) in enumerate(row_items):
        with cols[idx]: 
            st.caption(f"**{name}**") # 이미지 위에 제목 표시
            st.image(url, width='stretch') #`width='content'
st.divider()

def graph_n(item, d):
    # 이동평균선 간 교차점 찾기 함수
    def find_cross_points(df, col1, col2):
        cross_points = []
        for i in range(1, len(df)):
            if (df[col1].iloc[i] > df[col2].iloc[i] and df[col1].iloc[i-1] <= df[col2].iloc[i-1]) or \
            (df[col1].iloc[i] < df[col2].iloc[i] and df[col1].iloc[i-1] >= df[col2].iloc[i-1]):
                cross_points.append(i - 1)  # 교차점 날짜를 이전 인덱스로 설정
        return cross_points

    # 마지막 교차점만 추출하는 함수
    def extract_last_cross_data(df, cross_points, col1, col2):
        if cross_points:
            last_cross_index = cross_points[-1]
            last_cross_date = df['Date'].iloc[last_cross_index]
            last_cross_value = df[[col1, col2]].iloc[last_cross_index].mean()
            return last_cross_date, last_cross_value
        return None, None

    # 피크와 밸리 계산 함수
    def find_extrema(values):
        peaks, _ = find_peaks(values)
        valleys, _ = find_peaks(-values)
        return peaks, valleys

    # 최대/최소값과 날짜 추출
    def extract_extrema_data(df, values, peaks, valleys):
        maxi = values.iloc[peaks]
        mini = values.iloc[valleys]
        max_dates = df['Date'].iloc[peaks]
        min_dates = df['Date'].iloc[valleys]
        return maxi, mini, max_dates, min_dates

    values_day = d['Close']
    values_5day = d['MA5'].dropna()

    peaks_day, valleys_day = find_extrema(values_day)
    peaks_5day, valleys_5day = find_extrema(values_5day)

    # 최대/최소값과 날짜 추출
    maxi_day, mini_day, max_dates_day, min_dates_day = extract_extrema_data(d, values_day, peaks_day, valleys_day)
    maxi_5day, mini_5day, max_dates_5day, min_dates_5day = extract_extrema_data(d, values_5day, peaks_5day, valleys_5day)
    # 이동평균선 교차점 계산 및 마지막 교차점 추출
    cross_close_20_points = find_cross_points(d, 'Close', 'MA20')
    last_cross_close_20_date, last_cross_close_20_value = extract_last_cross_data(d, cross_close_20_points, 'Close', 'MA20')

    cross_close_60_points = find_cross_points(d, 'Close', 'MA60')
    last_cross_close_60_date, last_cross_close_60_value = extract_last_cross_data(d, cross_close_60_points, 'Close', 'MA60')

    rc('font', family='Malgun Gothic')
    fig, axs = plt.subplots(3, 1, figsize=(11, 7), sharex=True)  # 12, 9.5 / 7.5, 7
    ax2, ax3, ax4 = axs

    CC = d['Close'].iloc[-1]
    if item == '비트코인':
        RR = round((CC-165388411)/165388411*100,1)
        
    else :
        RR = round((CC-201864)/201864*100,1)
    Mo = int(RR * 20)

    ax2.set_title(f"{item} / {RR}%,  {Mo}"  , fontsize=14, color="blue")

    # [1] HL 그래프 (맨 위)
    ax2.plot(d['Date'], d['Close'], label='Close', color='blue', linewidth=1.5)
    ax2.plot(d['Date'], d['High'], label='High', color='green', linestyle='--', linewidth=1.2)
    ax2.plot(d['Date'], d['Low'], label='Low', color='red', linestyle='--', linewidth=1.2)
    for j in range(len(d)):
        ax2.axvline(x=d['Date'].iloc[j], color='lightgray', linestyle=':', linewidth=0.8, alpha=0.8)
    ax2_twin = ax2.twinx()
    ax2_twin.bar(d['Date'], d['Change'], color='gray', alpha=0.3, label='Change (%)')
    for i in [-3,-2,-1]:
        ax2_twin.text( d['Date'].iloc[i], d['Change'].iloc[i] + 0.1,str(d['Change'].iloc[i]), ha='center',
            va='bottom', fontsize=10, color='black',fontweight='bold')

    # [2] 이동평균선 그래프 (가운데)
    ax3.plot(d['Date'], d['Close'], linestyle='--', color='pink')
    ax3.plot(d['Date'], d['MA5'], linestyle='-.', color='green', label='5일')
    ax3.plot(d['Date'], d['MA20'], linestyle='-', color='magenta')
    ax3.plot(d['Date'], d['MA60'], linestyle='-', color='blue')
    ax3.axhline(round(d['Close'].mean(), 1), color='orange', linestyle='--')

    ax3.plot(min_dates_day, mini_day, "o", color='purple', markersize=5)
    ax3.plot(max_dates_day, maxi_day, "o", color='orange', markersize=5)
    ax3.plot(max_dates_5day, maxi_5day, "o", color='red', markersize=11)
    ax3.plot(min_dates_5day, mini_5day, "o", color='purple', markersize=12)

    if last_cross_close_20_date:
        ax3.plot(last_cross_close_20_date, last_cross_close_20_value, "d", color='magenta', markersize=12, label='20일')
    if last_cross_close_60_date:
        ax3.plot(last_cross_close_60_date, last_cross_close_60_value, "d", color='blue', markersize=12, label='60일')

    for j in range(len(d)):
        ax3.axvline(x=d['Date'].iloc[j], color='lightgray', linestyle=':', linewidth=1)

    ax3.legend(loc='upper left')

    ax4.plot(d['Date'], d['MA5'], label='5일', color='red', linewidth=1.5)
    ax4.plot(d['Date'], d['MA10'], label='10일', color='blue', linewidth=1.3)
    ax4.axhline(y=d['MA5'].mean(), color='green', linestyle='--', linewidth=2)
    ax42 = ax4.twinx()
    ax42.bar(d['Date'],d['MA5_d'], color=np.where(d['MA5_d'] >= 0, 'royalblue', 'salmon'), alpha=0.5 )
    ax4.legend(loc='upper left')

    for j in range(len(d)):
        ax4.axvline(x=d['Date'].iloc[j], color='lightgray', linestyle=':', linewidth=1)
    ax4.tick_params(axis='x', rotation=45)
    for label in ax4.get_xticklabels():
        label.set_fontsize(6.6)
    # ax4.legend(loc='upper left')
    ax2.tick_params(axis='y', labelsize=6)
    ax3.tick_params(axis='y', labelsize=6)
    ax4.tick_params(axis='y', labelsize=6)

    plt.rcParams['axes.unicode_minus'] = False
    return fig

def Gold( ):
    headers = {"User-Agent": "Mozilla/5.0"}
    all_data = [] 
    for page in range(1, 20):
        url = f'https://finance.naver.com/marketindex/goldDailyQuote.naver?&page={page}'
        res = requests.get(url, headers=headers)
        df = pd.read_html(StringIO(res.text))[0]
        all_data.append(df)
        dfv = pd.concat(all_data, ignore_index=True)
        dfv.columns = dfv.columns.droplevel(0)
        dfv.columns = ['Date','Close','bi','High','Low','sen','rec','F','G']
        dfv["Date"] = pd.to_datetime(dfv["Date"])
        dfv = dfv.sort_values(by="Date")
        dfv['Change'] = round(dfv['Close'].pct_change() * 100, 2)
        for n in [5, 10, 20, 60]:
            dfv[f'MA{n}'] = dfv['Close'].rolling(window=n).mean()
        dfv['MA5_d'] = dfv['MA5'].diff()
        dfv['MA10_d'] = dfv['MA10'].diff()
        d = dfv.tail(35).copy()
        d['Date'] = pd.to_datetime(d['Date']).dt.strftime('%m.%d')
    return d

def bit () :
    url = "https://api.upbit.com/v1/candles/days"

    start = (datetime.now() - timedelta(days=1500)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")

    start_datetime = datetime.strptime(start, "%Y-%m-%d")
    end_datetime = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)  # 끝 날짜 포함

    all_data = []
    while start_datetime <= end_datetime:
        # KST -> UTC 변환
        to_datetime_utc = end_datetime.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        params = {
            'market': 'KRW-BTC',
            'to': to_datetime_utc,
            'count': 200
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"API 요청 실패: {response.status_code}, {response.text}")

        data = response.json()
        if not data:
            break

        for item in data:
            all_data.append({
                'Date': item['candle_date_time_kst'][:10],
                'Open': item['opening_price'],
                'High': item['high_price'],
                'Low': item['low_price'],
                'Close': item['trade_price'],
                'volume': item['candle_acc_trade_volume']
            })

        # 데이터의 마지막 날짜를 기준으로 end_datetime 업데이트
        last_date = datetime.strptime(data[-1]['candle_date_time_kst'], "%Y-%m-%dT%H:%M:%S")
        end_datetime = last_date - timedelta(days=1)

    # DataFrame 생성
    df = pd.DataFrame(all_data)
    df = df.sort_values(by='Date')
    df['Change'] = round(df['Close'].pct_change() * 100, 2)
    for n in [5, 10, 20, 60]:
        df[f'MA{n}'] = df['Close'].rolling(window=n).mean()
    df['MA5_d'] = df['MA5'].diff()
    df['MA10_d'] = df['MA10'].diff()
    d = df.tail(35).copy()
    d['Date'] = pd.to_datetime(d['Date']).dt.strftime('%m.%d')
    return d

bb, gg = st.columns([2, 2])

with bb:
    d = bit()
    fig = graph_n('비트코인',d)
    st.pyplot(fig)

with gg:
    go = Gold()
    fig = graph_n('골드',go)
    st.pyplot(fig)

K = 2
if K == 1 :

    if 'browser_opened' not in st.session_state:
        st.session_state['browser_opened'] = False

    # 2. 실행 로직: 아직 열린 적이 없다면 실행
    if not st.session_state['browser_opened']:
        webbrowser.open('https://markets.hankyung.com/marketmap/kospi')# 코스피맵
        webbrowser.open('https://markets.hankyung.com/marketmap/kosdaq')
        webbrowser.open('https://finviz.com/map.ashx')# S&p
        webbrowser.open('https://www.thinkpool.com/') ##think
        webbrowser.open('https://stockplus.com/m/news/popular') # 증권플러스 
        webbrowser.open('https://www.thinkpool.com/analysis/sise') # 이슈종목
        webbrowser.open('https://seibro.or.kr/websquare/control.jsp?w2xPath=/IPORTAL/user/company/BIP_CNTS01021V.xml&menuNo=19') # 배당, 유상증자
        webbrowser.open('https://finance.naver.com/sise/sise_deal_rank.naver') # 외인 순매수
        # 상태를 True로 변경하여 다시 실행되지 않도록 방지
        st.session_state['browser_opened'] = True


