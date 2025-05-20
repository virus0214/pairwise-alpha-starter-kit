import pandas as pd
import importlib.util
import os

ALLOWED_SIGNALS = {"BUY", "SELL", "HOLD"}
ALLOWED_IMPORTS = {"pandas", "numpy"}
MIN_AVG_VOLUME_USD = 5_000_000  # $5M threshold

def load_strategy(path='strategy.py'):
    if not os.path.exists(path):
        raise FileNotFoundError("❌ strategy.py not found.")

    spec = importlib.util.spec_from_file_location("strategy", path)
    strategy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(strategy)
    return strategy

def validate_imports(path='strategy.py'):
    with open(path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        if line.strip().startswith("import"):
            for part in line.replace("import", "").split(","):
                lib = part.strip().split(" ")[0]
                if lib not in ALLOWED_IMPORTS:
                    raise ImportError(f"❌ External library '{lib}' is not allowed. Only 'pandas' and 'numpy' are permitted.")

def generate_dummy_ohlcv(symbol, timeframe="1H", rows=30):
    ts = pd.date_range("2025-01-01", periods=rows, freq=timeframe)
    df = pd.DataFrame({
        "timestamp": ts,
        "open": 1.0,
        "high": 1.02,
        "low": 0.98,
        "close": [1.0 + 0.01*i for i in range(rows)],
        "volume": [5_000_000 / (1.0 + 0.01*i) for i in range(rows)]  # reverse-engineer so avg USD vol = ~$5M
    })
    return df


#Generate dummy anchor data
import pandas as pd

def generate_dummy_anchor_data(symbols: list, rows: int = 50) -> pd.DataFrame:
    ts = pd.date_range("2025-01-01", periods=rows, freq="1H")
    df = pd.DataFrame({"timestamp": ts})

    for anchor_metadata in symbols:
        symbol = anchor_metadata['symbol']
        timeframe = anchor_metadata['timeframe']
        
        base_close = [1.0 + 0.01 * i for i in range(rows)]
        base_volume = [5_000_000 / (1.0 + 0.01 * i) for i in range(rows)]

        # 1H data
        df[f"open_{symbol}_{timeframe}"] = 1.0
        df[f"high_{symbol}_{timeframe}"] = 1.02
        df[f"low_{symbol}_{timeframe}"] = 0.98
        df[f"close_{symbol}_{timeframe}"] = base_close
        df[f"volume_{symbol}_{timeframe}"] = base_volume

        # 4H data (sparse) - assuming 1H base data is available
        if timeframe == "1H":
            df[f"open_{symbol}_4H"] = df[f"open_{symbol}_{timeframe}"].where(df.index % 4 == 0)
            df[f"high_{symbol}_4H"] = df[f"high_{symbol}_{timeframe}"].where(df.index % 4 == 0)
            df[f"low_{symbol}_4H"] = df[f"low_{symbol}_{timeframe}"].where(df.index % 4 == 0)
            df[f"close_{symbol}_4H"] = df[f"close_{symbol}_{timeframe}"].where(df.index % 4 == 0)
            df[f"volume_{symbol}_4H"] = df[f"volume_{symbol}_{timeframe}"].where(df.index % 4 == 0)

            # 1D data (sparse) - assuming 1H base data is available
            df[f"open_{symbol}_1D"] = df[f"open_{symbol}_{timeframe}"].where(df.index % 24 == 0)
            df[f"high_{symbol}_1D"] = df[f"high_{symbol}_{timeframe}"].where(df.index % 24 == 0)
            df[f"low_{symbol}_1D"] = df[f"low_{symbol}_{timeframe}"].where(df.index % 24 == 0)
            df[f"close_{symbol}_1D"] = df[f"close_{symbol}_{timeframe}"].where(df.index % 24 == 0)
            df[f"volume_{symbol}_1D"] = df[f"volume_{symbol}_{timeframe}"].where(df.index % 24 == 0)

    return df


ALLOWED_ANCHORS = {"BTC", "ETH", "SOL"}

def validate_anchors(anchors):
    for anchor in anchors:
        symbol = anchor.get("symbol")
        if symbol not in ALLOWED_ANCHORS:
            raise ValueError(f"❌ Invalid anchor symbol: {symbol}. Allowed: {ALLOWED_ANCHORS}")
    print("✅ Anchor symbols are valid.")

def run_check():
    print("🔍 Running submission checks...")

    try:
        strategy = load_strategy()
        validate_imports()

        if not hasattr(strategy, "generate_signals"):
            raise AttributeError("❌ Missing required function: generate_signals()")

        if not hasattr(strategy, "get_coin_metadata"):
            raise AttributeError("❌ Missing required function: get_coin_metadata()")

        metadata = strategy.get_coin_metadata()
        if "target" not in metadata or "anchors" not in metadata:
            raise ValueError("❌ Metadata must include 'target' and 'anchors' keys")

        target = metadata["target"]
        if "symbol" not in target or "timeframe" not in target:
            raise ValueError("❌ 'target' must contain 'symbol' and 'timeframe'")

        for anchor in metadata["anchors"]:
            if "symbol" not in anchor or "timeframe" not in anchor:
                raise ValueError("❌ Each anchor must contain 'symbol' and 'timeframe'")

        print(f"✅ Metadata OK: Target={target['symbol']} | Anchors={[a['symbol'] for a in metadata['anchors']]}")

        validate_anchors(metadata['anchors'])

        candles_target = generate_dummy_ohlcv(target["symbol"], target["timeframe"])
        candles_anchor = generate_dummy_anchor_data(metadata["anchors"])

        # 💰 Volume check
        candles_target["usd_volume"] = candles_target["volume"] * candles_target["close"]
        avg_usd_vol = candles_target["usd_volume"].mean()
        if avg_usd_vol < MIN_AVG_VOLUME_USD:
            print(f"❌ Avg daily USD volume = ${avg_usd_vol:,.2f} — must be ≥ $5,000,000.")
        else:
            print(f"✅ Avg daily USD volume = ${avg_usd_vol:,.2f} (meets requirement)")

        try:
            signals = strategy.generate_signals(candles_target, candles_anchor)
        except Exception as e:
            error_message = str(e)
            if any(keyword in error_message for keyword in ["KeyError", "not found", "not in index", "close_", "close"]):
                anchors_str = ", ".join(f"{a['symbol']}:{a['timeframe']}" for a in metadata['anchors'])
                
                lines = [
                    "❌ Strategy is referencing incorrect column names.",
                    "",
                    "Possible causes:",
                    "1. Column format mismatch: Use format 'close_SYMBOL_TIMEFRAME' (e.g., close_BTC_1H) for Anchor Data",
                    "2. Missing timeframe in metadata: Check if timeframes in get_coin_metadata() match the columns you're trying to access",
                    "3. Merge operation issue: Ensure you're merging all required columns from candles_anchor",
                    "",
                    f"Current metadata timeframes:",
                    f"- Target: {target['timeframe']}",
                    f"- Anchors: {anchors_str}",
                    "",
                    f"Exact Error: {e}"
                ]

                print("\n".join(lines))
                raise KeyError("Column naming or merge error detected.")
            else:
                raise e


        if len(signals) == 0:
            raise ValueError("❌ generate_signals() returned an empty DataFrame")

        if not isinstance(signals, pd.DataFrame):
            raise TypeError("❌ generate_signals() must return a pandas DataFrame")

        if 'timestamp' not in signals.columns or 'signal' not in signals.columns:
            raise ValueError("❌ Output must contain 'timestamp' and 'signal' columns")

        if len(signals) != len(candles_target):
            raise ValueError("❌ Output length mismatch: signals must match length of candles_target")

        invalid = [s for s in signals['signal'] if s not in ALLOWED_SIGNALS]
        if invalid:
            raise ValueError(f"❌ Invalid signal values found: {set(invalid)}")

        print("✅ Signals are correctly formatted and aligned.")
        print("✅ All checks passed! Submission is valid. 🎉")

    except Exception as e:
        print(str(e))

if __name__ == "__main__":
    run_check()