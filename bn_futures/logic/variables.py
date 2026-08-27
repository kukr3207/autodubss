"""Legacy futures adapter settings sourced from the process environment."""

import os


REALTIME_PORT = int(os.getenv("TRUEDATA_REALTIME_PORT", "8082"))
HISTORY_PORT = int(os.getenv("TRUEDATA_HISTORY_PORT", "8092"))
USERNAME = os.getenv("TRUEDATA_USERNAME", "")
PASSWORD = os.getenv("TRUEDATA_PASSWORD", "")

# bnfutures_data
BN_FUTURES_CONTRACT_FETCH_VALUES = os.getenv(
    "BN_FUTURES_CONTRACT", "BANKNIFTY22MAYFUT"
)
BN_FUTURES_CONTRACT = "NSE:" + BN_FUTURES_CONTRACT_FETCH_VALUES
