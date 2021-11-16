# 지수만들기
# 0. 대상 코드 입력
# 1. 맵핑 정보 가져오기
# 2. 지수생성 (동일가중)
# 3. 모멘텀시그널
# 4. 수익률 산출

import pandas as pd
import requests
import re
import FinanceDataReader as fdr
import matplotlib.pyplot as plt
import datetime
import numpy as np
import warnings
warnings.filterwarnings(action='ignore')

start_date = '20191114'
end_date = '20211114'
selected_num = 2
lookback_m = 1
df_krx = fdr.StockListing('KRX')

bm = pd.DataFrame(fdr.DataReader('148020', start_date, end_date)['Close'])


# 0. 대상 코드 입력
thema_info = {496: '골프',
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
def get_thema_code(num) :
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
def get_thema_idx(thema_info, df_krx) :
    idx = pd.DataFrame()
    for key,value in thema_info.items():
        code_list = get_thema_code(key)
        df = pd.DataFrame()
        for i in range(0, len(code_list)) :
            df_temp = pd.DataFrame(fdr.DataReader(code_list[i], start_date, end_date)['Close'])
            code_info = df_krx[df_krx['Symbol'].isin(code_list)]
            df_temp.columns = code_info[code_info['Symbol']==code_list[i]].Name
            df = pd.concat([df,df_temp], axis= 1)
        df = df.pct_change().fillna(0)
        idx_temp = pd.DataFrame(df.sum(axis=1)/len(df.columns), index = df.index, columns= [value])
        idx = pd.concat([idx,idx_temp], axis =1)
    cum_idx = (1 + idx).cumprod() - 1
    return cum_idx, idx

cum_idx, idx = get_thema_idx(thema_info, df_krx)

# 3. 모멘텀 시그널 생성
def get_rm_signal(cum_idx, lookback_m, selected_num) :
    month_list = cum_idx.index.map(lambda x : datetime.datetime.strftime(x, '%Y-%m')).unique()
    rebal_date= pd.DataFrame()
    for m in month_list:
        rebal_date = rebal_date.append(cum_idx[cum_idx.index.map(lambda x : datetime.datetime.strftime(x, '%Y-%m')) == m].iloc[-1])
    rebal_date = rebal_date - rebal_date.shift(lookback_m).fillna(0)
    signal_m = pd.DataFrame((rebal_date.rank(axis=1, ascending = False) <= selected_num).applymap(lambda x : '1' if x == True else '0'))
    signal_m = signal_m.shift(1).fillna(0)
    return signal_m

signal_m = get_rm_signal(cum_idx, lookback_m, selected_num)

# 4. 수익률 산출
def get_rm_return(idx,signal_m) :
    idx = idx.rename_axis('Date').reset_index()
    idx['Date'] = pd.to_datetime(idx['Date'])
    idx['YYYY-MM'] = idx['Date'].map(lambda x : datetime.datetime.strftime(x, '%Y-%m'))
    signal_m['YYYY-MM'] =signal_m.index.map(lambda x : datetime.datetime.strftime(x, '%Y-%m'))
    signal_d = pd.merge(idx[['Date','YYYY-MM']], signal_m, on = 'YYYY-MM', how = 'left')
    signal_d.set_index(['Date'],inplace=True)
    signal_d = signal_d[thema_info.values()].astype(float)
    idx.set_index(['Date'],inplace=True)
    result = pd.DataFrame(((signal_d * idx) * 1 / selected_num).sum(axis=1))
    return result, signal_d

result = get_rm_return(idx,signal_m)[0]
signal_d = get_rm_return(idx,signal_m)[1]

# Cumulative Compounded Returns for Momentum
plt.figure(figsize=(17,7))
plt.title('Relative Momentum Return')
plt.plot((1 + result).cumprod() - 1, label = 'Momentum')
plt.plot((1 + bm['Close'].pct_change().fillna(0)).cumprod() - 1, label = 'BenchMark')
plt.legend()
plt.show()

# Cross-Sectional Weights
plt.figure(figsize=(17,7))
plt.title('Cross-Sectional Weights')
plt.stackplot(signal_d.index, np.transpose(signal_d),labels = signal_d.columns)
plt.legend()
plt.show()

