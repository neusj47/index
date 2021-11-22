# 지수만들기
# 0. 대상 코드 입력
# 1. 맵핑 정보 가져오기
# 2. 지수생성
# 3. 구성종목 조회
# 4. 시각화

import pandas as pd
import requests
import re
import FinanceDataReader as fdr
import random
import warnings
warnings.filterwarnings(action='ignore')

start_date = '20201114'
end_date = '20211114'
num = '128'
df_krx = fdr.StockListing('KRX')

# 0. 대상 코드 입력
theme_info = {
              496: '골프',
              492: 'NFT',
              503: 'LFP/리튬인산철',
              44 : '시멘트/레미콘',
              206 : '농업',
              42 :  '게임',
              488 : '웹툰',
              434 : '재택근무/스마트워크',
              498 : 'CMO(의약품 위탁생산)',
              480 : '메타버스(Metaverse)',
              265 : '모바일게임(스마트폰)',
              331 : '가상화폐(비트코인 등)',
              310 : '리츠(REITs)',
              232 : '미디어(방송/신문)',
              387 : '블록체인',
              500 : '폐배터리',
              386 : '수소차(연료전지/부품/충전소 등)',
              152 : '온실가스(탄소배출권)',
              205 : '원자력발전',
              128 : '엔터테인먼트'
             }

# 1. 맵핑 정보 가져오기
def get_theme_code(num) :
    thema_url = 'https://m.infostock.co.kr/sector/sector_detail.asp?code=' + str(num) + ''
    thema_page = requests.get(thema_url)
    code_list = []
    if thema_page.status_code == 200 :
        thema_tables = pd.read_html(thema_page.text)
        for i in range(4,len(thema_tables[0][0])) :
            code_list.append(re.sub(r'[^0-9]','',thema_tables[0][0][i]))
    else :
        pass
    return code_list

# 2. 지수 생성
def get_theme_idx(theme_info, df_krx) :
    idx = pd.DataFrame()
    for key,value in theme_info.items():
        code_list = get_theme_code(key)
        stx = pd.DataFrame()
        for i in range(0, len(code_list)) :
            stx_temp = pd.DataFrame(fdr.DataReader(code_list[i], start_date, end_date)['Close'])
            code_info = df_krx[df_krx['Symbol'].isin(code_list)]
            stx_temp.columns = code_info[code_info['Symbol']==code_list[i]].Name
            stx = pd.concat([stx,stx_temp], axis= 1)
        stx = stx.pct_change().fillna(0)
        idx_temp = pd.DataFrame(stx.sum(axis=1)/len(stx.columns), index = stx.index, columns= [value])
        idx = pd.concat([idx,idx_temp], axis =1)
    cum_idx = (1 + idx).cumprod() - 1
    return cum_idx, idx

cum_idx, idx = get_theme_idx(theme_info, df_krx)

# 3. PDF 구성종목 조회
def get_pdf_stat(num) :
    pdf_info = df_krx[df_krx['Symbol'].isin(get_theme_code(num))]
    stx = pd.DataFrame()
    for i in range(0, len(pdf_info)) :
        stx_temp = pd.DataFrame(fdr.DataReader(pdf_info.iloc[i].Symbol, start_date, end_date)['Close'])
        stx_temp.columns = [pdf_info.iloc[i].Name]
        stx = pd.concat([stx,stx_temp], axis= 1)
    stx = stx.pct_change().fillna(0)
    cum_stx = (1 + stx).cumprod() - 1
    return pdf_info, cum_stx

pdf_info, cum_stx = get_pdf_stat(num)

# 4. 시각화
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
font_location = 'C:/Windows/Fonts/NanumGothic.ttf'
font_name = fm.FontProperties(fname=font_location).get_name()
plt.rc('font', family=font_name)


# Cumulative Compounded Returns for Thema Index
plt.figure(figsize = (20,10))
for i in range(1,len(cum_idx.columns)) :
    plt.legend(
        handles=(plt.plot(cum_idx.iloc[:,i-1]*100, label = cum_idx.columns[i-1],
                 color = "#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)]))))
plt.legend()


# Cumulative Compounded Returns for Individual Stock
plt.figure(figsize = (20,10))
for i in range(1,len(cum_stx.columns)) :
    plt.legend(
        handles=(plt.plot(cum_stx.iloc[:,i-1]*100, label = cum_stx.columns[i-1],
                 color = "#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)]))))
plt.legend()