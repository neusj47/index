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
import datetime
warnings.filterwarnings(action='ignore')

start_date = '20201114'
end_date = '20211129'
num = '152'
df_krx = fdr.StockListing('KRX')
tgt_n = 5

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


# 4. Top 종목 월별 성과
def get_top_pick(num, start_date, end_date, tgt_n) :
    code_list = get_theme_code(num)
    stk = pd.DataFrame()
    for i in range(0, len(code_list)):
        stk_temp = pd.DataFrame(fdr.DataReader(code_list[i], start_date, end_date)['Close'])
        code_info = df_krx[df_krx['Symbol'].isin(code_list)]
        stk_temp.columns = code_info[code_info['Symbol'] == code_list[i]].Name
        stk = pd.concat([stk, stk_temp], axis=1)
    month_list = stk.index.map(lambda x: datetime.datetime.strftime(x, '%Y-%m')).unique()
    rebal_date = pd.DataFrame()
    for m in month_list:
        rebal_date = rebal_date.append(
            stk[stk.index.map(lambda x: datetime.datetime.strftime(x, '%Y-%m')) == m].iloc[-1])
    rebal_date = rebal_date / rebal_date.shift(1) - 1
    rebal_date = rebal_date.fillna(0)
    rebal_date = rebal_date[1:len(rebal_date)]
    signal_m = pd.DataFrame((rebal_date.rank(axis=1, ascending=False) <= tgt_n).applymap(lambda x: '1' if x == True else '0'))
    df_stk = pd.DataFrame(index=signal_m.index, columns=list(range(1, tgt_n + 1)))
    df_rtn = pd.DataFrame(index=signal_m.index, columns=list(range(1, tgt_n + 1)))
    for s in range(0, len(signal_m)):
        df_stk.iloc[s] = signal_m.columns[signal_m.iloc[s] == '1']
        df_rtn.iloc[s] = rebal_date[signal_m.columns[signal_m.iloc[s] == '1']].iloc[s]
    df_rtn_t = pd.DataFrame(columns=signal_m.index)
    df_stk_t = pd.DataFrame(columns=signal_m.index)
    for i in range(0, len(df_rtn)):
        df_rtn_t.iloc[:, i] = df_rtn.T.sort_values(by=df_rtn.T.columns[i], ascending=False).iloc[:, i].reset_index(drop=True)
        df_stk_t.iloc[:, i] = df_stk.iloc[i][
            df_rtn.T.sort_values(by=df_rtn.T.columns[i], ascending=False).iloc[:, i].index].reset_index(drop=True)
    df_rtn_t.columns = df_rtn_t.columns.strftime('%Y%m%d')
    df_stk_t.columns = df_stk_t.columns.strftime('%Y%m%d')
    df_rtn_t = round(df_rtn_t,3)
    df_stk_t = round(df_stk_t, 3)
    return df_rtn_t, df_stk_t

df_rtn_t, df_stk_t = get_top_pick(num, start_date, end_date, tgt_n)



# 5. 시각화
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