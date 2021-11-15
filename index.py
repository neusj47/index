# 지수만들기
# 0. 대상 코드 입력
# 1. 맵핑 정보 가져오기
# 2. 지수생성 (동일가중)

import pandas as pd
import requests
import re
import FinanceDataReader as fdr
import matplotlib.pyplot as plt

start_date = '20201114'
end_date = '20211114'

df_krx = fdr.StockListing('KRX')


# 0. 대상 코드 입력
thema_info = {496: '골프',
              492: 'NFT',
              504: '요소수 관련주',
              44 : '시멘트/레미콘',
              488 : '웹툰'}


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
    return cum_idx
cum_idx = get_thema_idx(thema_info, df_krx)



plt.plot(cum_idx,label = [i for i in cum_idx.columns])
plt.legend()
