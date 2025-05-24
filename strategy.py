import pandas as pd
import numpy as np

def get_coin_metadata():
    """
    Specifies the target and anchor coins used in the strategy.
    """
    return {
        "target": {
            "symbol": "LDO",        # Replace with your actual target coin (must be Binance-listed, ≥$5M avg daily vol)
            "timeframe": "1H"
        },
        "anchors": [
            {"symbol": "BTC", "timeframe": "1H"},
            {"symbol": "ETH", "timeframe": "1H"}
        ]
    }

def generate_signals(candles_target: pd.DataFrame, candles_anchor: pd.DataFrame) -> pd.DataFrame:
    """
    Generate deterministic trading signals based on lagged correlation with BTC/ETH.
    Buys if the target's return is positively correlated with BTC/ETH returns from 1–3 hours ago.
    """
    df = pd.merge(
        candles_target[['timestamp', 'close']],
        candles_anchor[['timestamp', 'close_BTC', 'close_ETH']],
        on='timestamp',
        how='inner'
    )

    # Compute returns
    df['ret_target'] = df['close'].pct_change()
    df['ret_btc_lag1'] = df['close_BTC'].pct_change().shift(1)
    df['ret_eth_lag1'] = df['close_ETH'].pct_change().shift(1)
    df['ret_btc_lag2'] = df['close_BTC'].pct_change().shift(2)
    df['ret_eth_lag2'] = df['close_ETH'].pct_change().shift(2)
    df['ret_btc_lag3'] = df['close_BTC'].pct_change().shift(3)
    df['ret_eth_lag3'] = df['close_ETH'].pct_change().shift(3)

    # Simple correlation window
    window = 20

    df['corr_btc_lag'] = df['ret_target'].rolling(window).corr(df['ret_btc_lag1']) + \
                         df['ret_target'].rolling(window).corr(df['ret_btc_lag2']) + \
                         df['ret_target'].rolling(window).corr(df['ret_btc_lag3'])

    df['corr_eth_lag'] = df['ret_target'].rolling(window).corr(df['ret_eth_lag1']) + \
                         df['ret_target'].rolling(window).corr(df['ret_eth_lag2']) + \
                         df['ret_target'].rolling(window).corr(df['ret_eth_lag3'])

    # Total lagged correlation
    df['total_corr'] = df['corr_btc_lag'].fillna(0) + df['corr_eth_lag'].fillna(0)

    # Trading logic: buy if correlation is strongly positive, sell if strongly negative
    df['signal'] = 'HOLD'
    df.loc[df['total_corr'] > 1.0, 'signal'] = 'BUY'
    df.loc[df['total_corr'] < -1.0, 'signal'] = 'SELL'

    return df[['timestamp', 'signal']]
