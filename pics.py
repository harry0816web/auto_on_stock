from imgurpython import ImgurClient

# 設定 Imgur API
CLIENT_ID = 'b6b9cf224906c1c'
CLIENT_SECRET = 'a0d266ebf0635cb235ba42a34def8bb3f461a3fc'

def upload_images_to_imgur(image_paths):
    client = ImgurClient(CLIENT_ID, CLIENT_SECRET)
    links = []

    for image_path in image_paths:
        try:
            print(f"上傳中：{image_path}")
            upload = client.upload_from_path(image_path, anon=True)
            links.append(upload['link'])
            print(f"上傳成功：{upload['link']}")
        except Exception as e:
            print(f"上傳失敗：{e}")
    
    return links

# 圖片檔案位置
image_paths = ["downloaded_images/product_1.jpg", "downloaded_images/product_2.jpg","downloaded_images/product_3.jpg","downloaded_images/product_4.jpg","downloaded_images/product_5.jpg"]
uploaded_links = upload_images_to_imgur(image_paths)

# 顯示上傳後的圖片連結
print(uploaded_links)
