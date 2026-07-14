import matplotlib
matplotlib.use('Agg')

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------
# Load CSV
# -----------------------
df = pd.read_csv("data/nifty.csv")
df["date"] = pd.to_datetime(df["date"])
df.set_index("date", inplace=True)
df.sort_index(inplace=True)

# Pre‑compute sorted unique dates for next/prev lookups
all_dates = df.index.normalize().unique().sort_values()


# -----------------------
# Home
# -----------------------
@app.get("/")
def home():
    return FileResponse("templates/index.html")


# -----------------------
# Years, Months, Days
# -----------------------
@app.get("/years")
def get_years():
    return sorted(df.index.year.unique().tolist())


@app.get("/months/{year}")
def get_months(year: int):
    return sorted(df[df.index.year == year].index.month.unique().tolist())


@app.get("/days/{year}/{month}")
def get_days(year: int, month: int):
    temp = df[(df.index.year == year) & (df.index.month == month)]
    return sorted(temp.index.day.unique().tolist())


# -----------------------
# Next / Previous Day endpoints
# -----------------------
def date_to_dict(dt):
    return {"year": dt.year, "month": dt.month, "day": dt.day}


@app.get("/next_day/{year}/{month}/{day}")
def get_next_day(year: int, month: int, day: int):
    current = pd.Timestamp(year, month, day)
    # Find position of current date in all_dates
    # Use searchsorted to find insertion index
    idx = all_dates.searchsorted(current)
    if idx < len(all_dates) - 1:
        next_dt = all_dates[idx + 1]
        return date_to_dict(next_dt)
    return JSONResponse({"error": "No next day"}, status_code=404)


@app.get("/prev_day/{year}/{month}/{day}")
def get_prev_day(year: int, month: int, day: int):
    current = pd.Timestamp(year, month, day)
    idx = all_dates.searchsorted(current)
    if idx > 0:
        prev_dt = all_dates[idx - 1]
        return date_to_dict(prev_dt)
    return JSONResponse({"error": "No previous day"}, status_code=404)


# -----------------------
# Chart request and generation
# -----------------------
class ChartRequest(BaseModel):
    year: int
    month: int
    day: int
    timeframe: int


@app.post("/chart")
def create_chart(req: ChartRequest):
    day_df = df[
        (df.index.year == req.year) &
        (df.index.month == req.month) &
        (df.index.day == req.day)
    ]
    if day_df.empty:
        return JSONResponse(
            {"error": "No data found for the selected date"},
            status_code=404
        )

    tf = f"{req.timeframe}min"
    ohlc = day_df.resample(tf).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    })
    ohlc.dropna(inplace=True)

    filename = "static/charts/chart.png"

    # Custom market colors
    mc = mpf.make_marketcolors(
        up='#26a69a',
        down='#ef5350',
        edge='inherit',
        wick={'up': '#26a69a', 'down': '#ef5350'},
        volume={'up': '#26a69a', 'down': '#ef5350'},
        ohlc={'up': '#26a69a', 'down': '#ef5350'}
    )

    # Dark style with white text
    s = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle='--',
        gridcolor='#30363d',
        facecolor='#0d1117',
        figcolor='#0d1117',
        edgecolor='#21262d',
        y_on_right=False,
        rc={
            'font.size': 10,
            'text.color': 'white',
            'axes.labelcolor': 'white',
            'xtick.color': 'white',
            'ytick.color': 'white',
            'axes.edgecolor': 'white',
            'axes.titlecolor': 'white',
            'grid.color': '#30363d'
        }
    )

    date_str = day_df.index[0].strftime('%Y-%m-%d')
    title = f"NIFTY 50 – {date_str}  ({req.timeframe}‑min candles)"

    mpf.plot(
        ohlc,
        type="candle",
        style=s,
        volume=True,
        figsize=(14, 8),
        tight_layout=True,
        title=title,
        ylabel='Price',
        ylabel_lower='Volume',
        savefig=filename,
        returnfig=False
    )
    plt.close()
    return {"image": "/static/charts/chart.png"}
