import pyupbit
import datetime
import time

IGNORE_TICKERS = ['KRW-XRP', 'KRW-FLOW', 'KRW-BTT'] # 제외종목
SPLIT_NUM = 4 # 투자금 분할
PROFIT_RATE = 1.006 # 익절
PORTPOLIO_COUNT = 10
CANDLE_MARGIN = 0.4

with open("upbitKey.txt") as f:
    lines = f.readlines()
    apiKey = lines[0].strip()
    secKey = lines[1].strip()
    
    if len(apiKey) != 40 or len(secKey) != 40:
        print("Key가 올바르지 않습니다.")
    else:
        upbit = pyupbit.Upbit(apiKey, secKey)
        balance = upbit.get_balances()
        if balance == None:
            print("Key가 올바르지 않습니다.")
        else:
            print("Login 성공")
            print(balance)

def get_krw():
    """
    보유 원화 조회.
    :return float: 보유 원화
    """
    krw = upbit.get_balance('KRW')
    return krw

def get_avg_buy_price(ticker):
    """
    ticker의 평균 매수가를 조회.
    :param str ticker: 종목
    :return float: 평균 매수가 
    """
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker[4:]:
            avg_buy_price = b['avg_buy_price']
            return float(avg_buy_price)

def init(tickers):
    open = {ticker : None for ticker in tickers}
    close = {ticker : None for ticker in tickers}
    candle = {ticker : None for ticker in tickers}
    tick = {ticker : None for ticker in tickers}
    holdings = {ticker : None for ticker in tickers}
    
    return open, close, candle, tick, holdings

def set_invest_cost():
    '''
    투자금 
    '''
    krw = get_krw()
    invest_cost = int(krw / SPLIT_NUM)
    
    return invest_cost
    
def set_portpolio():
    '''
    거래량 많은순으로 count개만 리턴
    '''
    tickers = []
    
    all_tickers = pyupbit.get_tickers(fiat="KRW", verbose=True, is_details=True)
    
    # 유의종목 제외
    for t in all_tickers:
        if t['market_warning'] == 'NONE':
            tickers.append(t['market'])
    
    # 무시종목 제외
    for ignore_ticker in IGNORE_TICKERS:
        tickers.remove(ignore_ticker)
        
    result = []
    portpolio = []
    
    for ticker in tickers:
        df = None
        while df is None:
            df = pyupbit.get_ohlcv(ticker=ticker, count=1)
            time.sleep(0.1)
        value = df['value'][0]
        volume = ticker, value
        result.append(volume)
        
    result.sort(key=lambda x:x[1])
    
    for i in result[-PORTPOLIO_COUNT:]:
        portpolio.append(i[0])
        
    #완만한 상승인지 하락장인지도 파악 해야할듯

    return portpolio

def get_ohlcv(ticker, target_time, prev_open, prev_close, prev_candle, prev_tick, interval):
    
    count = 2 # count 만큼 데이터를 가져와서 target을 찾는다. 삑사리 방지
    df = None

    target_time = target_time.strftime("%Y-%m-%d %H:%M:%S")
        
    while df is None:
        df = pyupbit.get_ohlcv(ticker = ticker, interval=interval, count=count)

    for i in range(0, count):
        data_time = df.index[i]
        if str(data_time) == target_time:
            target_index = i

    open = df.iloc[target_index]['open'] # 시가
    close = df.iloc[target_index]['close'] # 종가

    # 시가 종가 같으면 전 캔들과 묶음.
    if open == close:
        print(ticker, " - 틱 묶음")
        if prev_tick is None:
            candle = False
            tick = 0
        else:
            open = prev_open
            close = prev_close
            candle = prev_candle
            tick = prev_tick
    else:
        if close > open: # 양, 음봉
            candle = True
        else:
            candle = False
        
        print(ticker, " - 틱 계산")
        tick = calc_tick(prev_open, prev_close, prev_candle, prev_tick, open, close, candle)
        
    return open, close, candle, tick

def get_all_ohlcv(tickers, target_time, prev_open, prev_close, prev_candle, prev_tick, interval):
    '''
    시가, 고가, 저가, 종가, 캔들 받아오기
    '''
    open, close, candle, tick = {}, {}, {}, {}
    
    for ticker in tickers:
         open[ticker], close[ticker], candle[ticker], tick[ticker] = get_ohlcv(ticker, 
                                                                               target_time, 
                                                                               prev_open[ticker], 
                                                                               prev_close[ticker], 
                                                                               prev_candle[ticker], 
                                                                               prev_tick[ticker], 
                                                                               interval) 
            
    return open, close, candle, tick        

           
              

def calc_tick(prev_open, prev_close, prev_candle, prev_tick, open, close, candle):
    '''
    틱 계산
    '''
    if prev_tick is None:
        return 0
    
    if candle == True: # 양봉일 때
        candle_length = close - open
    
        if prev_candle == True:
            prev_candle_length = prev_close - prev_open
            
            if candle_length > prev_candle_length: # 전 캔들보다 길 때
                print("[틱 초기화] 양봉, 전 캔들 양봉 보다 김")
                return 0
        else:
            prev_candle_length = prev_open - prev_close
            
            if candle_length > prev_candle_length: # 전 캔들보다 길 때
                print("[틱 초기화] 양봉, 전 캔들 음봉 보다 김")
                return 0
    else: # 음봉일 때
        candle_length = open - close
        
        if prev_candle == True: # 전 캔들이 양봉일 때
            prev_candle_length = prev_close - prev_open
            margin = prev_candle_length * CANDLE_MARGIN

            if prev_open - close > margin:
                print("[틱 + 1] 음봉, 종가가 전 캔들 양봉 시가보다 margin 이상 낮음")
                return prev_tick + 1
            
        else: # 전 캔들이 음봉일 때
            prev_candle_length = prev_open - prev_close
            margin = prev_candle_length * CANDLE_MARGIN
            
            if prev_close - close > margin: # 종가가 전 캔들 종가보다 margin 이상 낮을 때
                print("[틱 + 1] 음봉, 종가가 전 캔들 음봉 종가보다 margin 이상 낮음")
                return prev_tick + 1
    
    print("[틱 변화 없음]")
    return prev_tick
    
def try_buy(tickers, tick, holdings, invest_cost):
    '''
    매수 시도
    '''
    for ticker in tickers:
        if holdings[ticker] is None and tick[ticker] == 3: #3틱이면
            if invest_cost > 5000:
                current_price = pyupbit.get_current_price(ticker)
                buy_result = upbit.buy_market_order(ticker, invest_cost)
                
                if buy_result is None:
                    # 재시도?
                    pass
                else:
                    holdings[ticker] = True
                    tick[ticker] = 0
                    print("[매수] ", ticker, " - 현재가 : ", current_price)
            
                return True
      
    return False

def try_water(tickers, tick, holdings, invest_cost):
    for ticker in tickers:
            if holdings[ticker] is True and tick[ticker] == 3:
                if invest_cost > 5000:
                    current_price = pyupbit.get_current_price(ticker)
                    buy_result = upbit.buy_market_order(ticker, invest_cost)
                    
                    if buy_result is None:
                        # 재시도?
                        pass
                    else:
                        holdings[ticker] = True
                        tick[ticker] = 0
                        print("[물타기", ticker, " - 현재가 : ", current_price)
                        
                    return True
            
    return False
    
def try_sell(tickers, holdings):
    for ticker in tickers:
        if holdings[ticker] == True:
            avg_buy_price = get_avg_buy_price(ticker)
            current_price = pyupbit.get_current_price(ticker)
            if avg_buy_price is None:
                print("avg price is None")
                return False
            if avg_buy_price * PROFIT_RATE < current_price:
                unit = upbit.get_balance(ticker)
                sell_result = upbit.sell_market_order(ticker, unit)
                if sell_result is None:
                    retry_result = retry_sell(ticker, unit, 5)
                    if retry_result is None:
                        pass
                    else:
                        print("[매도] ", ticker, " - 매수가 : ", avg_buy_price, " 매도가 : ", current_price)
                        return True
                else:
                    print("[매도] ", ticker, " - 매수가 : ", avg_buy_price, " 매도가 : ", current_price)
                    return True
            
    return False

def retry_sell(ticker, unit, count):
    result = None
    while result is None and count > 0:
        result = upbit.sell_market_order(ticker, unit)
        time.sleep(1)

        print("[retry sell] " + ticker + " : " + str(unit))
        count = count - 1
        
    return result
    
def is_holdings(holdings): 
    for holding in holdings:
        if holdings[holding] is not None:
            return True

    return False

def print_status(portpolio, open, close, candle, tick, holdings):
    for ticker in portpolio:
        if candle[ticker] == True:
            c = '\033[31m' + "양봉" + '\033[0m'
        else:
            c = '\033[34m' + "음봉" + '\033[0m'
            
        if tick[ticker] > 2:
            t = '\033[31m' + str(tick[ticker]) + '\033[0m'
        else:
            t = '\033[34m' + str(tick[ticker]) + '\033[0m'
            
        if holdings[ticker] == True:
            h = '\033[31m' + str(holdings[ticker]) + '\033[0m'
        else:
            h = '\033[34m' + str(holdings[ticker]) + '\033[0m'
            
        print(ticker, "- [시가] ", open[ticker], ", [종가] ", close[ticker], ", [양음봉] ", c, ", [틱] ", t, ", [홀딩] ", h)

# 포트폴리오 짜기
portpolio = set_portpolio()

invest_cost = set_invest_cost()

open, close, candle, tick, holdings = init(portpolio)

while True:
    now = datetime.datetime.now() # 현재 시각

    if not is_holdings(holdings): # holding이 하나라도 있지 않으면
        if now.minute % 5 == 0 and 0 < now.second < 10: # 5분봉
            
            target_time = now - datetime.timedelta(minutes=5)
            target_time = target_time.replace(second=0)
            print(now, "target_time : ", target_time)

            open, close, candle, tick = get_all_ohlcv(portpolio, target_time, 
                                                    prev_open=open, 
                                                    prev_close=close, 
                                                    prev_candle=candle, 
                                                    prev_tick=tick, 
                                                    interval="minute5")
            
            print_status(portpolio, open, close, candle, tick, holdings)
            time.sleep(10)

        try_buy(portpolio, tick, holdings, invest_cost) # 5분봉 3틱룰로 매수 시도.
        
    else: # holding이 있으면
        if now.minute % 15 == 0 and 0 < now.second < 10: # 15분봉 으로 물타거나

            target_time = now - datetime.timedelta(minutes=15)
            target_time = target_time.replace(second=0)
            print(now, "target_time : ", target_time)

            open, close, candle, tick = get_all_ohlcv(portpolio, target_time, 
                                                    prev_open=open, 
                                                    prev_close=close, 
                                                    prev_candle=candle, 
                                                    prev_tick=tick, 
                                                    interval="minute15")
        
            print_status(portpolio, open, close, candle, tick, holdings)
            time.sleep(10)
            
        try_water(portpolio, tick, holdings, invest_cost) # 물타기 임시
        
        time.sleep(1)
        
        if try_sell(portpolio, holdings):
            portpolio = set_portpolio()
            invest_cost = set_invest_cost()
            open, close, candle, tick, holdings = init(portpolio)
            
    time.sleep(1)
