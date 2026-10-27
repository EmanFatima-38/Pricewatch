# PriceWatch

Product price tracking and fake discount detection for online stores. PriceWatch scrapes product pages on a daily schedule, stores every price check as time-series history, and uses that history to evaluate whether advertised discounts are genuine.

## Stack

- **Scraping:** Python, Requests, BeautifulSoup.
- **Storage:** SQLite with a normalized schema (`products`, `prices`).
- **Automation:** GitHub Actions scheduled workflow (daily at 03:17 UTC), with manual dispatch.
- **Planned:** Streamlit dashboard, Pandas analysis, email alerts, ML-based price drop prediction.

## How it works

Product URLs are listed in `products.txt`. `main.py` scrapes each URL through `src/scraper.py`, extracting name, price, stock status, and a UTC timestamp, then saves the result through `src/database.py`. Products are stored once; each check adds a new row to `prices`, so history accumulates over time. The GitHub Actions workflow repeats this daily and commits the updated `data/prices.db` back to the repository.

Failed products are logged and skipped without stopping the run. Requests use a descriptive User-Agent, a 10-second timeout, and a 1-second delay between pages.

## Local development (PowerShell)

Requires Python 3.13 or newer. From the project directory:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

If activation is blocked, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once, then activate again.

Run a price check and view stored history:

```
python main.py
python show_data.py
```

Run `git pull` before starting work, since the scheduled workflow commits new data to `main` daily.

## Automation

The workflow is defined in `.github/workflows/daily_scrape.yml`. It runs on a daily cron schedule and can also be triggered from the **Actions** tab using **Run workflow**. It requires `contents: write` permission to commit the updated database. Commits are skipped when no data changed.

## Project structure

```
.github/workflows/daily_scrape.yml   Scheduled scraping workflow
data/prices.db                       Price history database
src/scraper.py                       Page download and data extraction
src/database.py                      Schema creation and persistence
main.py                              Runs a full price check
show_data.py                         Prints stored price history
products.txt                         Tracked product URLs
```

## Status and limitations

The scraping, storage, and automation pipeline is working. Development currently uses [books.toscrape.com](https://books.toscrape.com), a site built for scraping practice, so prices do not change. Support for real stores, the dashboard, and the fake discount detector are in progress. Store-specific CSS selectors must be updated if a site changes its HTML structure.

## Author

Eman Fatima, Computer Science student, University of Central Punjab.
[GitHub](https://github.com/EmanFatima-38) · [LinkedIn](https://www.linkedin.com/in/emanfatima38)