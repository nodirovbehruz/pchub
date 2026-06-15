import asyncio
from playwright.async_api import async_playwright
import os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ARTIFACT_DIR = r"C:\Users\user\.gemini\antigravity\brain\54f6f578-bb8c-4198-97d5-8aad3e83e56c"


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        try:
            print("Step 1: Logging in...")
            await page.goto("http://127.0.0.1:8000/admin/")
            
            if "login" in page.url.lower():
                await page.fill("input[name='username']", "admin")
                await page.fill("input[name='password']", "admin")
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle")
            
            print("Step 2: Navigating to Club Map...")
            await page.goto("http://127.0.0.1:8000/admin/computers/computer/club-map/")
            await page.wait_for_selector("#canvas", timeout=10000)
            await asyncio.sleep(2) # Give it time to poll API and render PCs

            print("Step 3: Taking Initial Map Screenshot...")
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "map_initial.png"))

            print("Step 4: Opening Context Menu on PC 101...")
            # Locate PC 101 (we created PC-101 in previous script)
            await page.mouse.move(0, 0)
            pc_node = page.locator(".device-node").first
            await pc_node.click(button="right")
            await asyncio.sleep(1)
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "map_context_menu.png"))

            print("Step 5: Opening Abonement Modal...")
            await page.click("text=Продать абонемент")
            await asyncio.sleep(1)
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "map_abonement_modal.png"))

            print("Step 6: Closing modal...")
            await page.click("text=Отмена")
            await asyncio.sleep(1)

            print("Step 7: Testing Multi-Select...")
            # Click first PC normally
            await page.locator(".device-node").nth(0).click()
            # Control-click second PC
            await page.keyboard.down("Control")
            await page.locator(".device-node").nth(1).click()
            await page.keyboard.up("Control")
            await asyncio.sleep(1)
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "map_multi_select.png"))

            print("Manual UI test completed successfully.")
        except Exception as e:
            print(f"Error during UI test: {e}")
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "error_state.png"))
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
