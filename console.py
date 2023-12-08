import os
import re
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from utils import tw_current_time, get_diff_days_date

class Console:
    def __init__(self):
        cert = self.get_all_firestore_env()
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
        self.return_url = os.getenv('warehouse_url')
        self.employee_url = os.getenv('employee_url')

        self.get_employee_dict()

    def get_merchant_list(self):
        db = firestore.client()
        user_ref = db.collection("users")
        query_lst = user_ref.where(
            "role", "==", 1
        ).get()
        lst = []
        for query in query_lst:
            lst.append(query.to_dict())
        db.close()
        return lst

    def get_employee_dict(self):
        db = firestore.client()

        users_ref = db.collection("users")
        streams = users_ref.where(filter=FieldFilter("role", "in", [2, 3])).stream()
        self.employee_dict = {s.id: s.to_dict() for s in streams}
        
        cur_dt = tw_current_time()
        self.create_default_table(db)

        db.close()

    def create_default_table(self, db):
        tomo_dt = get_diff_days_date(-1).strftime("%Y%m%d")

        k_doc = db.collection("search_cnt").document(f'keyword_{tomo_dt}')
        u_doc = db.collection("search_cnt").document(f'users_{tomo_dt}')
        if not k_doc.get().to_dict() or not u_doc.get().to_dict():
            # Let document exist
            k_doc.set({"default": 0})
            u_doc.set({"default": 0})

    def close_client(self):
        self.db.close()

    def get_all_firestore_env(self):
        d = {}
        for k, v in os.environ.items():
            if k.startswith('CF'):
                if 'private_key' in k:
                    v = v.replace('\\n', '\n')
                d[k[3:]] = v
        return d

    def get_current_role(self, uid):
        if uid in self.employee_dict:
            return self.employee_dict[uid]
        d = self.db.collection("users").document(uid).get().to_dict()
        return d or {"role": 0}

    def set_default_role(self, uid, text):
        users_ref = self.db.collection("users")
        query = users_ref.where(
            filter=FieldFilter(
                "phone_number", "==", text
            )
        ).limit(1).get()
        if len(query) and query[0].to_dict()['uid'] != uid:
            return "此電話號碼已被使用，請確認電話號碼是否正確或者請洽管理員。"

        doc = users_ref.document(uid)
        doc.set(
            {
                "uid": uid, "role": 0, "phone_number": text,
                "create_dt": tw_current_time().strftime("%Y-%m-%d"),
                "create_ts": tw_current_time().strftime("%H:%M:%S"),
                "search_cnt": 0
            }
        )
        return f"設定成功。\n若為廠商，請通知管理員您的電話號碼以便於提升您的權限，謝謝。\n請點選下方連結_返回雲端通知管理員:\n{self.return_url}"
        
    def user_guide(self, role):
        if role == 3:
            product_1 = self.db.collection("products").document("1").get().to_dict()
            return f"""
目前商品最新更新時間為: {product_1.get("update_time")}

角色代碼 --> (0:消費者,1:廠商,2:員工,3:管理層)

CH <角色代碼> <手機號碼> \n    -> (改變權限)

RM <手機號碼> \n    -> (移除現有手機號碼綁定)

<商品規格> <角色代碼> \n    -> (使用特定角色查詢商品規格)
"""
        elif role == 0:
            return f"""
 管理人員尚未給予權限
 請耐心等候或洽管理人員
 請點選下方連結_返回雲端通知管理員:
 {self.return_url}
 """
        elif role == 1:
            return f"""
此機器人目前僅提供查詢規格
查詢方式請直接輸入規格
勿輸入廠牌與花紋
如: 2055017

若仍有其他問題
請至下方連結_返回雲端詢問管理員:
{self.return_url}
"""
        
    def delete_profile(self, uid):
        self.db = firestore.client()
        users_ref = self.db.collection("users").document(uid)
        users_ref.delete()

    def rm_phone_role(self, text):
        phone_no = text.split(' ')[-1]
        users_ref = self.db.collection("users")
        query = users_ref.where(
            filter=FieldFilter(
                "phone_number", "==", phone_no
            )
        ).get()
        if not len(query):
            return f"找不到此電話號碼: {phone_no}"
        users_ref.document(query[0].id).delete()
        return f"已將 {phone_no} 刪除"

    def lookup(self, role, text):
        prod_ref = self.db.collection("products")
        spec_text = text.replace('/', '').replace('R', '').replace('-', '').replace('.', '')
        query_lst = prod_ref.where(
            "spec", "==", spec_text
        ).get()
        if not len(query_lst):
            return f"您搜索的商品目前沒有現貨。\n需要調貨，請點選下方連結_返回雲端詢問\n{self.return_url}"

        d_lst = [q.to_dict() for q in query_lst]
        res = []
        idx = 1
        for d in sorted(d_lst, key=lambda x: x['item_name']):
            name, number = d['item_name'], d['stock_no']
            item_year = d['item_year']
            if role == 1 and number > 12:
                number = "12+"
            elif role == 2 and number > 20:
                number = "20+"

            if role == 1:
                if not d['wholesale']:
                    continue
                result_s = f"批發價 {d['wholesale']}/條\n"
            elif role == 2:
                result_s = f"現金價 {d['cash_price']}\n刷卡價 {d['credit_price']}\n"
                if d['district_project']:
                    result_s += f"南太平日 {d['district_project']}\n"
                if d['fb_project']:
                    result_s += f"FB合購價 {d['fb_project']}\n"
            else:
                result_s = f"現金價 {d['cash_price']}\n批發價 {d['wholesale']}\n"
            result_s += f"現貨庫存({number})"
            if role == 3:
                result_s += f"\n成本 {d['cost']}"

            res.append(f"{idx}) {name}\n{item_year}\n{result_s}")
            idx += 1
        results = "\n\n".join(res)
        cur_dt = tw_current_time().strftime("%m/%d %H:%M")
        if role == 1:
            results += f"\n\n以上庫存僅供參考，實際數量皆以管理員為主\n下單下方連結_返回雲端倉庫下單:\n{self.return_url}"
        elif role == 2:
            results += f"\n\n以上庫存僅供參考，請以預約當下為主\n換胎預約下方連接_台中輪胎館:\n{self.employee_url}"
        return f"查詢時間 {cur_dt}\n您所查詢的資料{text}如下：\n\n{results}"

    def set_phone_role(self, uid, text):
        role, phone_no = min(int(text.split(' ')[-2]), 3), text.split(' ')[-1]
        users_ref = self.db.collection("users")
        query = users_ref.where(
            filter=FieldFilter(
                "phone_number", "==", phone_no
            )
        ).get()
        if not len(query):
            return f"找不到此電話號碼: {phone_no}"
        d = query[0].to_dict()
        self.db.collection("users").document(d["uid"]).set({**d, "role": role})
        role_dict = {0: "消費者", 1: "廠商", 2: "員工", 3: "管理員"}
        return f"已將{phone_no}設定為: {role_dict.get(role)}"

    def update_cnt(self, text, phone):
        cur_dt = tw_current_time().strftime("%Y%m%d")
        # If text startswith dot, that will show Invalid path.
        # So we try to remove it.
        re_text = text.replace('/', '').replace('R', '').replace('-', '').replace('.', '')
        k_doc = self.db.collection("search_cnt").document(f'keyword_{cur_dt}').update({re_text: firestore.Increment(1)})
        u_doc = self.db.collection("search_cnt").document(f'users_{cur_dt}').update({phone: firestore.Increment(1)})

    def get_search_cnt_report(self, dt_lst):
        db = firestore.client()
        k_lst, u_lst = [], []
        for dt in dt_lst:
            dt_str = dt.strftime("%Y%m%d")
            k_doc = db.collection("search_cnt").document(f'keyword_{dt_str}').get().to_dict()
            u_doc = db.collection("search_cnt").document(f'users_{dt_str}').get().to_dict()
            if not k_doc:
                continue

            k_lst.append(k_doc)
            u_lst.append(u_doc)
        db.close()
        return k_lst, u_lst

    def delete_documents(self, tw_dt):
        search_cnt_table = "search_cnt"
        db = firestore.client()
        search_cnt_docs = db.collection(search_cnt_table).list_documents()
        # No need to check every Sunday. We think it is already removed after every 10 of month.
        if tw_dt.day >= 10:
            return
        
        keep_min_dt = min(tw_dt.replace(day=1), get_diff_days_date(7)).strftime("%Y%m%d")
        for doc in search_cnt_docs:
            id = doc.get().id
            doc_dt = id.split('_')[1]
            if doc_dt < keep_min_dt:
                doc.delete()

    def console(self, uid, text):
        self.db = firestore.client()
        d = self.get_current_role(uid)
        role, phone = d.get("role"), d.get("phone_number")
        print(f"UID: {uid}, Phone: {phone}, Role: {role}, Text: {text}")
        chinese_character = re.findall(r'[\u4e00-\u9fff]+', text)
        do_write = role == 1

        text_split = text.split(' ')
        if role >= 3 and len(text_split) == 2 and utils.check_spec_command(text_split[0]) and text_split[-1].isdigit():
            role = min(int(text_split[-1]), 2)
            text = text_split[0]

        # Admin
        if role >= 3 and utils.check_command_action(text):
            if text in ("?", "？", "說明", "指令"):
                return self.user_guide(3).strip()
            elif utils.check_ch_command(text):
                return self.set_phone_role(uid, text)
            elif utils.check_rm_command(text):
                return self.rm_phone_role(text)
        elif role == 0: # 若角色為消費者目前只提供設定電話號碼
            if utils.is_phone_no(text):
                return self.set_default_role(uid, text)
            elif utils.check_spec_command(text):
                return self.user_guide(0).strip()
            return ''
        elif not utils.check_spec_command(text) or \
                len(chinese_character):
            return self.user_guide(1).strip()

        if do_write:
            self.update_cnt(text, phone)
        return self.lookup(role, text)

class utils:
    @classmethod
    def check_spec_command(cls, text):
        t = text.replace('R', '').replace('-', '').replace('.', '')
        return (t.isdigit() and 4 < len(t) < 9) or re.findall(r'[0-9]{3}/[0-9]{2}', t)

    @classmethod
    def check_command_action(cls, text):
        return text in ("?", "？", "說明", "指令") or cls.check_ch_command(text) or cls.check_rm_command(text)

    @classmethod
    def is_phone_no(cls, text):
        return text.isdigit() and text.startswith('09') and len(text) == 10

    @classmethod
    def check_ch_command(cls, text):
        text_split = text.split(' ')
        if len(text_split) != 3:
            return False
        cond_1 = text_split[0] == 'CH'
        cond_2 = text_split[1].isdigit() and len(text_split[1]) == 1 and 0 <= int(text_split[1]) <= 3
        cond_3 = cls.is_phone_no(text_split[-1])
        return cond_1 and cond_2 and cond_3

    @classmethod
    def check_rm_command(cls, text):
        text_split = text.split(' ')
        if len(text_split) != 2:
            return False
        cond_1 = text_split[0] == 'RM'
        cond_2 = cls.is_phone_no(text_split[-1])
        return cond_1 and cond_2