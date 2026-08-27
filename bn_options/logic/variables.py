"""Legacy options adapter settings sourced from the process environment."""

import os


REALTIME_PORT = int(os.getenv("TRUEDATA_REALTIME_PORT", "8082"))
HISTORY_PORT = int(os.getenv("TRUEDATA_HISTORY_PORT", "8092"))
USERNAME = os.getenv("TRUEDATA_USERNAME", "")
PASSWORD = os.getenv("TRUEDATA_PASSWORD", "")

# bnfutures_data
BANKNIFTY_OPTIONS_CONTRACT_YEAR_MONTH_DATE = os.getenv(
    "BANKNIFTY_OPTIONS_PREFIX", "NSE:BANKNIFTY22210"
)
OPTIONS_DEPTH = int(os.getenv("BANKNIFTY_OPTIONS_DEPTH", "500"))
