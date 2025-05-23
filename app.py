# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os
import pandas as pd
import sys
import requests
from argparse import ArgumentParser

from flask import Flask, request, abort, render_template, jsonify
from linebot.v3 import (
     WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage
)

from linebot.models import UnfollowEvent

from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from collections import Counter
from openpyxl import load_workbook

# Local package
from console import Console, role_2_seen_cols
from notify import EMail
from utils import *
from auth import requires_auth, user_auth

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

handler = WebhookHandler(channel_secret)

configuration = Configuration(
    access_token=channel_access_token
)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(UnfollowEvent)
def handle_unfollow(event):
    user_id = event.source.user_id
    con.delete_profile(user_id)
    con.close_client()

@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    user_id = event.source.user_id
    mess = event.message.text.strip().upper()
    reply = con.console(user_id, mess)
    if not reply:
        return
    partial_reply = reply.split('\n')[0]
    print(f"UID: {user_id}, Reply: {partial_reply}")
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        profile = line_bot_api.get_profile(user_id)
        name = profile.display_name
        # print(f"Line User_id: {user_id}, Display name: {profile.display_name}")
        messages = [TextMessage(text=f"{name} 您好\n{reply}")]

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages
            )
        )
    con.close_client()

@app.route("/test_push_message", methods=['GET'])
def test_push_message():
    headers = request.headers
    bearer = headers.get('Authorization')
    token = bearer.split()[1]
    if token != os.getenv('token', None):
        return "OK"
    
    notify_uids = os.getenv('notify_uid', '')
    if not notify_uids:
        return "No UID"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        for uid in notify_uids.split(','):
            line_bot_api.push_message(
                PushMessageRequest(to=uid, messages=[TextMessage(text='推播測試。')]))
    return "OK"
    
def check_update():
    tw_cur_time = tw_current_time()
    # If it's Sunday, we don't check database update or not
    if tw_cur_time.isoweekday() == 7:
        return

    update_dt_str = con.get_latest_update_time()
    update_dt = datetim_strptime(update_dt_str)
    diff_seconds = (tw_cur_time - update_dt).seconds
    if diff_seconds <= 900:
        return

    notify_uids = os.getenv('notify_uid', '')
    if not notify_uids:
        return "No UID"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        for uid in notify_uids.split(','):
            line_bot_api.push_message(
                PushMessageRequest(to=uid, messages=[TextMessage(text='更新失敗，請確認是否正常。')]))
    return


@app.route("/healthcheck", methods=['GET'])
def healthcheck():
    return "OK"

@app.route("/lut-spec", methods=['GET'])
@requires_auth
def table():
    user_info = list(user_auth)[0]
    api_user = user_info[0]
    api_pass = user_info[-1]
    api_url = os.environ.get("SELF_URL", None)
    return render_template("lut_page.html", user=api_user, pw=api_pass, url=api_url)

@app.route('/lut-api', methods=['POST'])
@requires_auth
def lut_api():
    data = request.get_json()
    spec = data.get('spec', '').strip()

    data = con.lut_product(spec)
    d = [q.to_dict() for q in data]
    df = pd.DataFrame(data=d)[role_2_seen_cols.keys()].rename(columns=role_2_seen_cols)
    df['年份'] = df['年份'].mask(df['年份'] == '').fillna('-')
    df['FB合購價'] = df['FB合購價'].mask(df['FB合購價'] == 0).fillna('-')
    df['橫濱專案'] = df['橫濱專案'].mask(df['橫濱專案'] == 0).fillna('-')
    return jsonify(df.to_dict('records'))

def keep_awake():
    url = os.getenv('SELF_URL', None)
    if not url:
        print("URL Not FOUND.")
        return
    resp = requests.get(f"{url}/healthcheck")

def daily_update_employee_list():
    print(f"Update employee list - Start")
    con.daily_update()
    print(f"Update employee list - Done")

@app.route("/daily_notify", methods=['GET'])
def daily_notify():
    headers = request.headers
    bearer = headers.get('Authorization')
    token = bearer.split()[1]
    if token != os.getenv('token', None):
        return "OK"

    generate_reports()
    return "Sent Successfully"

def generate_reports():
    def sorted_split_dict(items):
        sorted_d = sorted(items, key=lambda x: x[1], reverse=True)
        return zip(*sorted_d)

    def return_pd_dataframe(keywords, users, date):
        k_k, k_v = sorted_split_dict(keywords.items())
        u_k, u_v = sorted_split_dict(users.items())
        total = sum(k_v)
        data = {
            "關鍵字": k_k,
            "關鍵字查詢次數": k_v,
            "廠商手機號碼": u_k,
            "廠商手機號碼查詢次數": u_v,
            "總查詢次數": total,
        }
        date_keyword = "報表區間" if len(date) == 6 or "~" in date else "報表日期"
        data[date_keyword] = date
        
        df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in data.items()]))
        # df['廠商手機號碼'] = '="' + df['廠商手機號碼'] + '"'
        return df, date_keyword

    def parse_lst(k_lst, k_counter, u_lst, u_counter):
        for ele in k_lst:
            ele.pop('default')
            # print(f"K Ele: {ele}")
            new_d = {k: v for k, v in ele.items() if isinstance(v, int)}
            k_counter += Counter(new_d)
        for ele in u_lst:
            ele.pop('default')
            new_d = {k: v for k, v in ele.items() if isinstance(v, int)}
            u_counter += Counter(new_d)
        return k_counter, u_counter

    def get_sheet_name(freq):
        if freq == 'D':
            return '日報表'
        elif freq == 'W':
            return '周報表'
        else:
            return '月報表'

    def get_merchant_name(phone_number):
        res = [d.get('merchant_name', '') for d in merchant_lst if d['phone_number'] == phone_number]
        return res[0] if len(res) else ''

    print(f"Daily Notify - Start")
    start_dt, ytd = tw_current_time(), get_diff_days_date(1)
    ytd_dt = ytd.strftime("%Y%m%d")
    att_lst = [f"auto_gen_{ytd_dt}.xlsx"]

    keywords, users = Counter(), Counter()
    sheet_list = []

    mail_to_list, mail_bcc_list = os.getenv('mail_to').split(','), os.getenv('mail_bcc').split(',')
    test_mail = int(os.getenv('test'))
    if test_mail:
        mail_to_list, mail_bcc_list = ['rod92540@gmail.com'], []

    merchant_lst = con.get_merchant_list()
    with pd.ExcelWriter(att_lst[0]) as writer:
        for freq in ('D', 'W', 'M'):
            if freq == 'D' or (freq == 'W' and ytd.weekday() == 5) or (freq == 'M' and ytd.day == get_end_day(ytd.year, ytd.month)) or test_mail:
                sheet_name = get_sheet_name(freq)
                date_lst = get_date_list(freq, start_dt)
                start_dt = date_lst[0]
                keyword_lst, user_lst = con.get_search_cnt_report(date_lst)
                keywords, users = parse_lst(keyword_lst, keywords, user_lst, users)
                date = ytd_dt if freq == 'D' else f'{start_dt.strftime("%Y%m%d")}~{ytd_dt}'
                df, date_key = return_pd_dataframe(keywords, users, date)
                if freq == 'W':
                    con.delete_documents(start_dt)
                elif freq == 'M':
                    merchant_df = pd.DataFrame(merchant_lst)
                    merchant_df = merchant_df.drop(columns=['search_cnt'])
                    merchant_df = merchant_df[~merchant_df['phone_number'].isin(df['廠商手機號碼'])]

                    att_lst.append(f'{ytd.year - 1911}{ytd.month}月未使用廠商清單.csv')
                    merchant_df.to_csv(att_lst[-1], index=False, header=True, encoding='utf-8-sig')
                df['廠商名稱'] = df['廠商手機號碼'].apply(get_merchant_name)
                df = df[['關鍵字', '關鍵字查詢次數', '廠商名稱', '廠商手機號碼', '廠商手機號碼查詢次數', '總查詢次數', date_key]]

                df.to_excel(writer, sheet_name=sheet_name, index=False, header=True)
                sheet_list.append(sheet_name)

    wb = load_workbook(att_lst[0])
    for sheet in sheet_list:
        ws = wb.get_sheet_by_name(sheet)
        auto_adjust_width(ws)
    wb.save(att_lst[0])

    mail = EMail(os.getenv('EMAIL_KEY'))
    mail.send(
        mail_to_list,
        f"每日報表 - TTShop {ytd_dt}",
        "您好，<br><br>此為系統每日自動產生的報告，若有任何疑慮請聯絡我們。<br>謝謝。",
        attachments=att_lst,
        bcc_emails=mail_bcc_list
    )
    print(f"Daily Notify - Done")

# Use scheduler to health check
scheduler = BackgroundScheduler(daemon=True, job_defaults={'max_instances': 1})
trigger = CronTrigger(year="*", month="*", day="*", hour="*", minute="*/10")
trigger1 = CronTrigger(year="*", month="*", day="*", hour="4,12", minute="0", second="0")
trigger2 = CronTrigger(year="*", month="*", day="*", hour="1", minute="0", second="0")
trigger3 = CronTrigger(year="*", month="*", day="*", hour="0-11", minute="40", second="0")
scheduler.add_job(keep_awake, trigger=trigger)
scheduler.add_job(daily_update_employee_list, trigger=trigger1)
scheduler.add_job(generate_reports, trigger=trigger2)
scheduler.add_job(check_update, trigger=trigger3)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

con = Console()

if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)