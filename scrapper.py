import csv
import json
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Setup driver
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)



# Helper: AMbil DEscription
def get_description(driver):

    # Priority 1: meta name="description"
    try:
        desc = driver.find_element(
            By.XPATH, "//meta[@name='description']"
        ).get_attribute("content")
        if desc and desc.strip():
            return desc.strip()
    except:
        pass

    # Priority 2: og:description
    try:
        desc = driver.find_element(
            By.XPATH, "//meta[@property='og:description']"
        ).get_attribute("content")
        if desc and desc.strip():
            return desc.strip()
    except:
        pass

    # Priority 3: h2 tag (subtitle artikel)
    try:
        desc = driver.find_element(By.TAG_NAME, "h2").text
        if desc and desc.strip():
            return desc.strip()
    except:
        pass

    # Priority 4: Paragraf pertama body artikel
    try:
        desc = driver.find_element(
            By.CSS_SELECTOR, "article p, div[data-testid='body-inner-container'] p"
        ).text
        if desc and desc.strip():
            return desc.strip()
    except:
        pass

    return ""


# Helper: ambil author
def get_author(driver):

    # Priority 1: Link /author/
    try:
        author = driver.find_element(By.XPATH, "//a[contains(@href, '/author/')]").text
        if author and author.strip():
            return author.strip()
    except:
        pass

    # Priority 2: Elemen dengan atribut rel="author"
    try:
        author = driver.find_element(By.XPATH, "//*[@rel='author']").text
        if author and author.strip():
            return author.strip()
    except:
        pass

    # Priority 3: Cari teks yang mengandung "By " (byline pattern)
    try:
        author = driver.find_element(
            By.XPATH, "//*[starts-with(normalize-space(text()), 'By ')]"
        ).text
        if author and author.strip():
            return author.strip()
    except:
        pass

    return ""


# Scrape dari beberapa kategori
CATEGORY_URLS = [
    "https://www.wired.com/category/security/",
    "https://www.wired.com/category/science/",
    "https://www.wired.com/category/business/",
    "https://www.wired.com/category/culture/",
    "https://www.wired.com/category/gear/",
]

all_urls = []

for cat_url in CATEGORY_URLS:
    print(f"\n📂 Collecting links from: {cat_url}")
    driver.get(cat_url)
    time.sleep(4)

    # Scroll beberapa kali agar lebih banyak artikel ter-load
    for _ in range(4):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    link_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/story/')]")
    count_before = len(all_urls)

    for elem in link_elements:
        url = elem.get_attribute("href")
        # Pastikan URL valid dan belum ada di list
        if url and "/story/" in url and url not in all_urls:
            all_urls.append(url)

    print(f"   +{len(all_urls) - count_before} links (total: {len(all_urls)})")

    # Stop jika sudah cukup banyak link
    if len(all_urls) >= 100:
        break

print(f"\n✅ Total unique article links found: {len(all_urls)}")


# scrape detail artikel
articles_data = []
TARGET = 75  # Ambil 75 artikel

print(f"\n🔍 Starting detail scrape for {min(TARGET, len(all_urls))} articles...\n")

for i, url in enumerate(all_urls[:TARGET], start=1):
    try:
        driver.get(url)
        # Tunggu sampai h1 muncul, timeout 10 detik
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )

        # Title
        try:
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            title = ""

        # Description — pakai fungsi multi-fallback
        description = get_description(driver)

        # Author
        author = get_author(driver)

        articles_data.append(
            {
                "title": title,
                "url": url,
                "description": description,
                "author": author,
                "scraped_at": datetime.now().isoformat(),
                "source": "Wired.com",
            }
        )

        # Log progress
        has_desc = "✓ desc" if description else "✗ desc"
        has_auth = "✓ auth" if author else "✗ auth"
        print(
            f"[{i:02d}/{min(TARGET, len(all_urls))}] {has_desc} {has_auth} | {title[:55]}"
        )

    except Exception as e:
        print(f"[{i:02d}] ⚠️  Error on {url}: {e}")
        continue

driver.quit()
print(f"\n✅ Scraped {len(articles_data)} articles successfully")


# save json
session_id = f"wired_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

output = {
    "session_id": session_id,
    "timestamp": datetime.now().isoformat(),
    "articles_count": len(articles_data),
    "articles": articles_data,
}

with open("wired_articles.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("💾 JSON saved → wired_articles.json")

# Save CSV
with open("wired_articles.csv", "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["title", "url", "description", "author", "scraped_at", "source"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for article in articles_data:
        writer.writerow(article)

print("CSV saved  → wired_articles.csv")

# Ringkasan
has_desc = sum(1 for a in articles_data if a["description"])
has_auth = sum(1 for a in articles_data if a["author"])

print(f"""
╔══════════════════════════════╗
║        SCRAPE SUMMARY        ║
╠══════════════════════════════╣
║ Total artikel   : {len(articles_data):<11}║
║ Ada description : {has_desc:<11}║
║ Ada author      : {has_auth:<11}║
╚══════════════════════════════╝
""")
