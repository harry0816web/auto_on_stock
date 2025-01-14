import time
import os
import re
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

# 設定 Imgur API
CLIENT_ID = 'b6b9cf224906c1c'
CLIENT_SECRET = 'a0d266ebf0635cb235ba42a34def8bb3f461a3fc'

# 帳號密碼
LOGIN_EMAIL = 'rainyh258@gmail.com'
LOGIN_PASSWORD = 'aa502501'
EXCEL_OUTPUT = "shopee_full_table_with_imgur_links.xlsx"

def upload_to_imgur(image_path):
    """上傳圖片至 Imgur 並返回圖片連結"""
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    try:
        with open(image_path, "rb") as img_file:
            response = requests.post(
                "https://api.imgur.com/3/upload",
                headers=headers,
                files={"image": img_file},  # 使用 files 而不是 data
            )
        if response.status_code == 200:
            return response.json()["data"]["link"]
        else:
            print(f"Imgur 上傳失敗: {response.json()}")
            return ""
    except Exception as e:
        print(f"圖片上傳異常: {e}")
        return ""


def login_and_crawl(product_url):
    """登入並爬取商品頁資料"""
    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get(product_url)
    time.sleep(1)

    try:
        driver.switch_to.frame(driver.find_element(By.XPATH, "//iframe[contains(@src,'mem_login_pop.aspx')]"))
        time.sleep(1)
    except:
        pass

    try:
        account_input = driver.find_element(By.XPATH, "/html/body/center/div[2]/form/table/tbody/tr[1]/td/input")
        password_input = driver.find_element(By.XPATH, "/html/body/center/div[2]/form/table/tbody/tr[2]/td[1]/input")
        account_input.clear()
        account_input.send_keys(LOGIN_EMAIL)
        password_input.clear()
        password_input.send_keys(LOGIN_PASSWORD)
        password_input.send_keys(Keys.ENTER)
        time.sleep(2)
    except Exception as e:
        print("登入失敗:", e)
        driver.quit()
        return None

    # 回到主頁
    try:
        driver.switch_to.default_content()
    except:
        pass

    # 再次進入商品頁(以登入狀態)
    driver.get(product_url)
    time.sleep(1)
    html_source = driver.page_source
    driver.quit()
    return html_source

def parse_product_details(html_source):
    """解析商品頁面資料"""
    soup = BeautifulSoup(html_source, "html.parser")
    product_details = {}

    # 抓「一般價格」
    try:
        price_element =  soup.find("span", {"class": "price1"})
        product_details["price"] = price_element.text
    except:
        product_details["price"] = "找不到一般價格"

    # 抓「庫存」
    try:
        stock_element = soup.find("stkt0")
        product_details["stock"] = stock_element.text
    except:
        product_details["stock"] = "找不到庫存"

    # 商品名稱
    product_name = soup.find("span", {"id": "product_name"})
    product_details["product_name"] =  "【萬泰豐團購】 " + product_name.get_text(strip=True) if product_name else "未找到商品名稱"

    # 商品描述
    desc_td = soup.select_one("html body center div:nth-of-type(4) table tr td")
    if desc_td:
        divs = desc_td.find_all("div")
        product_details["product_desc"] = "\n".join(d.get_text(strip=True) for d in divs)
    else:
        product_details["product_desc"] = "無描述"

    # 商品圖片連結
    img_tags = soup.select("img[src*='product_']")
    product_details["Imgur_link"] = [img["src"] if img["src"].startswith("http") else "https:" + img["src"] for img in img_tags if "product_" in img["src"]]

    return product_details

def download_and_upload_images(image_urls):
    """下載圖片並上傳至 Imgur，返回圖片連結列表"""
    img_folder = "downloaded_images"
    os.makedirs(img_folder, exist_ok=True)
    imgur_links = []

    for idx, img_url in enumerate(image_urls, start=1):
        try:
            response = requests.get(img_url, timeout=10)
            if response.status_code == 200:
                img_path = os.path.join(img_folder, f"product_{idx}.jpg")
                with open(img_path, 'wb') as f:
                    f.write(response.content)
                imgur_link = upload_to_imgur(img_path)
                imgur_links.append(imgur_link)
            else:
                imgur_links.append("")
        except Exception as e:
            print(f"圖片處理失敗: {e}")
            imgur_links.append("")

    return imgur_links

def create_excel(products_data):
    """將產品資料寫入 Excel"""
    columns = [
        "分類", "商品名稱", "商品描述", "最高購買數量", "最高購買數量 - 循環週期的開始日期", "最高購買數量 - 循環週期的天數",
        "最高購買數量 - 循環週期的結束日期", "最低購買數量", "主商品貨號", "商品規格識別碼", "規格名稱 1", "規格選項 1",
        "規格圖片", "規格名稱 2", "規格選項 2", "價格", "庫存", "商品選項貨號", "新版尺寸表", "圖片尺寸表", "GTIN",
        "主商品圖片", "商品圖片 1", "商品圖片 2", "商品圖片 3", "商品圖片 4", "商品圖片 5", "商品圖片 6", "商品圖片 7",
        "商品圖片 8", "重量", "長度", "寬度", "高度", "黑貓宅急便", "7-ELEVEN", "全家", "萊爾富", "全家冷凍超取(不寄送離島地區)",
        "宅配通", "OK Mart", "蝦皮店到店", "店到家宅配", "嘉里快遞", "蝦皮店到店 - 隔日到貨", "賣家宅配：箱購", "賣家宅配：冷凍", "較長備貨天數"
    ]

    data_list = []
    for product in products_data:
        # 將圖片連結作為 list 使用
        image_paths = product.get("Imgur_link", [])  # 確保是 list
        row_data = {
            "分類": "",
            "商品名稱": product["product_name"],
            "商品描述": product["product_desc"],
            "最高購買數量": "",
            "最高購買數量 - 循環週期的開始日期": "",
            "最高購買數量 - 循環週期的天數": "",
            "最高購買數量 - 循環週期的結束日期": "",
            "最低購買數量": "",
            "主商品貨號": "",
            "商品規格識別碼": "",
            "規格名稱 1": "",
            "規格選項 1": "",
            "規格圖片": "",
            "規格名稱 2": "",
            "規格選項 2": "",
            "價格": product["price"],
            "庫存": product["stock"],
            "商品選項貨號": "",
            "新版尺寸表": "",
            "圖片尺寸表": "",
            "GTIN": "",
            "主商品圖片": image_paths[0] if len(image_paths) >= 1 else "",
            "商品圖片 1": image_paths[1] if len(image_paths) >= 2 else "",
            "商品圖片 2": image_paths[2] if len(image_paths) >= 3 else "",
            "商品圖片 3": image_paths[3] if len(image_paths) >= 4 else "",
            "商品圖片 4": image_paths[4] if len(image_paths) >= 5 else "",
            "商品圖片 5": image_paths[5] if len(image_paths) >= 6 else "",
            "商品圖片 6": image_paths[6] if len(image_paths) >= 7 else "",
            "商品圖片 7": image_paths[7] if len(image_paths) >= 8 else "",
            "商品圖片 8": "",
            "重量": "",
            "長度": "",
            "寬度": "",
            "高度": "",
            "黑貓宅急便": "開啟",
            "7-ELEVEN": "開啟",
            "全家": "開啟",
            "萊爾富": "開啟",
            "全家冷凍超取(不寄送離島地區)": "關閉",
            "宅配通": "開啟",
            "OK Mart": "開啟",
            "蝦皮店到店": "開啟",
            "店到家宅配": "開啟",
            "嘉里快遞": "開啟",
            "蝦皮店到店 - 隔日到貨": "開啟",
            "賣家宅配：箱購": "開啟",
            "賣家宅配：冷凍": "關閉",
            "較長備貨天數": "否"
        }
        data_list.append(row_data)

    df = pd.DataFrame(data_list, columns=columns)
    df.to_excel(EXCEL_OUTPUT, index=False)
    print(f"[成功] Excel 檔案產生完成: {EXCEL_OUTPUT}")



def main():
    # 載入 CSV
    input_file = "./test_case.csv"
    df = pd.read_csv(input_file)
    product_urls = df["product_link"].tolist()

    products_data = []
    for url in product_urls:
        print(f"正在處理商品: {url}")
        html_source = login_and_crawl(url)
        if not html_source:
            continue

        product_details = parse_product_details(html_source)
        image_urls = product_details.get("圖片路徑", [])
        imgur_links = download_and_upload_images(image_urls)

        # 將 Imgur 連結加入產品資訊
        product_details["Imgur 圖片連結"] = ", ".join(imgur_links)
        products_data.append(product_details)

    # 產生 Excel
    create_excel(products_data)

if __name__ == "__main__":
    main()
