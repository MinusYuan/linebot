stock_key_mapping = [
    ('100', '總倉'),
    ('101', '安和'),
    ('102', '安和卡'),
    ('301', '玉門'),
    ('401', '南投'),
    ('501', '太原'),
    ('601', '竹北')
]

role_2_seen_cols = {
    "item_name": "品名",
    "item_year": "年份",
    "cash_price": "現金價",
    "credit_price": "刷卡價",
    "fb_project": "FB合購價",
    "hb_project": "橫濱專案",
    **{
       k: v for k, v in stock_key_mapping
    }
}