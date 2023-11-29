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

from flask import Flask, request, abort
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
from console import Console
from notify import EMail
from utils import *

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
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"{name} 您好\n{reply}")]
            )
        )
    con.close_client()

@app.route("/healthcheck", methods=['GET'])
def healthcheck():
    return "OK"

def keep_awake():
    url = os.getenv('SELF_URL', None)
    if not url:
        print("URL Not FOUND.")
        return
    resp = requests.get(f"{url}/healthcheck")

def daily_update_employee_list():
    print(f"Update employee list - Start")
    con.get_employee_dict()
    print(f"Update employee list - Done")

# @app.route("/daily_notify", methods=['GET'])
def daily_notify():
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
        return df

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

    print(f"Daily Notify - Start")
    start_dt, ytd = tw_current_time(), get_diff_days_date(1)
    ytd_dt = ytd.strftime("%Y%m%d")
    att_name = f"auto_gen_{ytd_dt}.xlsx"

    keywords, users = Counter(), Counter()
    sheet_list = []
    with pd.ExcelWriter(att_name) as writer:
        for freq in ('D', 'W', 'M'):
            if freq == 'D' or (freq == 'W' and ytd.weekday() == 5) or (freq == 'M' and ytd.day == get_end_day(ytd.year, ytd.month)):
                sheet_name = get_sheet_name(freq)
                date_lst = get_date_list(freq, start_dt)
                start_dt = date_lst[0]
                keyword_lst, user_lst = con.get_search_cnt_report(date_lst)
                keywords, users = parse_lst(keyword_lst, keywords, user_lst, users)
                date = ytd_dt if freq == 'D' else f'{start_dt.strftime("%Y%m%d")}~{ytd_dt}'
                df = return_pd_dataframe(keywords, users, date)
                df.to_excel(writer, sheet_name=sheet_name, index=False, header=True, encoding='utf-8-sig')
                sheet_list.append(sheet_name)
                # if freq == 'M':
                #     date_lst = get_date_list(freq, tw_current_time())
                #     con.delete_documents(date_lst)

    wb = load_workbook(att_name)
    for sheet in sheet_list:
        ws = wb.get_sheet_by_name(sheet)
        auto_adjust_width(ws)
    wb.save(att_name)

    mail = EMail(os.getenv('EMAIL_KEY'))
    mail_to_list, mail_bcc_list = os.getenv('mail_to').split(','), os.getenv('mail_bcc').split(',')
    mail.send(
        mail_to_list,
        f"每日報表 - TTShop {ytd_dt}",
        "您好，<br><br>此為系統每日自動產生的報告，若有任何疑慮請聯絡我們。<br>謝謝。",
        attachments=[att_name],
        bcc_emails=mail_bcc_list
    )
    print(f"Daily Notify - Done")

# Use scheduler to health check
scheduler = BackgroundScheduler(daemon=True, job_defaults={'max_instances': 1})
trigger = CronTrigger(year="*", month="*", day="*", hour="*", minute="*/10")
trigger1 = CronTrigger(year="*", month="*", day="*", hour="15", minute="10", second="0")
trigger2 = CronTrigger(year="*", month="*", day="*", hour="1", minute="0", second="0")
scheduler.add_job(keep_awake, trigger=trigger)
scheduler.add_job(daily_update_employee_list, trigger=trigger1)
scheduler.add_job(daily_notify, trigger=trigger2)
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