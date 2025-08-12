import os, json, time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

ADV_SEARCH_URL = "https://nato.taleo.net/careersection/2/moresearch.ftl"
SEEN_FILE = Path("seen_jobs.json")
ALERT_FILE = Path("alert.md")

def load_seen():
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()

def save_seen(seen_ids):
    SEEN_FILE.write_text(json.dumps(sorted(list(seen_ids)), ensure_ascii=False, indent=2), encoding="utf-8")

def init_driver():
    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--window-size=1400,1000")

    chrome_path = os.getenv("CHROME_PATH") or os.getenv("CHROME_BIN")
    if chrome_path:
        chrome_opts.binary_location = chrome_path

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_opts)
    driver.set_page_load_timeout(90)
    return driver

def click_if_present(driver, by, selector, wait=4):
    try:
        el = WebDriverWait(driver, wait).until(EC.element_to_be_clickable((by, selector)))
        el.click()
        return True
    except Exception:
        return False

def set_posting_date_today(driver):
    for sel in [
        (By.ID, "onetrust-accept-btn-handler"),
        (By.CSS_SELECTOR, "button[aria-label*='Accept'], button[title*='Accept']"),
    ]:
        click_if_present(driver, *sel, wait=2)

    for sel in [
        (By.XPATH, "//button[contains(.,'Advanced Search') or contains(.,'Refine') or contains(.,'Gelişmiş')]"),
        (By.CSS_SELECTOR, "button[aria-controls*='advancedSearch']"),
    ]:
        if click_if_present(driver, *sel, wait=3):
            break

    for sel in [
        (By.XPATH, "//div[contains(@class,'facet')][.//span[contains(.,'Posting Date')]]//button"),
        (By.XPATH, "//button[contains(.,'Posting Date')]"),
    ]:
        if click_if_present(driver, *sel, wait=3):
            break

    for sel in [
        (By.XPATH, "//label[.//span[contains(translate(., 'TODAYBUGÜN', 'todaybugün'), 'today') or contains(translate(., 'TODAYBUGÜN', 'todaybugün'), 'bugün')]]//input"),
        (By.XPATH, "//span[contains(.,'Today') or contains(.,'Bugün')]/ancestor::label//input"),
        (By.XPATH, "//input[@type='checkbox' or @type='radio'][@value='TODAY' or @value='Today']"),
    ]:
        try:
            el = WebDriverWait(driver, 6).until(EC.presence_of_element_located(sel))
            driver.execute_script("arguments[0].click();", el)
            break
        except Exception:
            pass

    for sel in [
        (By.XPATH, "//button[contains(.,'Search') or contains(.,'Apply') or contains(.,'Ara')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
    ]:
        if click_if_present(driver, *sel, wait=2):
            break

    time.sleep(3)

def scrape_results(driver):
    jobs = []
    anchors = driver.find_elements(By.XPATH, "//a[contains(@href, 'jobdetail.ftl') and (contains(@href,'job=') or contains(@href,'Job='))]")
    for a in anchors:
        title = (a.text or "").strip()
        href = a.get_attribute("href")
        if not href:
            continue
        job_id = None
        for key in ["job=", "Job="]:
            if key in href:
                job_id = href.split(key, 1)[1].split("&")[0]
                break
        if not job_id:
            job_id = href.rsplit("/", 1)[-1]
        if title:
            jobs.append({"id": job_id, "title": title, "url": href})
    uniq = {j["id"]: j for j in jobs}
    return list(uniq.values())

def write_alert_md(new_jobs):
    lines = [
        "## Yeni NATO Taleo ilanları (Posting Date: Today)\n",
        f"Toplam: **{len(new_jobs)}**\n",
    ]
    for j in new_jobs:
        lines.append(f"- [{j['title']}]({j['url']}) — `{j['id']}`")
    ALERT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    seen = load_seen()
    driver = init_driver()
    try:
        driver.get(ADV_SEARCH_URL)
        set_posting_date_today(driver)
        jobs = scrape_results(driver)
        new_jobs = [j for j in jobs if j["id"] not in seen]

        if new_jobs:
            write_alert_md(new_jobs)
            for j in new_jobs:
                seen.add(j["id"])
            save_seen(seen)
            print(f"Yeni {len(new_jobs)} ilan bulundu. alert.md üretildi.")
        else:
            print("Yeni ilan yok.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
