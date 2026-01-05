from playwright.sync_api import sync_playwright
import time
from urllib.parse import urljoin
import random

def human_wait(min_s=0.3, max_s=1.2):
    time.sleep(random.uniform(min_s, max_s))

# ================== ADDED ==================
def focus_page(page):
    """Force focus inside webpage so address bar is not highlighted"""
    page.bring_to_front()                     # <-- ADDED
    time.sleep(0.2)
    page.mouse.move(400, 400)                 # <-- ADDED (move mouse inside page)
    time.sleep(0.2)
    page.evaluate("""
        document.body.focus();
        document.activeElement && document.activeElement.blur();
    """)                                      # <-- ADDED
    time.sleep(0.2)
# ==========================================

STATE = {
    "searched": False,
    "clicked_products": [],
    "initial_scrolls": 0,
    "post_click_scroll": False,
    "scroll_offset": 0,
}

SKIP = ["login", "account", "signup", "register", "cart", "help", "privacy", "terms", "pr?"]

def decide():
    if not STATE["searched"]:
        return "search"

    if STATE["initial_scrolls"] < 2:
        return "scroll"

    if len(STATE["clicked_products"]) == 0:
        return "click_product"

    if len(STATE["clicked_products"]) == 1 and not STATE["post_click_scroll"]:
        return "scroll"

    if len(STATE["clicked_products"]) == 1 and STATE["post_click_scroll"]:
        return "click_product"

    return "stop"

def scroll(page, amount=1500):
    page.mouse.wheel(0, amount)
    STATE["scroll_offset"] += amount
    time.sleep(1)

def restore_scroll(page):
    page.evaluate(f"window.scrollTo(0, {STATE['scroll_offset']});")
    time.sleep(1)

def click_visible_product(page):
    context = page.context
    original_page = page

    links = page.locator("a")
    viewport_height = page.evaluate("window.innerHeight")

    for i in range(min(links.count(), 150)):
        box = links.nth(i).bounding_box()
        if not box:
            continue
        if box["y"] < 0 or box["y"] > viewport_height:
            continue

        href = links.nth(i).get_attribute("href")
        if not href:
            continue

        full = urljoin(page.url, href)

        if "/p/" not in full:
            continue
        if any(x in full.lower() for x in SKIP):
            continue
        if full in STATE["clicked_products"]:
            continue

        with context.expect_page() as new_tab:
            links.nth(i).click()

        new_page = new_tab.value
        new_page.wait_for_load_state()
        time.sleep(2)

        new_page.close()
        time.sleep(1)

        original_page.bring_to_front()
        restore_scroll(original_page)

        STATE["clicked_products"].append(full)
        STATE["post_click_scroll"] = False

        return f"Clicked product {full[:60]}"

    return "No visible product found"

def act(page, action):
    if action == "search":
        box = page.locator("input[name='q']")
        box.click()
        human_wait(0.4, 0.8)

        for ch in "laptop":
            box.type(ch)
            human_wait(0.05, 0.15)

        human_wait(0.3, 0.6)
        box.press("Enter")

        human_wait(1.5, 2.5)
        focus_page(page)        # <-- ADDED (remove focus from address bar after search)

        STATE["searched"] = True
        return "Searched laptop"

    if action == "scroll":
        scroll(page)
        if len(STATE["clicked_products"]) == 0:
            STATE["initial_scrolls"] += 1
        else:
            STATE["post_click_scroll"] = True
        return "Scrolled"

    if action == "click_product":
        return click_visible_product(page)

    return "No action"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        page.goto("https://www.flipkart.com")
        page.wait_for_load_state()

        focus_page(page)        # <-- ADDED (remove address bar focus at start)

        for step in range(10):
            action = decide()
            print(f"[Step {step}] {page.url} -> {action}")

            if action == "stop":
                break

            result = act(page, action)
            print(f"  Result: {result}")

        browser.close()

if __name__ == "__main__":
    run()