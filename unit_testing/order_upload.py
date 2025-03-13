import re
from playwright.sync_api import Playwright, sync_playwright, expect

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://172.16.17.21:8000/login")
    page.get_by_role("button", name="Log in").click()
    page.get_by_role("link", name="Order Uploader").click()
    page.get_by_role("textbox", name="ZIP File").click()
    page.get_by_role("textbox", name="ZIP File").set_input_files("/home/ranjith/Art_work_automation/samples/static/2AH31/B0558256.zip")
    page.get_by_role("button", name="Upload").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
