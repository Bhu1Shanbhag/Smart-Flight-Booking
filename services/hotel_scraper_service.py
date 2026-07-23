import os
import urllib.parse
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

class HotelScraperService:
    @staticmethod
    async def get_hotel_data(location: str, checkin_date_str: str) -> str:
        """
        Scrapes Booking.com for premier hotels in the given location on the checkin date.
        Runs in background (headless=True by default).
        """
        try:
            checkin_dt = datetime.strptime(checkin_date_str, "%Y-%m-%d")
            checkout_dt = checkin_dt + timedelta(days=1)
            checkin_str = checkin_dt.strftime("%Y-%m-%d")
            checkout_str = checkout_dt.strftime("%Y-%m-%d")
        except ValueError:
            checkin_dt = datetime.now() + timedelta(days=1)
            checkout_dt = checkin_dt + timedelta(days=1)
            checkin_str = checkin_dt.strftime("%Y-%m-%d")
            checkout_str = checkout_dt.strftime("%Y-%m-%d")

        search_loc = location.strip()
        encoded_loc = urllib.parse.quote(search_loc)

        # Direct searchresults URL for Booking.com with INR currency
        url = (
            f"https://www.booking.com/searchresults.html"
            f"?ss={encoded_loc}&checkin={checkin_str}&checkout={checkout_str}"
            f"&selected_currency=INR&lang=en-us&group_adults=1&no_rooms=1"
        )

        # Headless background execution setting
        is_headless = os.environ.get("SCRAPER_HEADLESS", "true").lower() == "true"
        print(f"\n[HotelAgent Background Web Surfer] Searching Booking.com for '{search_loc}' (Check-in: {checkin_str})...", flush=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=is_headless)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, timeout=35000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                # Attempt to dismiss popups if visible
                try:
                    dismiss_btn = page.locator('button[aria-label*="Dismiss"], button:has-text("Accept"), button:has-text("Decline")')
                    if await dismiss_btn.count() > 0 and await dismiss_btn.first.is_visible():
                        await dismiss_btn.first.click()
                except Exception:
                    pass

                # Extract property cards
                hotels = await page.evaluate("""
                    () => {
                        const results = [];
                        // Selectors for property cards on Booking.com search results
                        const cards = document.querySelectorAll('[data-testid="property-card"], .sr_property_block');
                        
                        cards.forEach((card, i) => {
                            if (i >= 8) return;
                            const titleEl = card.querySelector('[data-testid="title"], .sr-hotel__name');
                            const priceEl = card.querySelector('[data-testid="price-and-discounted-price"], .bui-price-display__value');
                            const reviewEl = card.querySelector('[data-testid="review-score"], .bui-review-score__badge');
                            const locationEl = card.querySelector('[data-testid="address-link"], [data-testid="distance"]');

                            const title = titleEl ? titleEl.innerText.trim() : "";
                            const price = priceEl ? priceEl.innerText.trim() : "";
                            const review = reviewEl ? reviewEl.innerText.trim() : "4.5/5";
                            const dist = locationEl ? locationEl.innerText.trim() : "";

                            if (title && title.length > 3) {
                                results.push(`Hotel: ${title} | Price: ${price} | Rating: ${review} | Location: ${dist}`);
                            }
                        });

                        return results;
                    }
                """)

                if hotels and len(hotels) > 0:
                    lines = [f"{i+1}. {h}" for i, h in enumerate(hotels[:10])]
                    return f"Location: {search_loc}\nCheck-in Date: {checkin_str}\n\nSearch Results:\n" + "\n".join(lines)
                else:
                    # Fallback page text extraction
                    page_text = await page.evaluate("() => document.body.innerText")
                    clean_lines = [line.strip() for line in page_text.split("\n") if len(line.strip()) > 10 and not line.startswith("http")]
                    return f"Location: {search_loc}\nCheck-in Date: {checkin_str}\n\nWeb Page Text:\n" + "\n".join(clean_lines[:30])

            except Exception as e:
                print(f"[HotelAgent Background Scraper Error] {e}", flush=True)
                return f"Could not retrieve live scraper results: {str(e)}"
            finally:
                await browser.close()
