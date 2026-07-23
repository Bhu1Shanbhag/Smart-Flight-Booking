import os
import re
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

CITY_TO_IATA = {
    "delhi": "DEL", "new delhi": "DEL",
    "mumbai": "BOM", "bombay": "BOM",
    "bangalore": "BLR", "bengaluru": "BLR",
    "hyderabad": "HYD",
    "chennai": "MAA",
    "kolkata": "CCU",
    "pune": "PNQ",
    "ahmedabad": "AMD",
    "goa": "GOI",
    "mysore": "MYQ", "mysuru": "MYQ",
    "kochi": "COK", "cochin": "COK",
    "jaipur": "JAI",
    "lucknow": "LKO",
    "amritsar": "ATQ",
    "guwahati": "GAU",
    "bhubaneswar": "BBI",
    "patna": "PAT",
    "varanasi": "VNS",
    "nagpur": "NAG",
    "coimbatore": "CJB",
    "thiruvananthapuram": "TRV", "trivandrum": "TRV",
    "mangalore": "IXE", "mangaluru": "IXE",
    "srinagar": "SXR",
    "leh": "IXL",
    "udaipur": "UDR",
    "jodhpur": "JDH",
    "visakhapatnam": "VTZ", "vizag": "VTZ",
    "madurai": "IXM",
    "indore": "IDR",
    "bhopal": "BHO",
    "ranchi": "IXR",
    "agra": "AGR",
    "surat": "STV",
    "vadodara": "BDQ",
}

class FlightScraperService:
    @staticmethod
    async def get_flight_data(source: str, destination: str, date_str: str) -> str:
        src_code = CITY_TO_IATA.get(source.strip().lower(), source.strip().upper()[:3])
        dst_code = CITY_TO_IATA.get(destination.strip().lower(), destination.strip().upper()[:3])
        
        try:
            ixigo_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d%m%Y")
            display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %B %Y")
        except ValueError:
            ixigo_date = datetime.now().strftime("%d%m%Y")
            display_date = datetime.now().strftime("%d %B %Y")

        url = (
            f"https://www.ixigo.com/search/result/flight"
            f"?from={src_code}&to={dst_code}&date={ixigo_date}"
            f"&adults=1&children=0&infants=0&class=e&source=Search"
        )

        is_headless = os.environ.get("SCRAPER_HEADLESS", "true").lower() == "true"
        print(f"\n[FlightAgent Background Web Surfer] Opening Ixigo: {source}({src_code}) -> {destination}({dst_code}) on {display_date}", flush=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=is_headless)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                # Dismiss popups
                try:
                    popup_button = page.locator("text=Okay, Got it!")
                    if await popup_button.is_visible():
                        await popup_button.click()
                except Exception:
                    pass

                flights = await page.evaluate("""
                    () => {
                        const results = [];
                        const selectors = [
                            '[class*="Listing_listItem"]', '[class*="listItem"]',
                            '[class*="FlightCard"]', '[class*="flight-card"]',
                            '[class*="flight_card"]', '.flight-list-item',
                            '[data-testid*="flight"]'
                        ];
                        let cards = [];
                        for (const sel of selectors) {
                            cards = document.querySelectorAll(sel);
                            if (cards.length > 0) break;
                        }
                        cards.forEach((card, i) => {
                            if (i >= 8) return;
                            const raw = card.innerText || '';
                            const clean = raw.replace(/\\s+/g, ' ').trim().substring(0, 300);
                            if (clean.length > 20) results.push(clean);
                        });
                        return results;
                    }
                """)

                if flights and len(flights) >= 1:
                    lines = [f"Flight {i+1}: {f}" for i, f in enumerate(flights)]
                    result = "\n".join(lines)
                else:
                    raw_text = await page.evaluate("() => document.body.innerText")
                    lines = raw_text.split("\n")
                    clean_lines = []
                    for ln in lines:
                        ln = ln.strip()
                        if not ln or len(ln) > 150: continue
                        if re.search(r'http|www\.|<|>|{|}|\(function', ln): continue
                        clean_lines.append(ln)
                    result = "\n".join(clean_lines[:60])

                return (f"Route: {source} to {destination}\nDate: {display_date}\n\n" + result[:2000])

            except Exception as e:
                print(f"[FlightAgent Background Scraper Error] {e}", flush=True)
                return f"Could not retrieve flight data: {str(e)}"
            finally:
                await browser.close()
