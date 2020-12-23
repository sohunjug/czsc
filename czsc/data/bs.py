# coding: utf-8
import pandas as pd
import baostock as bs
from datetime import datetime, timedelta

lg = bs.login()
# 显示登陆返回信息
print('login respond error_code:' + lg.error_code)
print('login respond  error_msg:' + lg.error_msg)


def get_stock_info(symbol):
    rs = bs.query_stock_basic(code=symbol)
    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)
    return result

def get_index_stocks(symbol):
    """获取指数成份股

    :param symbol: str
        如 399300.SZ
    :param date: str or datetime
        日期，如 2020-08-08
    :return: list

    examples:
    -------
    >>> symbols1 = get_index_stocks("000300.XSHG", date="2020-07-08")
    >>> symbols2 = get_index_stocks("000300.XSHG", date=datetime.now())
    """
    industry_list = []
    if symbol == 'sz50':
        rs = bs.query_sz50_stocks()
    elif symbol == 'hs300':
        rs = bs.query_hs300_stocks()
    elif symbol == 'zz500':
        rs = bs.query_zz500_stocks()
    else:
        rs = bs.query_stock_industry()
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        industry_list.append(rs.get_row_data())
    result = pd.DataFrame(industry_list, columns=rs.fields)
    return list(set([x for x in result.code]))

def _get_start_date(end_date, freq):
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)

    if freq == '1':
        start_date = end_date - timedelta(days=30)
    elif freq == '5':
        start_date = end_date - timedelta(days=70)
    elif freq == '15':
        start_date = end_date - timedelta(days=200)
    elif freq == '30':
        start_date = end_date - timedelta(days=300)
    elif freq == '60':
        start_date = end_date - timedelta(days=500)
    elif freq == 'd':
        start_date = end_date - timedelta(weeks=500)
    elif freq == 'w':
        start_date = end_date - timedelta(weeks=1000)
    elif freq == 'm':
        start_date = end_date - timedelta(weeks=2000)
    else:
        raise ValueError("'freq' value error, current value is %s, "
                         "optional valid values are ['1min', '5min', '30min', "
                         "'D', 'W']" % freq)
    return start_date

def get_kline(symbol,  end_date, freq, start_date=None, count=None):
    """获取K线数据

    :param symbol: str
        Tushare 标的代码 + Tushare asset 代码，如 000001.SH-I
    :param start_date: datetime
        截止日期
    :param end_date: datetime
        截止日期
    :param freq: str
        K线级别，可选值 ['1min', '5min', '30min', '60min', 'D', 'W', "M"]
    :param count: int
        K线数量，最大值为 5000
    :return: pd.DataFrame

    >>> start_date = datetime.strptime("20200701", "%Y%m%d")
    >>> end_date = datetime.strptime("20200719", "%Y%m%d")
    >>> df1 = get_kline(symbol="000001.SH-I", start_date=start_date, end_date=end_date, freq="1min")
    >>> df2 = get_kline(symbol="000001.SH-I", end_date=end_date, freq="1min", count=1000)
    """
    if count:
        start_date = _get_start_date(end_date, freq)
        start_date = start_date.date().__str__()

        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)

        end_date = end_date + timedelta(days=1)
        end_date = end_date.date().__str__()

    if isinstance(end_date, datetime):
        end_date = end_date.date().__str__()

    if isinstance(start_date, datetime):
        start_date = start_date.date().__str__()

    rs = bs.query_history_k_data_plus(symbol,
        "date,code,open,high,low,close,volume,amount",
        start_date=start_date, end_date=end_date,
        frequency=freq, adjustflag="2")

    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data_list.append(rs.get_row_data())
    df = pd.DataFrame(data_list, columns=rs.fields)

    # 统一 k 线数据格式为 6 列，分别是 ["symbol", "dt", "open", "close", "high", "low", "vr"]
    if "min" in freq:
        df.rename(columns={'code': "symbol", "date": "dt", "volume": "vol"}, inplace=True)
    else:
        df.rename(columns={'code': "symbol", "date": "dt", "volume": "vol"}, inplace=True)

    df = df.dropna()
    df.drop_duplicates(subset='dt', keep='first', inplace=True)
    df.sort_values('dt', inplace=True)
    df['dt'] = df.dt.apply(str)
    df['open'] = df.open.apply(float)
    df['close'] = df.close.apply(float)
    df['high'] = df.high.apply(float)
    df['low'] = df.low.apply(float)
    df['vol'] = df.vol.apply(float)
    if freq in ('1','5','15','30','60'):
        # 清理 9:30 的空数据
        df['not_start'] = df.dt.apply(lambda x: not x.endswith("09:30:00"))
        df = df[df['not_start']]
    if count:
        df = df.tail(count)

    df.reset_index(drop=True, inplace=True)
    df.loc[:, "dt"] = pd.to_datetime(df['dt'])

    k = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]

    for col in ['open', 'close', 'high', 'low']:
        k[col] = k[col].apply(round, args=(2,))

    return k


def download_kline(symbol, freq, start_date, end_date, delta, save=True):
    """下载K线数据

    :param save:
    :param symbol:
    :param end_date:
    :param freq:
    :param start_date:
    :param delta:
    :return:

    >>> start_date = datetime.strptime("20200101", "%Y%m%d")
    >>> end_date = datetime.strptime("20200719", "%Y%m%d")
    >>> df = download_kline("000001.SH-I", "1min", start_date, end_date, delta=timedelta(days=10), save=False)
    """
    data = []
    end_dt = start_date + delta
    print("开始下载数据：{} - {} - {}".format(symbol, start_date, end_date))
    df_ = get_kline(symbol, start_date=start_date, end_date=end_dt, freq=freq)
    if not df_.empty:
        data.append(df_)

    while end_dt < end_date:
        df_ = get_kline(symbol, start_date=start_date, end_date=end_dt, freq=freq)
        if not df_.empty:
            data.append(df_)
        start_date = end_dt
        end_dt += delta
        print("当前下载进度：{} - {} - {}".format(symbol, start_date, end_dt))

    df = pd.concat(data, ignore_index=True)
    print("{} 去重前K线数量为 {}".format(symbol, len(df)))
    df.drop_duplicates(['dt'], inplace=True)
    df.sort_values('dt', ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    print("{} 去重后K线数量为 {}".format(symbol, len(df)))

    if save:
        df.to_csv(f"{symbol}_{freq}_{start_date.date()}_{end_date.date()}.csv", index=False, encoding="utf-8")
    else:
        return df
