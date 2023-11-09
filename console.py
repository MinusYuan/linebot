import os
import random
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
        doc = self.db.collection("users").document(uid).get().to_dict()
        return doc and doc.get("role") or 0

    def set_default_role(self, uid, text):
        doc = self.db.collection("users").document(uid)
        doc.set(
            {
                "uid": uid, "role": 0, "phone_number": text,
                "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        return 0
        
    def user_guide(self):
        return f"""
角色代碼 --> (0:消費者,1:廠商,2:員工,3:管理層)
ch <角色代碼> <手機號碼>
"""

    def lookup(self, role, text):
        customers_ref = self.db.collection("customers")
        query = customers_ref.where(
            filter=FieldFilter(
                "Country", "==", text.capitalize()
            )
        ).limit(1).get()
        if not len(query):
            return "請重新輸入要查詢的區域，如Taiwan、Brazil ... 等"

        d = random.sample(query, 1)[0].to_dict()
        if role in (1, 2):
            get_cols = {1: ["First Name","Last Name","City"], 2: ["First Name","Last Name","City","Company","Phone 1"]}
            d = {k: v for k, v in d.items() if k in get_cols[role]}
        return "\n".join([f"{k} -> {v}" for k, v in d.items()])

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

    def console(self, uid, text):
        self.db = firestore.client()
        role = self.get_current_role(uid)
        print(f"UID: {uid}, Role: {role}")
        # 消費者目前無法查詢
        if role == 0:
            if utils.is_phone_no(text):
                self.set_default_role(uid, text)
                return "若為廠商，請通知管理員您的電話號碼以便於提升您的權限，謝謝。"
            return ''

        # Admin
        if role >= 3 and utils.check_command_action(text):
            if text in ("?", "說明", "指令"):
                return self.user_guide().strip()
            elif utils.check_ch_command(text):
                return self.set_phone_role(uid, text)
            return '指令錯誤。'
        return self.lookup(role, text)

class utils:
    @classmethod
    def check_command_action(cls, text):
        return text in ("?", "說明", "指令") or cls.check_ch_command(text)

    @classmethod
    def is_phone_no(cls, text):
        return text.isdigit() and text.startswith('09') and len(text) == 10

    @classmethod
    def check_ch_command(cls, text):
        text_split = text.split(' ')
        if len(text_split) != 3:
            return False
        cond_1 = text_split[0] == 'ch'
        cond_2 = text_split[1].isdigit() and len(text_split[1]) == 1 and 0 <= int(text_split[1]) <= 3
        cond_3 = cls.is_phone_no(text_split[2])
        return cond_1 and cond_2 and cond_3