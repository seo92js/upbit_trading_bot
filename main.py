import pyupbit
import datetime
import time

IGNORE_TICKERS = ['KRW-XRP', 'KRW-FLOW', 'KRW-BTT'] # 제외종목

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

def set_portpolio(interval):
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
        
    count = 10

    result = []
    portpolio = []
    
    for ticker in tickers:
        df = pyupbit.get_ohlcv(ticker=ticker, interval=interval, count=1)
        if df is not None:
            value = df['value'][0]
            volume = ticker, value
            result.append(volume)
        
    result.sort(key=lambda x:x[1])
    
    for i in result[-count:]:
        portpolio.append(i[0])
        
    #완만한 상승인지 하락장인지도 파악 해야할듯

    return portpolio

def get_ohlcv(ticker, t, prev_open, prev_close, prev_candle, prev_tick, interval):
    
    df = None
        
    while df is None:
        time.sleep(0.05)
        time_to = t.strftime("%Y%m%d %H:%M:%S")

        df = pyupbit.get_ohlcv(ticker = ticker, interval=interval, to=time_to, count=1)

    open = df['open'][0] # 시가
    close = df['close'][0] # 종가
    
    if df['close'][0] > df['open'][0]: # 양, 음봉
        candle = True
    else:
        candle = False
    
    tick = calc_tick(prev_open, prev_close, prev_candle, prev_tick, open, close, candle)
        
    return open, close, candle, tick

def get_all_ohlcv(tickers, t, prev_open, prev_close, prev_candle, prev_tick, interval):
    '''
    시가, 고가, 저가, 종가, 캔들 받아오기
    '''
    open, close, candle, tick = {}, {}, {}, {}
    
    for ticker in tickers:
         open[ticker], close[ticker], candle[ticker], tick[ticker] = get_ohlcv(ticker, 
                                                                               t, 
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
                #print(ticker, ", 양봉이고 전 캔들보다 김, 틱 초기화")
                return 0
        else:
            prev_candle_length = prev_open - prev_close
            
            if candle_length > prev_candle_length: # 전 캔들보다 길 때
                #print(ticker, ", 양봉이고 전 캔들보다 김, 틱 초기화")
                return 0
    else: # 음봉일 때
        candle_length = open - close
        
        if prev_candle == True: # 전 캔들이 양봉일 때
            prev_candle_length = prev_close - prev_open
            
            if prev_candle_length * 2 < candle_length: # 캔들길이가 전 캔들길이의 2배 이상일 때
                #print(ticker, ", 음봉이고 전 양봉 캔들 보다 2배 김, 틱 + 1")
                return prev_tick + 1
        else: # 전 캔들이 음봉일 때
            prev_candle_length = prev_open - prev_close
            margin = prev_candle_length * 0.4
            
            if prev_close - close > margin: # 종가가 전 캔들 종가보다 margin 이상 낮을 때
                #print(ticker, ", 음봉이고 종가가 전 캔들 종가보다 margin 이상 낮음, 틱 + 1")
                return prev_tick + 1
            
    return prev_tick
    
def try_buy(tickers, tick, holdings):
    '''
    매수 시도
    '''
    for ticker in tickers:
        if holdings[ticker] is None and tick[ticker] == 3: #3틱이면
            krw = get_krw()
            #if krw > 50000:
            #    krw = 50000
            invest_cost = int(krw / 3)
            if invest_cost > 5000:
                current_price = pyupbit.get_current_price(ticker)
                buy_result = upbit.buy_market_order(ticker, invest_cost)
                
                if buy_result is None:
                    # 재시도?
                    pass
                else:
                    holdings[ticker] = True
                    tick[ticker] = 0
                    print(ticker, " - 현재가 : ", current_price, " 매수")
            
                return True
      
    return False

def try_water(tickers, tick, holdings):
    for ticker in tickers:
            if holdings[ticker] is True and tick[ticker] == 3:
                krw = get_krw()
                #if krw > 50000:
                #    krw = 50000
                invest_cost = int(krw / 3)
                if invest_cost > 5000:
                    current_price = pyupbit.get_current_price(ticker)
                    buy_result = upbit.buy_market_order(ticker, invest_cost)
                    
                    if buy_result is None:
                        # 재시도?
                        pass
                    else:
                        holdings[ticker] = True
                        tick[ticker] = 0
                        print(ticker, " - 현재가 : ", current_price, " 물타기")
                        
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
            if avg_buy_price * 1.01 < current_price:
                unit = upbit.get_balance(ticker)
                sell_result = upbit.sell_market_order(ticker, unit)
                if sell_result is None:
                    retry_result = retry_sell(ticker, unit, 5)
                    if retry_result is None:
                        pass
                    else:
                        print(ticker, " - 매수가 : ", avg_buy_price, " 매도가 : ", current_price, " 1% 익절")
                        return True
                else:
                    print(ticker, " - 매수가 : ", avg_buy_price, " 매도가 : ", current_price, " 1% 익절")
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
portpolio = set_portpolio("minute60")

open, close, candle, tick, holdings = init(portpolio)

while True:
    now = datetime.datetime.now() # 현재 시각

    if not is_holdings(holdings): # holding이 하나라도 있지 않으면
        if now.minute % 5 == 0 and 0 < now.second < 10: # 5분봉
            print(now)
            t = now - datetime.timedelta(seconds=15) #캔들이 생긴 직후이기 때문에 전 5분봉 데이터를 받아온다.
            open, close, candle, tick = get_all_ohlcv(portpolio, t, 
                                                    prev_open=open, 
                                                    prev_close=close, 
                                                    prev_candle=candle, 
                                                    prev_tick=tick, 
                                                    #interval="minute5")
                                                    interval="minute15")
            
            print_status(portpolio, open, close, candle, tick, holdings)
            time.sleep(10)

        try_buy(portpolio, tick, holdings) # 5분봉 3틱룰로 매수 시도.
        
    else: # holding이 있으면
        if now.minute % 15 == 0 and 0 < now.second < 10: # 15분봉 으로 물타거나
            print(now)
            t = now - datetime.timedelta(seconds=15) #캔들이 생긴 직후이기 때문에 전 15분봉 데이터를 받아온다.
            open, close, candle, tick = get_all_ohlcv(portpolio, t, 
                                                    prev_open=open, 
                                                    prev_close=close, 
                                                    prev_candle=candle, 
                                                    prev_tick=tick, 
                                                    interval="minute15")
        
            print_status(portpolio, open, close, candle, tick, holdings)
            time.sleep(10)
            
        try_water(portpolio, tick, holdings) # 물타기 임시
        
        time.sleep(1)
        
        if try_sell(portpolio, holdings):
            portpolio = set_portpolio("minute60")
            open, close, candle, tick, holdings = init(portpolio)
            
        time.sleep(1)
        
    time.sleep(1)
