from utils import get_line_liff_mapping

liff_id_mapping = get_line_liff_mapping('BIND')

role_dict = {0: "消費者", 1: "廠商", 2: "員工", 3: "管理員"}

stock_key_mapping = [
    ('100', '總倉'),
    ('101', '安和'),
    ('102', '安和卡'),
    ('301', '玉門'),
    ('401', '南投'),
    ('501', '太原'),
    ('600', '湖口'),
    ('601', '竹北'),
    ('888', '台南'),
    ('1001', '大肚')
]
role_1_no_see = []
role_2_no_see = ['888']

line_con_customized_seen = {
    '1001': (3, )
}

role_mapping_table = {
    'TTSU': {
        '301': '玉門',
        '501': '太原',
        '401': '南投',
        '600': '湖口',
        '601': '竹北',
        '1001': '大肚'
    },
    'TTSN': {
        '401': '南投',
        '501': '太原',
        '301': '玉門',
        '600': '湖口',
        '601': '竹北',
        '1001': '大肚'
    },
    'TTST': {
        '501': '太原',
        '301': '玉門',
        '401': '南投',
        '600': '湖口',
        '601': '竹北',
        '1001': '大肚'
    },
    'TTSC': {
        '600': '湖口',
        '601': '竹北',
        '301': '玉門',
        '401': '南投',
        '501': '太原',
        '1001': '大肚'
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
    "promotional_price": "限時專案",
    "stock_no": "總條數",
}

web_final_cols = {
    '100': '總倉',
    '101': '安和',
    '102': '安和卡'
}