# daybasedchartviewer
nifty chart  filtered as per date time frame

####### code app.py
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




    #### index.html
    <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Candlestick Viewer</title>
  <style>
    /* ----- Reset & Base ----- */
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: #0d1117;
      color: #c9d1d9;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 20px;
    }
    .container {
      max-width: 1300px;
      width: 100%;
      background: #161b22;
      border-radius: 24px;
      padding: 30px 35px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
      border: 1px solid #30363d;
    }
    h1 {
      font-size: 28px;
      font-weight: 600;
      margin-bottom: 8px;
      background: linear-gradient(135deg, #f0e6d0, #f5c842);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .subtitle {
      color: #8b949e;
      font-size: 14px;
      margin-bottom: 25px;
      border-bottom: 1px solid #21262d;
      padding-bottom: 12px;
    }
    /* ----- Controls ----- */
    .controls {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      gap: 15px 25px;
      margin-bottom: 25px;
    }
    .control-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1 0 auto;
    }
    .control-group label {
      font-size: 12px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #8b949e;
    }
    select {
      background: #0d1117;
      border: 1px solid #30363d;
      color: #c9d1d9;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 14px;
      min-width: 100px;
      cursor: pointer;
      transition: 0.2s;
    }
    select:hover,
    select:focus {
      border-color: #58a6ff;
      outline: none;
      box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.2);
    }
    /* Button group */
    .btn-group {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    .btn {
      background: #21262d;
      border: none;
      color: #c9d1d9;
      padding: 8px 16px;
      border-radius: 8px;
      font-weight: 500;
      font-size: 14px;
      cursor: pointer;
      transition: 0.2s;
      height: 40px;
      white-space: nowrap;
      border: 1px solid #30363d;
    }
    .btn:hover:not(:disabled) {
      background: #30363d;
      border-color: #58a6ff;
    }
    .btn:disabled {
      opacity: 0.3;
      cursor: not-allowed;
    }
    .btn-load {
      background: #238636;
      color: #fff;
      border: none;
      padding: 8px 28px;
    }
    .btn-load:hover:not(:disabled) {
      background: #2ea043;
    }
    .btn-load:active:not(:disabled) {
      transform: scale(0.96);
    }
    .selected-date {
      font-size: 14px;
      color: #8b949e;
      margin-left: 5px;
      align-self: flex-end;
      padding-bottom: 2px;
    }
    /* ----- Chart Area ----- */
    .chart-wrapper {
      background: #0d1117;
      border-radius: 16px;
      border: 1px solid #21262d;
      padding: 15px;
      margin-top: 5px;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 500px;
      position: relative;
    }
    .chart-wrapper img {
      max-width: 100%;
      height: auto;
      border-radius: 12px;
      display: none;
    }
    .chart-wrapper img.loaded {
      display: block;
    }
    /* ----- Spinner ----- */
    .spinner {
      border: 4px solid #21262d;
      border-top: 4px solid #58a6ff;
      border-radius: 50%;
      width: 48px;
      height: 48px;
      animation: spin 0.8s linear infinite;
      display: none;
      position: absolute;
      top: 50%;
      left: 50%;
      margin: -24px 0 0 -24px;
    }
    .spinner.active {
      display: block;
    }
    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
    /* ----- Responsive ----- */
    @media (max-width: 768px) {
      .container {
        padding: 20px;
      }
      .controls {
        gap: 12px;
      }
      .control-group {
        flex: 1 1 45%;
      }
      .btn-group {
        flex: 1 1 100%;
        justify-content: flex-start;
      }
      .btn-load {
        width: 100%;
        justify-content: center;
      }
      .selected-date {
        text-align: right;
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>📈 Candlestick Viewer</h1>
    <div class="subtitle">NIFTY 50 – 1‑minute data</div>

    <div class="controls">
      <div class="control-group">
        <label for="year">Year</label>
        <select id="year"></select>
      </div>
      <div class="control-group">
        <label for="month">Month</label>
        <select id="month"></select>
      </div>
      <div class="control-group">
        <label for="day">Day</label>
        <select id="day"></select>
      </div>
      <div class="control-group">
        <label for="timeframe">Timeframe</label>
        <select id="timeframe">
          <option value="1">1 Minute</option>
          <option value="3">3 Minutes</option>
          <option value="5">5 Minutes</option>
          <option value="15">15 Minutes</option>
          <option value="30">30 Minutes</option>
          <option value="60">60 Minutes</option>
        </select>
      </div>

      <!-- New: Previous / Next buttons -->
      <div class="btn-group">
        <button class="btn" id="prevDayBtn" disabled>◀ Prev Day</button>
        <button class="btn" id="nextDayBtn" disabled>Next Day ▶</button>
        <button class="btn btn-load" id="loadChart">Load Chart</button>
      </div>

      <span class="selected-date" id="selectedDate"></span>
    </div>

    <div class="chart-wrapper">
      <div class="spinner" id="spinner"></div>
      <img id="chart" alt="Candlestick chart" />
    </div>
  </div>

  <script>
    // DOM refs
    const yearSel = document.getElementById('year');
    const monthSel = document.getElementById('month');
    const daySel = document.getElementById('day');
    const timeframeSel = document.getElementById('timeframe');
    const chartImg = document.getElementById('chart');
    const spinner = document.getElementById('spinner');
    const loadBtn = document.getElementById('loadChart');
    const prevBtn = document.getElementById('prevDayBtn');
    const nextBtn = document.getElementById('nextDayBtn');
    const selectedDateSpan = document.getElementById('selectedDate');

    // ----- Helpers -----
    async function fetchJSON(url) {
      const res = await fetch(url);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      return res.json();
    }

    function populateSelect(sel, values) {
      sel.innerHTML = '';
      values.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v;
        sel.appendChild(opt);
      });
    }

    function updateSelectedDate() {
      const y = yearSel.value;
      const m = monthSel.value.padStart(2, '0');
      const d = daySel.value.padStart(2, '0');
      selectedDateSpan.textContent = y && m && d ? `📅 ${y}-${m}-${d}` : '';
    }

    // ----- Load cascading dropdowns -----
    async function loadYears() {
      const years = await fetchJSON('/years');
      populateSelect(yearSel, years);
      await loadMonths();
    }

    async function loadMonths() {
      const year = yearSel.value;
      if (!year) return;
      const months = await fetchJSON(`/months/${year}`);
      populateSelect(monthSel, months);
      await loadDays();
      updateSelectedDate();
      updateNavButtons();
    }

    async function loadDays() {
      const year = yearSel.value;
      const month = monthSel.value;
      if (!year || !month) return;
      const days = await fetchJSON(`/days/${year}/${month}`);
      populateSelect(daySel, days);
      updateSelectedDate();
      updateNavButtons();
    }

    // ----- Navigation buttons state -----
    async function updateNavButtons() {
      const y = yearSel.value;
      const m = monthSel.value;
      const d = daySel.value;
      if (!y || !m || !d) {
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        return;
      }
      // Check next day
      try {
        await fetchJSON(`/next_day/${y}/${m}/${d}`);
        nextBtn.disabled = false;
      } catch {
        nextBtn.disabled = true;
      }
      try {
        await fetchJSON(`/prev_day/${y}/${m}/${d}`);
        prevBtn.disabled = false;
      } catch {
        prevBtn.disabled = true;
      }
    }

    // ----- Move to next/prev day and load chart -----
    async function moveDay(direction) {
      const y = yearSel.value;
      const m = monthSel.value;
      const d = daySel.value;
      if (!y || !m || !d) return;

      const endpoint = direction === 'next' ? `/next_day/${y}/${m}/${d}` : `/prev_day/${y}/${m}/${d}`;
      try {
        const data = await fetchJSON(endpoint);
        // data contains { year, month, day }
        yearSel.value = data.year;
        // Reload months and days for the new year
        await loadMonths(); // this loads months for the new year
        // After loadMonths, month and day are populated; set them
        monthSel.value = data.month;
        await loadDays();  // loads days for the new month
        daySel.value = data.day;
        updateSelectedDate();
        // Automatically load chart
        loadChart();
      } catch (err) {
        alert(err.message);
      }
    }

    // ----- Load chart (extracted) -----
    async function loadChart() {
      const year = Number(yearSel.value);
      const month = Number(monthSel.value);
      const day = Number(daySel.value);
      const timeframe = Number(timeframeSel.value);

      if (!year || !month || !day) {
        alert('Please select a valid year, month and day.');
        return;
      }

      loadBtn.disabled = true;
      spinner.classList.add('active');
      chartImg.classList.remove('loaded');
      chartImg.style.display = 'none';

      try {
        const response = await fetch('/chart', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ year, month, day, timeframe }),
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.error || 'Failed to generate chart');
        }

        const result = await response.json();
        chartImg.src = result.image + '?t=' + Date.now();
        chartImg.onload = () => {
          chartImg.style.display = 'block';
          chartImg.classList.add('loaded');
          spinner.classList.remove('active');
          loadBtn.disabled = false;
          updateNavButtons();
        };
        chartImg.onerror = () => {
          alert('Error loading chart image.');
          spinner.classList.remove('active');
          loadBtn.disabled = false;
        };
      } catch (error) {
        alert(error.message);
        spinner.classList.remove('active');
        loadBtn.disabled = false;
      }
    }

    // ----- Event listeners -----
    yearSel.addEventListener('change', () => {
      loadMonths();
    });
    monthSel.addEventListener('change', () => {
      loadDays();
    });
    daySel.addEventListener('change', () => {
      updateSelectedDate();
      updateNavButtons();
    });
    timeframeSel.addEventListener('change', updateSelectedDate);

    loadBtn.addEventListener('click', loadChart);
    prevBtn.addEventListener('click', () => moveDay('prev'));
    nextBtn.addEventListener('click', () => moveDay('next'));

    // ----- Initialise -----
    loadYears();
  </script>
</body>
</html>
