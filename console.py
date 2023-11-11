import os
import re
import firebase_admin
from datetime import datetime
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

class Console:
    def __init__(self):
        cert = self.get_all_firestore_env()
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)

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
                "create_dt": datetime.now().strftime("%Y-%m-%d"),
                "create_ts": datetime.now().strftime("%H:%M:%S"),
                "search_cnt": 0
            }
        )
        return "設定成功。\n若為廠商，請通知管理員您的電話號碼以便於提升您的權限，謝謝。"
        
    def user_guide(self):
        return f"""
角色代碼 --> (0:消費者,1:廠商,2:員工,3:管理層)
CH <角色代碼> <手機號碼>
RM <手機號碼>
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
        spec_text = text.replace('/', '')
        query_lst = prod_ref.where(
            "spec", ">=", spec_text
        ).where(
            "spec", "<=", spec_text + '\uf8ff'
        ).get()
        if not len(query_lst):
            return f"目前查無此規格{text}，請洽管理人員。"

        res = []
        for idx, query in enumerate(query_lst, 1):
            d = query.to_dict()
            name, number = d['item_name'], d['stock_no']
            if role == 1 and number > 8:
                number = "8+"

            if role == 1:
                result_s = f"{d['wholesale']}/條\n庫存({number})"
            elif role == 2:
                result_s = f"現金價 {d['price']}\n庫存({number})"
            else:
                result_s = f"現金價 {d['price']}\n批發價 {d['wholesale']}\n庫存({number})"

            res.append(f"{idx}) {name}\n{result_s}")
        results = "\n".join(res)
        return f"所查詢的資料{text}如下：\n{results}\n下單連結:\nhttps://liff.line.me/1645278921-kWRPP32q/?accountId=9527orz"

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

    def set_search_cnt(self, uid, d):
        user_doc = self.db.collection("users").document(uid)
        user_doc.set(d)

    def console(self, uid, text):
        self.db = firestore.client()
        d = self.get_current_role(uid)
        role = d.get("role")
        print(f"UID: {uid}, Role: {role}")
        chinese_character = re.findall(r'[\u4e00-\u9fff]+', text)

        # Admin
        if role >= 3 and utils.check_command_action(text):
            if text in ("?", "說明", "指令"):
                return self.user_guide().strip()
            elif utils.check_ch_command(text):
                return self.set_phone_role(uid, text)
            elif utils.check_rm_command(text):
                return self.rm_phone_role(text)
        elif role == 0 and utils.is_phone_no(text): # 消費者目前無法查詢
            return self.set_default_role(uid, text)
        elif not utils.check_spec_command(text) or \
                len(chinese_character) or \
                (role == 0 and not utils.is_phone_no(text)):
            return ''

        d["search_cnt"] = d.get("search_cnt", 0) + 1
        self.set_search_cnt(uid, d)
        return self.lookup(role, text)

class utils:
    @classmethod
    def check_spec_command(cls, text):
        return (text.isdigit() and 4 < len(text) < 9) or re.findall(r'[0-9]{3}/[0-9]{2}', text)

    @classmethod
    def check_command_action(cls, text):
        return text in ("?", "說明", "指令") or cls.check_ch_command(text) or cls.check_rm_command(text)

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