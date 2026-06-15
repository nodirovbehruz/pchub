import asyncio
from playwright.async_api import async_playwright
import json, os, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ARTIFACT_DIR = r"C:\Users\user\.gemini\antigravity\brain\54f6f578-bb8c-4198-97d5-8aad3e83e56c"

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 3000})
        page = await context.new_page()

        try:
            print("Going to SENET Main Category...")
            await page.goto("https://enestech.zendesk.com/hc/ru/categories/23424411660316-SENET", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            # Take a high level screenshot of the category page
            screenshot_path = os.path.join(ARTIFACT_DIR, "senet_modules.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print("Took full page screenshot of modules.")

            # Scrape main sections (Modules)
            sections = await page.eval_on_selector_all("section.section", """sections => 
                sections.map(s => {
                    const title = s.querySelector('h2 a')?.innerText || s.querySelector('h3 a')?.innerText || 'Unknown';
                    const links = Array.from(s.querySelectorAll('.article-list li a')).map(a => a.innerText);
                    return { module: title, articles: links };
                })
            """)
            
            with open("senet_modules.json", "w", encoding="utf-8") as f:
                json.dump(sections, f, ensure_ascii=False, indent=2)
            print("Extracted module data.")
        except Exception as e:
            print(f"Failed to scrape: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
