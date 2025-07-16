import os
import re
import uuid
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from utils import tw_current_time, get_diff_days_date, get_month_ago
from mapping import *

class Console:
    def __init__(self):
        cert = self.get_all_firestore_env()
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
        self.return_url = os.getenv('warehouse_url')
        self.employee_url = os.getenv('employee_url')
        self.merchant_see_phone_number = os.getenv('merchant_see_phone_number')
        self.customer_service_phone_number = os.getenv('customer_service_phone_number')
        self.office_phone_number = os.getenv('office_phone_number')

        self.daily_update()

    def lut_line_liff_bind(self, source, user_id):
        db = firestore.client()
        line_liff_ref = db.collection(f"{source}_line_liff")
        user_info = line_liff_ref.document(user_id).get().to_dict()
        db.close()
        return user_info

    def write_line_liff_member(self, source, user_id, mail):
        db = firestore.client()
        line_liff_ref = db.collection(f"{source}_line_liff")
        line_liff_ref.document(user_id).set(
            {
                "line_user_id": user_id,
                "line_register_mail": mail,
                "create_dt": tw_current_time().strftime("%Y-%m-%d"),
                "create_ts": tw_current_time().strftime("%H:%M:%S"),
            }
        )

        db.close()


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

    def daily_update(self):
        db = firestore.client()

        # users_ref = db.collection("users")
        # streams = users_ref.where(filter=FieldFilter("role", "in", [2, 3])).stream()
        # self.employee_dict = {s.id: s.to_dict() for s in streams}
        
        # cur_dt = tw_current_time()
        self.create_default_table(db)

        db.close()

    def create_default_table(self, db):
        tomo_dt = get_diff_days_date(-1).strftime("%Y%m%d")

        doc = db.collection("search_cnt").document(tomo_dt)
        if not doc.get().to_dict(): # Let document exist
            doc.set({})

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
        # if uid in self.employee_dict:
        #     return self.employee_dict[uid]
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

    def get_latest_update_time(self):
        lut_db = firestore.client()
        update_time = lut_db.collection("products").document("1").get().to_dict().get("update_time")
        lut_db.close()
        return update_time
        
    def user_guide(self, role):
        if role == 3:
            product_1 = self.db.collection("products").document("1").get().to_dict()
            if not product_1:
                product_1 = {}
            return f"""
目前商品最新更新時間為: {product_1.get("update_time", "查無資料庫最新更新時間，請聯絡系統管理員。")}

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
範例: 2055017

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

    def get_abbr_spec_text(self, text):
        return text.upper().replace('/', '').replace('R', '').replace('-', '').replace('.', '').replace('C', '').replace('O', '0')

    def lut_product(self, text):
        db = firestore.client()
        prod_ref = db.collection("products")
        db.close()
        return prod_ref.where("spec", "==", text).get()

    def lut_log(self, data):
        db = firestore.client()
        log_ref = db.collection("log")

        phone = data.get('phone')
        if phone:
            log_ref = prod_ref.where("phone", "==", phone)

        spec = data.get('spec')
        if spec:
            log_ref = prod_ref.where("spec", "==", spec)
        results = log_ref.where("created_date", ">=", data['startDate']).where("created_date", ">=", data['endDate']).get()
        db.close()
        return [r.to_dict() for r in results]

    def lookup(self, role, text):
        query_lst = self.lut_product(text)
        if not len(query_lst):
            return f"您搜索的商品目前沒有現貨。\n需要調貨，請點選下方連結_返回雲端詢問\n{self.return_url}"

        d_lst = [q.to_dict() for q in query_lst]
        res, case_0_res = [], []
        idx = 1
        for d in sorted(d_lst, key=lambda x: (x['item_name'].split(' ')[0], x['stock_no']), reverse=True):
            name, stock_number = d['item_name'], d['stock_no']
            item_year = d['item_year']

            stock_number_str = ''
            stock_number_str = f"({stock_number})"
            if role in (1, 2):
                contactor = "管理員/業務" if role == 1 else "門市人員"

                if stock_number <= 0:
                    stock_number_str = f"(0) 請洽{contactor}"
                elif stock_number > 20:
                    stock_number_str = "(20+)"

            if role == 1:
                if not d['wholesale']:
                    continue

                if d['wholesale'] == 8888:
                    price = "請洽管理員/業務"
                else:
                    price = f"{d['wholesale']}/條"
                result_s = f"批發價 {price}\n"
            elif role == 2:
                result_s = f"現金價 {d['cash_price']}\n刷卡價 {d['credit_price']}\n"
                if d.get('district_project'):
                    result_s += f"南太平日 {d['district_project']}\n"
                if d.get('fb_project'):
                    result_s += f"FB合購價 {d['fb_project']}\n"
                if d.get('hb_project'):
                    result_s += f"橫濱專案 {d['hb_project']}\n"
            else:
                result_s = f"現金價 {d['cash_price']}\n批發價 {d['wholesale']}\n"
            result_s += f"現貨庫存{stock_number_str}"

            count = 0
            for key, stock_code in stock_key_mapping:
                num = int(d[key])
                if num <= 0:
                    continue

                if role in (1, 2) and num >= 8:
                    num = "8+"
                count += 1
                suffix = ' '
                if count % 2:
                    result_s += f'\n    '
                result_s += f'{suffix}{stock_code}({num})'

            if role == 3:
                result_s += f"\n成本 {d['cost']}"

            if stock_number == 0:
                case_0_res.append(f"{name}\n{item_year}\n{result_s}")
            else:
                res.append(f"{idx}) {name}\n{item_year}\n{result_s}")
                idx += 1
        case_0_res = [f"{i}) {row}" for i, row in enumerate(case_0_res, 1)]
        if len(case_0_res):
            case_0_res.insert(0, '以下項目未有庫存，請向管理員/業務洽詢定購。')
            case_0_res.insert(0, '----------分隔線----------')
        results = "\n\n".join(res + case_0_res)
        cur_dt = tw_current_time().strftime("%m/%d %H:%M")
        phone_message = f"\n📞 客服下單專線：{self.merchant_see_phone_number}"
        if role == 1:
            results += f"\n\n以上庫存僅供參考，實際數量皆以管理員為主\n下單下方連結_返回雲端倉庫下單:\n{self.return_url}"
        elif role == 2:
            results += f"\n\n以上庫存僅供參考，請以預約當下為主\n換胎預約下方連接_台中輪胎館:\n{self.employee_url}"
            phone_message =f"\n客服預約專線：\n{self.customer_service_phone_number}\n總機專線：\n{self.office_phone_number}"
        results += phone_message
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

        doc = self.db.collection("search_cnt").document(cur_dt)
        data = doc.get().to_dict()
        m_data = data.get(phone, {})
        cur_count = m_data.get(text, 0) + 1

        # Update
        m_data = {**m_data, text: cur_count}
        doc.update({**data, phone: m_data})

    def write_log(self, text, phone):
        doc_name = str(uuid.uuid4())
        cur_dt = tw_current_time()

        doc = self.db.collection("log").document(doc_name).set(
            {
                'phone': phone,
                'spec': text,
                'created_date': cur_dt.strftime('%Y-%m-%d'),
                'created_timestamp': cur_dt.strftime('%Y-%m-%d %H:%M:%S')
            }
        )

    def get_search_cnt_report(self, dt_lst):
        db = firestore.client()
        k_lst, u_lst = [], []
        for dt in dt_lst:
            dt_str = dt.strftime("%Y%m%d")
            doc = db.collection("search_cnt").document(dt_str).get().to_dict()
            if not doc:
                continue
            k_d = {}
            u_d = {}
            # Table should look like {'phone': {'spec': 2, 'spec1': 5}}
            for k, v in doc.items():
                # Update keyword table
                total_count = 0
                for sub_k, sub_v in v.items():
                    total_count += sub_v
                    k_count = k_d.get(sub_k, 0) + sub_v
                    k_d = {**k_d, sub_k: k_count}

                # Update user table
                u_count = u_d.get(k, 0) + total_count
                u_d = {**u_d, k: u_count}

            k_lst.append(k_d)
            u_lst.append(u_d)
        db.close()
        return k_lst, u_lst

    def delete_documents(self, tw_dt):
        search_cnt_table = "search_cnt"
        db = firestore.client()
        search_cnt_docs = db.collection(search_cnt_table).list_documents()
        
        keep_min_dt = min(tw_dt.replace(day=1), get_diff_days_date(7)).strftime("%Y%m%d")
        for doc in search_cnt_docs:
            doc_dt = doc.get().id
            if '_' in doc_dt:
                doc_dt = doc_dt.split('_')[1]
            if doc_dt < keep_min_dt:
                doc.delete()
        db.close()

    def delete_logs(self, tw_dt):
        month_ago = get_month_ago(tw_dt, 6).strftime("%Y-%m-%d")
        db = firestore.client()
        log_collection = db.collection("log")
        query_lst = log_collection.where(
            "created_date", "<=", month_ago
        ).get()
        for query in query_lst:
            doc = log_collection.document(query.id)
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
            role = max(min(int(text_split[-1]), 2), 1)
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

        spec_text = self.get_abbr_spec_text(text)
        if do_write:
            self.update_cnt(spec_text, phone)
            self.write_log(spec_text, phone)
        return self.lookup(role, spec_text)

class utils:
    @classmethod
    def check_spec_command(cls, text):
        t = text.upper().replace('R', '').replace('-', '').replace('.', '').replace('C', '').replace('O', '0')
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