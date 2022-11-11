import pyupbit
import datetime
import time

IGNORE_TICKERS = ['KRW-XRP', 'KRW-FLOW', 'KRW-BTT'] # 제외종목

def login():
    '''
    로그인
    '''
    with open("upbitKey.txt") as f:
        lines = f.readlines()
        apiKey = lines[0].strip()
        secKey = lines[1].strip()
        
        if len(apiKey) != 40 or len(secKey) != 40:
            print("Key가 올바르지 않습니다.")
            return
        else:
            upbit = pyupbit.Upbit(apiKey, secKey)
            balance = upbit.get_balances()
            if balance == None:
                print("Key가 올바르지 않습니다.")
                return
            else:
                print("Login 성공")
            
def set_portpolio(tickers, interval):
    '''
    거래량 많은순으로 10개만 리턴
    '''
    count = 10 #갯수

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
            
def get_all_ohlcv(tickers, min_ago, prev_open, prev_high, prev_low, prev_close, prev_candle, prev_tick, interval):
    '''
    시가, 고가, 저가, 종가, 캔들 받아오기
    '''

    open, high, low, close, candle, tick = {}, {}, {}, {}, {}, {}
    
    for ticker in tickers:
        df = None
        
        while df is None:
            time.sleep(0.05)
            min_ago_time = min_ago.strftime("%Y%m%d %H:%M:00")

            df = pyupbit.get_ohlcv(ticker = ticker, interval=interval, to=min_ago_time, count=1)
            # if df is not None:
            #     df_time = str(df.index[0])
            #     now_time = now.strftime("%Y-%m-%d %H:%M:00")
            #     if df_time != now_time:
            #         df = None
                
        open[ticker] = df['open'][0] # 시가
        high[ticker] = df['high'][0] # 고가
        low[ticker] = df['low'][0] # 저가
        close[ticker] = df['close'][0] # 종가
       
        if df['close'][0] > df['open'][0]: # 양, 음봉
            candle[ticker] = True
        else:
            candle[ticker] = False
        
        if prev_tick == {}: # 틱
            tick[ticker] = 0
        else:
            tick[ticker] = calc_tick(ticker, prev_open, prev_high, prev_low, prev_close, prev_candle, prev_tick, open, high, low, close, candle, tick)
  
    return open, high, low, close, candle, tick        

def calc_tick(ticker, prev_open, prev_high, prev_low, prev_close, prev_candle, prev_tick, open, high, low, close, candle, tick):
    '''
    틱 계산
    '''
    prev_candle_length = prev_close[ticker] - prev_open[ticker] # 이전 캔들 길이
    candle_length = close[ticker] - open[ticker] # 캔들 길이
    
    if candle == True:
        # 틱 카운트 리셋이 나올수 있음
        pass
    else:
        if prev_candle == True: # 전 캔들이 양봉일 때
            if prev_candle_length < candle_length * 2:
                tick[ticker] = prev_tick[ticker] + 1
        else: # 전 캔들이 음봉일 때
            margin = prev_candle_length * 0.2
            if prev_close[ticker] - close[ticker] > margin: #
                tick[ticker] = prev_tick[ticker] + 1
    
def try_buy(tickers, tick, holdings):
    '''
    매수 시도
    '''
    for ticker in tickers:
        if tick[ticker] == 3: #3틱이면
            # current_price = 현재 값 받아서
            # 매수
            # holdings[ticker] = current_price
            return holdings
        elif:
            return holdings

def is_holdings(tickers, holdings):
    for ticker in tickers:
        if holdings[ticker] is not None:
            return True

    return False

# 로그인
login()

# upbit 모든 ticker 항목
tickers = pyupbit.get_tickers(fiat="KRW")

# 제외
for ignore_ticker in IGNORE_TICKERS:
    tickers.remove(ignore_ticker)
    
# 포트폴리오 짜기
portpolio = set_portpolio(tickers, "day")

holdings = {ticker : None for ticker in portpolio}

open, high, low, close, candle, tick = {}, {}, {}, {}, {}, {}

while True:
    now = datetime.datetime.now() # 현재 시각

    if not is_holdings(): # holding이 하나라도 있지 않으면
        if now.minute % 5 == 0 and 0 < now.second < 10: # 5분봉
            min_ago_5 = now - datetime.timedelta(minute=5) #캔들이 생긴 직후이기 때문에 5분전 데이터를 받아온다.
            open, high, low, close, candle, tick = get_all_ohlcv(portpolio, min_ago_5, 
                                                                    prev_open=open, 
                                                                    prev_high=high, 
                                                                    prev_low=low, 
                                                                    prev_close=close, 
                                                                    prev_candle=candle, 
                                                                    prev_tick=tick, 
                                                                    interval="minute5")
            
            print("open = ", open, "\n", "high = ", high, "\n", "low = ", low, "\n", "close = ", close, "\n", "candle = ", candle, "\n", "tick = ", tick)
            time.sleep(10)

        holdings = try_buy(portpolio, tick, holdings)# 5분봉 3틱룰로 매수 시도.
    elif: # holding이 있으면
        # holding이 있을 시 익절 or 순환매수매도

    time.sleep(1)
