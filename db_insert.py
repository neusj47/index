import pandas as pd
from datetime import datetime, timedelta
from pykrx import stock
import requests
import FinanceDataReader as fdr
import pymysql
import calendar
from threading import Timer


class DBUpdater:
    def __init__(self):
        self.conn = pymysql.connect(host='localhost', user='root', password='sjyoo1~', db='domestic', charset='utf8')
        with self.conn.cursor() as curs:
            sql = """
                  CREATE TABLE IF NOT EXISTS daily_idx_rtn (
                      Last_Update Date,
                      Theme varchar(50),
                      Rtn float,
                      PRIMARY KEY (last_update, Theme)
                      )
                  """
            curs.execute(sql)
        self.conn.commit()

    def get_holdings(self, fn_theme):
        theme_url = "http://www.fnindex.co.kr/detail/excel/FI00.WLT.{}/TIS/1Y/FnGuide%20{}/Price%20Index/Non-Ceiling"
        df = pd.DataFrame()
        for key, value in fn_theme.items():
            try:
                file_name_theme = theme_url.format(key, value).split('/')[-3].split('%20')[1] +'.xlsx'
                with open(file_path + file_name_theme, 'wb') as file:
                    response = requests.get(theme_url.format(key, value))
                    if response.status_code == 200:
                        file.write(response.content)
                df_temp = pd.read_excel(file_path + "{}.xlsx".format(value), sheet_name='Constituents',
                                        index_col=0).fillna(0)
                df_temp = df_temp.iloc[6:len(df_temp)]
                df_temp['theme'] = value
                df_temp.reset_index(inplace=True)
                df_temp.columns = ['Sector', 'IndustryGroup', 'Code', 'Name', 'Theme']
                df_temp['Last_Update'] = stddate
                df_temp = df_temp[['Last_Update', 'Theme', 'Code', 'Name', 'Sector', 'IndustryGroup']]
                df = df.append(df_temp)
            except Exception as e:
                print(key, value, '오류발생', '오류:', str(e))
        df.Code = df.Code.str.split('A').str[1]
        return df

    def get_stk_wgt(self, fn_theme, stddate) :
        df = self.get_holdings(fn_theme)
        df_mkt = stock.get_market_cap_by_ticker(stddate).reset_index().rename(columns = {'티커':'Code'})
        df = pd.merge(df, df_mkt, how = 'inner', on ='Code')
        df_temp = pd.DataFrame(df.groupby('Theme').apply(lambda x : x.시가총액/x.시가총액.sum())).reset_index().set_index('level_1')['시가총액']
        df = pd.merge(df, df_temp, left_index=True, right_index=True,how='left')
        df_wgt = df.rename(columns = {'종가':'Price_Adj','시가총액_x':'Marketcap','거래량':'TQty','거래대금':'TAmt','상장주식수':'Qty','시가총액_y':'Wgt'})
        return df_wgt

    def insert_into_DB(self, fn_theme, stddate, prevbdate):
        if stock.get_nearest_business_day_in_a_week(stddate) == stddate :
            df_wgt = self.get_stk_wgt(fn_theme, stddate)
            theme_list = df_wgt.Theme.unique().tolist()
            with self.conn.cursor() as curs:
                sql = "SELECT max(last_update) from daily_idx_rtn"
                curs.execute(sql)
                rs = curs.fetchone()  # last_update
                today = datetime.today().strftime('%Y-%m-%d')
                if rs[0] == None or rs[0].strftime('%Y-%m-%d') < today:
                    for s in range(0, len(theme_list)):
                        df_theme = df_wgt[df_wgt['Theme'] == theme_list[s]]
                        code_list = df_theme.Code.tolist()
                        wgt_list = df_theme.Wgt.tolist()
                        stk = pd.DataFrame()
                        for i in range(0, len(code_list)):
                            stk_temp = pd.DataFrame(fdr.DataReader(code_list[i], prevbdate, stddate)['Close'])
                            stk = pd.concat([stk, stk_temp], axis=1)
                        stk = stk.pct_change().dropna(axis=0)
                        last_update = stddate
                        theme = theme_list[s]
                        rtn = sum(stk.iloc[0] * wgt_list)
                        sql = f"INSERT INTO daily_idx_rtn (Last_Update, Theme, Rtn) " \
                              f"VALUES ('{last_update}', '{theme}', '{rtn}')"
                        curs.execute(sql)
                        today = datetime.today().strftime('%Y-%m-%d')
                        print(f"[{today}] #{s + 1:04d} INSERT INTO daily_idx_rtn " \
                              f"VALUES ({theme}, {stddate})")
                        self.conn.commit()

    def __del__(self):
        self.conn.close()

    def execute_daily(self,fn_theme,stddate,prevbdate):
        self.insert_into_DB(fn_theme, stddate, prevbdate)
        tmnow = datetime.now()
        lastday = calendar.monthrange(tmnow.year, tmnow.month)[1]
        if tmnow.month == 12 and tmnow.day == lastday:
            tmnext = tmnow.replace(year=tmnow.year + 1, month=1, day=1,
                                   hour=17, minute=0, second=0)
        elif tmnow.day == lastday:
            tmnext = tmnow.replace(month=tmnow.month + 1, day=1, hour=17,
                                   minute=0, second=0)
        else:
            tmnext = tmnow.replace(day=tmnow.day + 1, hour=17, minute=0,
                                   second=0)
        tmdiff = tmnext - tmnow
        secs = tmdiff.seconds
        t = Timer(secs, self.execute_daily)
        print("Waiting for next update ({}) ... ".format(tmnext.strftime('%Y-%m-%d %H:%M')))
        t.start()

if __name__ == '__main__':
    file_path = "C:/Users/ysj/Desktop/path/"
    stddate = datetime.now().strftime('%Y%m%d')
    prevbdate = stock.get_nearest_business_day_in_a_week(datetime.strftime(datetime.strptime(stddate, "%Y%m%d") - timedelta(days=1), "%Y%m%d"))
    fn_theme = {
        'HSS': '핵심소비재',
        'CYC': '경기주도주',
        'DEF': '경기방어주',
        'CHC': '중국내수테마',
        'HST': '성장소비주도',
        'HCY': '주도업종',
        'SBI': '2차전지 산업',
        'SBD': 'TOP 5 PLUS',
        'NAG': '농업융복합산업',
        'NCE': 'E커머스',
        'KIT': 'IT플러스',
        'KDS': '내수주플러스',
        'SRE': '부동산인컴',
        'TTP': 'Top 10 Plus',
        'KBU': '언택트',
        'KBH': '수소 경제 테마',
        'KB5': '5G 테크',
        'SKI': 'K-이노베이션',
        'NH5': '5G 산업',
        'SND': 'K-뉴딜 디지털 플러스',
        'NHV': '전기&수소차',
        'HIB': 'IT바이오',
        'KBP': 'BBIG 플러스',
        'YKN': '코리아 뉴딜 BBIG',
        'MRN': '신재생에너지',
        'NGE': '친환경에너지',
        'MSE': '반도체 TOP',
        'MHC': '수소퓨처모빌리티',
        'MMC': '미디어컨텐츠 TOP3 PLUS',
        'HTN': '5G 플러스',
        'REP': 'K-신재생에너지 플러스',
        'SAV': 'K-미래차',
        'NHS': 'K-반도체',
        'NHG': 'K-게임',
        'NHM': 'K-POP & 미디어',
        'HGV': '친환경 자동차 밸류체인',
        'NMS': '시스템반도체',
        'SMK': 'TOP10 동일가중',
        'TMT': 'TMT',
        'SCM': '스마트커머스',
        'SWT': '웹툰&드라마',
        'KBC': '컨택트대표',
        'SES': 'K-친환경 선박',
        'MVS': 'K-메타버스',
        'NMV': 'K-메타버스 MZ',
        'ASP': '플랫폼',
        'MVT': '메타버스테마',
        'NGF': '골프 테마',
        'HMZ': 'MZ 소비',
        'NHK': '네카하 파트너스',
        'TKC': 'K-컬처'
    }
    DBUpdater().execute_daily(fn_theme,stddate,prevbdate)
