import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# -----------------------------
# State configurations
# -----------------------------
SITES = [
    {
        "name": "Odisha",
        "url": "https://tendersodisha.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page"
    },
    {
        "name": "Maharashtra",
        "url": "https://mahatenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page"
    },
    {
        "name": "Madhya Pradesh",
        "url": "https://mptenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page"
    }
]

# -----------------------------
# Initialize Chrome driver
# -----------------------------
def init_driver(headless=False):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# -----------------------------
# Detect iframe containing table (if any)
# -----------------------------
def switch_to_table_iframe(driver):
    # Check all iframes
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for frame in iframes:
        driver.switch_to.frame(frame)
        tables = driver.find_elements(By.TAG_NAME, "table")
        if tables:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
            return True
        driver.switch_to.default_content()
    return False

# -----------------------------
# Extract table rows
# -----------------------------
def extract_rows(driver):
    # Detect all tables
    tables = driver.find_elements(By.TAG_NAME, "table")
    for table in tables:
        rows = table.find_elements(By.TAG_NAME, "tr")
        if len(rows) > 1:  # Skip header-only tables
            return table, rows
    return None, []

# -----------------------------
# Scrape single site
# -----------------------------
def scrape_one_site(site, keyword=None, start_date=None, end_date=None, headless=False, wait_for_captcha=True):
    driver = init_driver(headless)
    data = []
    try:
        driver.get(site["url"])
        print(f"✅ Opened {site['name']} – solve CAPTCHA manually, then press ENTER...")
        if wait_for_captcha:
            input("Press ENTER after solving CAPTCHA and clicking Search...")

        # Switch to iframe if table is inside one
        switch_to_table_iframe(driver)

        while True:
            table, rows = extract_rows(driver)
            if not rows:
                time.sleep(2)
                table, rows = extract_rows(driver)
                if not rows:
                    break

            for row in rows[1:]:  # skip header
                cols = []
                for c in row.find_elements(By.TAG_NAME, "td"):
                    html = c.get_attribute("innerHTML")
                    text = BeautifulSoup(html, "html.parser").get_text(separator=" ").strip()
                    cols.append(text)
                if not cols:
                    continue

                link_el = row.find_elements(By.TAG_NAME, "a")
                link = link_el[0].get_attribute("href") if link_el else ""

                record = {}
                for i, col in enumerate(cols):
                    record[f"Col{i+1}"] = col
                record["Link"] = link
                record["State"] = site["name"]

                # Keyword filter (search all text in row)
                row_text = " ".join(cols).lower()
                if keyword and keyword.lower() not in row_text:
                    continue

                # Date filter on first column that looks like a date
                if start_date or end_date:
                    try:
                        pub_date = pd.to_datetime(cols[1], errors="coerce", dayfirst=True)
                        if start_date and pub_date < pd.to_datetime(start_date):
                            continue
                        if end_date and pub_date > pd.to_datetime(end_date):
                            continue
                    except:
                        pass

                data.append(record)

            # -----------------------------
            # Pagination detection
            # -----------------------------
            try:
                # Try Next by link text
                next_btns = driver.find_elements(By.XPATH, "//a[contains(text(),'Next') or contains(@class,'next')]")
                if not next_btns:
                    break
                next_btn = next_btns[0]
                driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)
            except:
                break

    except Exception as e:
        print(f"⚠️ Error on {site['name']}: {e}")
    finally:
        driver.quit()

    return pd.DataFrame(data)

# -----------------------------
# Scrape all sites
# -----------------------------
def scrape_all_sites(keyword=None, start_date=None, end_date=None, states=None, headless=False, wait_for_captcha=True):
    results = []
    for site in SITES:
        if states and site["name"] not in states:
            continue
        df = scrape_one_site(site, keyword, start_date, end_date, headless, wait_for_captcha)
        results.append(df)
    if results:
        return pd.concat(results, ignore_index=True)
    return pd.DataFrame()
