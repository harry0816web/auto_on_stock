import time
import os
import re
import requests
import glob

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

import pandas as pd

# openpyxl 相關
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OImage

# 假設你的登入帳密、目標頁面
# LOGIN_EMAIL = ''
# LOGIN_PASSWORD = '
# /product
# input_url = "https://www.shop2000.com.tw/%E6%99%A8%E4%B8%80/p51852772"

# 產出檔名
EXCEL_BASE = "shopee_upload.xlsx"             # pandas 產生的 base 檔(文字/欄位)
EXCEL_WITH_IMAGES = "shopee_upload_with_images.xlsx"  # 最終檔(內嵌圖片)

def login_and_crawl(PRODUCT_URL):
    """
    透過 Selenium 自動登入後，爬取商品頁資訊與圖片，回傳字典格式的商品資料。
    """
    driver = webdriver.Chrome()  # 假設 chromedriver 已在 PATH
    driver.maximize_window()

    # 前往商品頁
    driver.get(PRODUCT_URL)
    time.sleep(1)

    # 若頁面有 iframe 跳窗登入，就切過去
    try:
        driver.switch_to.frame(
            driver.find_element(By.XPATH, "//iframe[contains(@src,'mem_login_pop.aspx')]")
        )
        time.sleep(1)
    except:
        pass

    # 找到帳號 / 密碼欄位
    try:
        account_input = driver.find_element(
            By.XPATH, "/html/body/center/div[2]/form/table/tbody/tr[1]/td/input"
        )
        password_input = driver.find_element(
            By.XPATH, "/html/body/center/div[2]/form/table/tbody/tr[2]/td[1]/input"
        )
    except Exception as e:
        print("找不到帳號或密碼欄位:", e)
        driver.quit()
        return None

    # 輸入帳密並送出
    account_input.clear()
    account_input.send_keys(LOGIN_EMAIL)
    password_input.clear()
    password_input.send_keys(LOGIN_PASSWORD)
    password_input.send_keys(Keys.ENTER)
    time.sleep(1)

    # 回到主頁
    try:
        driver.switch_to.default_content()
    except:
        pass

    # 再次進入商品頁(以登入狀態)
    driver.get(PRODUCT_URL)
    time.sleep(1)

    # 抓「一般價格」
    try:
        price_element = driver.find_element(
            By.XPATH,
            "/html/body/center/div/div[2]/table/tbody/tr/td[2]/table[2]/tbody/tr/td/table/tbody/tr/td[1]/div[1]/span"
        )
        product_price = price_element.text
    except:
        product_price = "找不到一般價格"
    print("一般價格:", product_price)
    # 抓「庫存」
    try:
        stock_element = driver.find_element(
            By.XPATH,
            "/html/body/center/div/div[2]/table/tbody/tr/td[2]/table[1]/tbody/tr[4]/td[2]/stkt0"
        )
        product_stock = stock_element.text
    except:
        product_stock = "找不到庫存"

    print("庫存", product_stock)

    # 用 BeautifulSoup 擷取商品名稱/描述/圖片路徑
    html_source = driver.page_source
    soup = BeautifulSoup(html_source, "lxml")

    # (1) 商品名稱
    tag_name = soup.find("span", id="product_name")
    product_name = "【萬泰豐團購】 " + tag_name.get_text(strip=True) if tag_name else "未抓到商品名稱"
    print("商品名稱:", product_name)

    # (2) 商品描述
    try:
        desc_td = soup.select_one("html body center div:nth-of-type(4) table tr td")
        if desc_td:
            divs = desc_td.find_all("div")
            product_desc_text = "【萬泰豐團購】 果香年年雪Q禮盒(180g/包)\n\n週週上新品 團購批發直播抖音網紅 新品上不完\n\n批發請聊聊私訊 我們將盡快回復 謝謝\n\n" + "\n".join(d.get_text(strip=True) for d in divs)
            product_desc_text += "\n\n#晨一鮮食#薄荷巧克力#巧克力#薄荷夾心#單顆包裝#零食#零嘴\n\n#晨一鮮食#鳳松林#晨元堂#淨の職人#Sonne#焙可皇后#MiinShop#鎮德蔘藥行#AURÉLIE#九龍堂\n\n#海苔#炙燒烤海苔#溫剁椒醬#剁椒醬#辣椒#罐頭#蒜蓉辣椒#酵素梅#去籽茶梅#桂花烏梅磚#茶磚#魷魚條#甘宋梅\n\n#梅子#剝皮辣椒#蒜味胡椒鹽#胡椒鹽#草本蜂梨糖#脆梅#葉黃素"
        else:
            product_desc_text = "抓不到描述文字"
    except:
        product_desc_text = "抓不到描述文字"
    print("商品描述:", product_desc_text)

    # (3) 圖片 URL
    match_path = re.search(r"var\s+imgPath\s*=\s*'([^']+)'", html_source)
    match_str = re.search(r"var\s+imgstr\s*=\s*'([^']+)'", html_source)
    image_urls = []
    if match_path and match_str:
        img_path = match_path.group(1)
        img_str = match_str.group(1).strip('|')
        gno_list = img_str.split('||')
        for gno in gno_list:
            gno = gno.strip()
            if gno:
                full_url = f"https://{img_path}{gno}.jpg"
                image_urls.append(full_url)

    # 下載圖片
    img_folder = "downloaded_images"
    if not os.path.exists(img_folder):
        os.makedirs(img_folder)

    downloaded_paths = []
    for idx, url_ in enumerate(image_urls, start=1):
        try:
            r = requests.get(url_, timeout=10)
            if r.status_code == 200:
                filename = os.path.join(img_folder, f"product_{idx}.jpg")
                with open(filename, 'wb') as f:
                    f.write(r.content)
                downloaded_paths.append(filename)
                print(f"[下載成功] {filename}")
            else:
                print(f"[下載失敗] {r.status_code} - {url_}")
        except Exception as e:
            print(f"[下載失敗] {url_}, 原因:", e)

    driver.quit()

    # 封裝並回傳
    return {
        "category": "零食/點心",
        "product_name": product_name,
        "product_desc": product_desc_text,
        "price": product_price,
        "stock": product_stock,
        "images": downloaded_paths  # 本機檔案路徑
    }


def main():
    # 1. Selenium 爬取
    while 1:
        PRODUCT_URL = input("請輸入商品頁面網址: ")
        PRODUCT_URL = PRODUCT_URL.replace("/p", "/product/p")
        # 插入/product
        print(PRODUCT_URL)
        product_data = login_and_crawl(PRODUCT_URL)
        if not product_data:
            print("爬蟲失敗或未取得資料，程式中斷。")
            return
    
if __name__ == "__main__":
    main()
