from utils import get_line_liff_mapping

liff_id_mapping = get_line_liff_mapping('BIND')

stock_key_mapping = [
    ('100', '總倉'),
    ('101', '安和'),
    ('102', '安和卡'),
    ('301', '玉門'),
    ('401', '南投'),
    ('501', '太原'),
    ('601', '竹北')
]

role_mapping_table = {
    'TTSU': {
        '301': '玉門',
        '501': '太原',
        '401': '南投',
        '601': '竹北'
    },
    'TTSN': {
        '401': '南投',
        '501': '太原',
        '301': '玉門',
        '601': '竹北'
    },
    'TTST': {
        '501': '太原',
        '301': '玉門',
        '401': '南投',
        '601': '竹北'
    },
    'TTSC': {
        '601': '竹北',
        '301': '玉門',
        '401': '南投',
        '501': '太原'
    }
}

zero_stock_seen_cols = {
    "item_name": "品名",
    "cash_price": "現金價",
    "credit_price": "刷卡價",
}

role_2_seen_cols = {
    "item_name": "品名",
    "item_year": "年份",
    "cash_price": "現金價",
    "credit_price": "刷卡價",
    "fb_project": "FB合購價",
    "hb_project": "橫濱專案",
    "stock_no": "總條數",
}

web_final_cols = {
    '100': '總倉',
    '101': '安和',
    '102': '安和卡'
}