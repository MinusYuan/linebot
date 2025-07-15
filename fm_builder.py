import json
def build_default_d(type, **kwargs):
    return {
        'type': type,
        **kwargs
    }

def build_box(layout):
    return build_default_d('box', layout=layout, contents=[])

def build_text(text, **kwargs):
    return build_default_d('text', text=text, **kwargs)

def build_sep(**kwargs):
    return build_default_d('separator', **kwargs)

def build_items_box(lst, items):
    lst.append(build_box('vertical'))
    item_lst = lst[-1]['contents']
    build_pair_box(item_lst, '商品明細', '數量 x 金額', 'items')
    for item in items:
        price = item['price']
        qty = item['quantity']
        amt = item['amount']
        build_pair_box(item_lst, item['name'], f"{qty} x {price} = {amt}", 'items')

def build_pair_box(lst, l_text, r_text, case, layout='horizontal'):
    lst.append(build_box(layout))
    if case == 'items':
        lst[-1]['contents'].append(build_text(l_text, size='xs', color='#1515e6'))
        lst[-1]['contents'].append(build_text(r_text, align='end', size='xs', color='#1515e6'))
    else:
        lst[-1]['contents'].append(build_text(l_text, flex=1))
        lst[-1]['contents'].append(build_text(str(r_text), flex=3, wrap=True))

def build_invoice_info(info):
    with open('templates/flex_message_template.txt', encoding='utf-8') as f:
        bubble_string = f.read()
    bubble_string = bubble_string.replace('{{number}}', info['number'])
    bubble_d = json.loads(bubble_string)
    bubble_d['body'] = build_box('vertical')

    if info['created_at']:
        bubble_d['body']['contents'].append(build_text(info['created_at'], margin='xl'))

    build_pair_box(bubble_d['body']['contents'], '賣方：', info['sbname'], 'others')
    if str(info['type']) == '1':
        if info.get('bbuid'):
            build_pair_box(bubble_d['body']['contents'], '買方：', info['bbuid'], 'others')
        build_pair_box(bubble_d['body']['contents'], '隨機碼：', info['random_no'], 'others')
        build_pair_box(bubble_d['body']['contents'], '總計：', info['total_amt'], 'others')
        bubble_d['body']['contents'].append(build_sep(margin='md', color='#000000'))
        build_items_box(bubble_d['body']['contents'], info['items'])
    else:
        build_pair_box(bubble_d['body']['contents'], '發票已作廢', '', 'others')
    return bubble_d

if __name__ == '__main__':
    info = {
        'type': 1,
        'number': 'AA-12345678',
        'created_at': '2025-07-01 00:01:02',
        'sbname': '測試結果',
        'bbuid': '87654321',
        'random_no': '3456',
        'total_amt': 300,
        'items': [
            {'name': '物品1', 'price': 15, 'quantity': 2, 'amount': 30},
            {'name': '物品2', 'price': 50, 'quantity': 3, 'amount': 150},
            {'name': '物品3', 'price': 120, 'quantity': 1, 'amount': 120}
        ]
    }
    build_invoice_info(info)