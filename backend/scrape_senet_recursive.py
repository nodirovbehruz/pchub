import asyncio
from playwright.async_api import async_playwright
import json, os, io, sys
from urllib.parse import urljoin, urldefrag

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "https://enestech.zendesk.com/hc/ru"
MAX_PAGES = 50 

async def recursive_scrape():
    visited = set()
    to_visit = {BASE_URL}
    scraped_data = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 3000})
        page = await context.new_page()

        print(f"Starting RECURSIVE DEEP SCAN (Target limit: {MAX_PAGES} pages)...")

        while to_visit and len(visited) < MAX_PAGES:
            url = to_visit.pop()
            if url in visited: continue
            
            print(f"[{len(visited)+1}/{MAX_PAGES}] Scanning: {url}")
            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("domcontentloaded")
                visited.add(url)

                # Extract Text Content
                title = await page.title()
                content = await page.evaluate("""() => {
                    const article = document.querySelector('.article-body');
                    if (article) return article.innerText;
                    return "";
                }""")

                if content:
                    scraped_data[title] = {"url": url, "content": content}

                # Extract Internal Links to queue them up
                hrefs = await page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
                for href in hrefs:
                    clean_url, _ = urldefrag(href) # remove #anchors
                    if clean_url.startswith(BASE_URL) and clean_url not in visited and "signin" not in clean_url:
                        to_visit.add(clean_url)
                        
            except Exception as e:
                print(f"  -> Error loading {url}: {e}")
                visited.add(url) # Mark as visited so we don't retry immediately

        print(f"Finished crawling. Found {len(scraped_data)} detailed articles.")
        
        # Save structural dump
        with open("senet_ultimate_dump.json", "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=2)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(recursive_scrape())
