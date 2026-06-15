import asyncio
from playwright.async_api import async_playwright
import json, os, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ARTIFACT_DIR = r"C:\Users\user\.gemini\antigravity\brain\54f6f578-bb8c-4198-97d5-8aad3e83e56c"

async def deep_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 3000})
        page = await context.new_page()

        try:
            with open("senet_links.json", "r", encoding="utf-8") as f:
                links = json.load(f)

            scraped_data = {}
            print(f"Starting deep scan of {len(links)} modules...")

            for title, url in links.items():
                print(f"-> Scanning: {title[:30]}...")
                await page.goto(url, timeout=60000)
                await page.wait_for_load_state("networkidle")
                
                # Get the detailed text content of the page
                content = await page.evaluate("""() => {
                    const article = document.querySelector('.article-body');
                    if (article) return article.innerText;
                    
                    const sections = Array.from(document.querySelectorAll('.section-tree-with-article'));
                    if (sections.length > 0) {
                        return sections.map(s => s.innerText).join('\\n');
                    }
                    
                    const list = document.querySelector('.article-list');
                    if (list) return list.innerText;
                    
                    return "No standard content found";
                }""")
                
                # Save data for my analysis
                scraped_data[title] = {"url": url, "content": content[:1500] + "..." if len(content)>1500 else content}

            with open("senet_deep_analysis.json", "w", encoding="utf-8") as f:
                json.dump(scraped_data, f, ensure_ascii=False, indent=2)
            print("DEEP SCAN COMPLETE.")

        except Exception as e:
            print(f"Failed to scrape: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(deep_scrape())
