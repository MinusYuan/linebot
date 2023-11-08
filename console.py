import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

class Console:
    def __init__(self):
        cert = self.get_all_firestore_env()
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def get_all_firestore_env(self):
        d = {}
        for k, v in os.environ.items():
            if k.startswith('CF'):
                if 'private_key' in k:
                    v = v.replace('\\n', '\n')
                d[k[3:]] = v
        return d

    def get_current_role(self, uid):
        doc = self.db.collection("users").document(uid)
        if doc.get().exists:
            return doc.get().to_dict().get("role") or 0
        else:
            doc.set(
                {
                    "uid": uid, "role": 0, "phone_number": "",
                    "create_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            return 0
        
    def user_guide(self):
        return f"""
角色代碼 --> (0:消費者,1:廠商,2:員工,3:管理層)
ch <角色代碼> <手機號碼>
"""

    def lookup(self, role, code):
        doc = self.db.collection("customers").document(code)

    def console(self, uid, text):
        role = self.get_current_role(uid)
        print(f"UID: {uid}, Role: {role}")
        if role >= 3: # Admin
            if text in ("說明", "指令"):
                return self.user_guide().strip()
        if role >= 1:
            pass
        return ''
