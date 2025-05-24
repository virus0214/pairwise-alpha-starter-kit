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
    Buy LDO if BTC or ETH pumped >2% exactly 4 hours ago using 1H data.
    """

    # Merge target and anchor OHLCV data on timestamp
    df = pd.merge(
        candles_target[['timestamp', 'close']],
        candles_anchor[['timestamp', 'close_BTC_1H', 'close_ETH_1H']],
        on='timestamp',
        how='inner'
    )

    # Calculate 4-hour-ago returns (shifted by 4 periods)
    df['btc_return_4h_ago'] = df['close_BTC_1H'].pct_change(periods=4)
    df['eth_return_4h_ago'] = df['close_ETH_1H'].pct_change(periods=4)

    # Generate signals
    df['signal'] = 'HOLD'
    df.loc[(df['btc_return_4h_ago'] > 0.02) | (df['eth_return_4h_ago'] > 0.02), 'signal'] = 'BUY'

    return df[['timestamp', 'signal']]
