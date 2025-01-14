import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---- 使用者資訊 ----
LOGIN_EMAIL = 'rainyh258@gmail.com'
LOGIN_PASSWORD = 'aa502501'

# ---- 網站位置(請修改成實際網址) ----
LOGIN_URL = "https://www.shop2000.com.tw/晨一"   # 假設這是登入頁與商品列表同一 URL
TARGET_URL = "https://www.shop2000.com.tw/%E6%99%A8%E4%B8%80/product/688279"  # 假設這是商品列表頁
# 若實際有不同登入頁，可再分開設置。例如
#   LOGIN_URL = "https://example.com/login"
#   TARGET_URL = "https://example.com/product"

# ---- 爬蟲參數 ----
PAGES_TO_SCRAPE = 2  # 要爬的頁數(可視情況調整)

# ---- 初始化 WebDriver：請確認 ChromeDriver 版本對應 Chrome Browser ----
driver = webdriver.Chrome()  # 確保版本相符
driver.maximize_window()      # 讓視窗最大化，減少元素隱藏問題

try:
    # ---- 1) 前往登入頁 ----
    driver.get(LOGIN_URL)

    # ---- 2) 等待登入表單出現 (依照實際 XPATH/CSS 調整) ----
    account_input = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/center/div/table[2]/tbody/tr[2]/td[1]/div[2]/form/table/tbody/tr[1]/td/input"))
    )
    password_input = driver.find_element(By.XPATH, "/html/body/center/div/table[2]/tbody/tr[2]/td[1]/div[2]/form/table/tbody/tr[2]/td[1]/input")
    login_button  = driver.find_element(By.XPATH, "/html/body/center/div/table[2]/tbody/tr[2]/td[1]/div[2]/form/table/tbody/tr[2]/td[2]/span")

    # ---- 3) 輸入帳密 + 登入 ----
    account_input.send_keys(LOGIN_EMAIL)
    password_input.send_keys(LOGIN_PASSWORD)
    login_button.click()

    # (若登入成功後會跳回同一個 URL，可以再加一個等待條件，
    #  確認登入後出現的元素，例如「查訂單」或使用者名稱等)
    try:
        # 這裡舉例等待「查訂單」連結顯示，您可依照實際登入後會顯示的標的 (文字/元素)
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='mem_tab' and contains(text(),'查訂單')]"))
        )
        print("登入成功，目前頁面：", driver.current_url)
    except:
        print("登入可能失敗或尚未成功，請檢查程式與網站結構。")
        # 如果無法定位到可視為登入失敗，您可以直接 raise Exception 或嘗試其他動作
        # raise Exception("登入失敗或找不到查訂單連結")

    # ---- 4) 確認是否已在商品列表頁 (若需要) ----
    # 若登入與商品列表同頁，就直接開始爬。否則可以 driver.get(TARGET_URL)。
    
    driver.get(TARGET_URL)  # 登入後前往商品列表頁
    # driver.get(TARGET_URL)  # 如果有獨立商品頁就前往

    # ---- 5) 開始翻頁爬取 & 存 CSV ----
    filename = "new_year_products_with_stock_over_50.csv"
    csv_columns = ["product_name", "product_link", "stock"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()

        for page_index in range(1, PAGES_TO_SCRAPE + 1):
            # 等商品列表出現
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "plist_tb"))
            )

            product_cells = driver.find_elements(By.CSS_SELECTOR, "#plist_tb td.p_td")
            print(f"目前在第 {page_index} 頁，偵測到商品筆數：", len(product_cells))

            for cell in product_cells:
                try:
                    # 抓取庫存 (若 <stkT0> 無法直接抓，可以改從 cell 內文字用分割或 Regex)
                    # 例如:
                    stk_div = cell.find_element(By.CSS_SELECTOR, "div.stk")
                    # Ex: 內容類似「庫存 -92」
                    # 拆文字取後方數字
                    text_all = stk_div.text.strip()  # "庫存 -92"
                    # 這裡簡單用 split
                    # text_all.split() -> ["庫存", "-92"]
                    stock_str = text_all.split()[-1]  # 取最後一個
                    stock_number = int(stock_str)

                    # 只篩選庫存 > 50
                    if stock_number > 50:
                        # 商品名稱 (抓 <ul class='p_ul'><li>...</li></ul>)
                        product_li = cell.find_element(By.CSS_SELECTOR, "ul.p_ul li")
                        product_name = product_li.text.strip()

                        # 商品連結 (抓 div style="display:none;"><a href="...">...</a>)
                        link_div = cell.find_element(By.CSS_SELECTOR, "div[style='display:none;'] a")
                        product_link = link_div.get_attribute("href")

                        writer.writerow({
                            "product_name": product_name,
                            "product_link": product_link,
                            "stock": stock_number
                        })

                except Exception as e:
                    # 若有商品抓不到庫存或其他元素，直接跳過
                    # (可改為 print(e) 以除錯)
                    pass

            # 嘗試點擊下一頁
            # 以 「<li to_p='2' ><LG class=pt9>下一頁</LG></li>」為例
            # to_p = page_index+1
            try:
                next_page_btn = driver.find_element(By.XPATH, f"//li[@to_p='{page_index+1}']")
                next_page_btn.click()
                time.sleep(2)  # 等一下新頁面載入
            except:
                print("找不到下一頁，可能已到最末頁。")
                break

    print(f"資料已寫入 {filename}")

except Exception as e:
    print("執行過程發生錯誤：", e)

finally:
    # 不論成功失敗都可在這裡關閉
    time.sleep(3)  # 暫停幾秒，方便觀察
    driver.quit()
