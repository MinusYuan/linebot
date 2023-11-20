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

# Local package
from console import Console
from notify import EMail
from utils import tw_current_time

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
    print(f"UID: {user_id}, Reply: {reply[:15]}")
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

def weekly_notify():
    print(f"Weekly Notify - Start")
    keyword, users = con.get_search_cnt_report_then_reset()
    attachments = []
    for d, fn in ((keyword, 'keyword'), (users, 'users')):
        df = pd.DataFrame(d.items(), columns=[fn, 'Count'], dtype=str)
        sorted_df = df.sort_values(by='Count', ascending=False)
        sorted_df.to_csv(f"{fn}.csv", index=False, header=True, encoding='utf-8-sig')
        attachments.append(f"{fn}.csv")

    cur_time = tw_current_time().strftime("%Y-%m-%d")
    mail = EMail(os.getenv('EMAIL_KEY'))
    mail.send(
        os.getenv('mail_to').split(','),
        [],
        f"每周報表 - TTShop {cur_time}",
        "您好，<br><br>此為系統每周自動產生的報告，若有任何疑慮請聯絡我們。<br>謝謝。",
        attachments
    )
    print(f"Weekly Notify - Done")

# Use scheduler to health check
scheduler = BackgroundScheduler(daemon=True, job_defaults={'max_instances': 1})
trigger = CronTrigger(year="*", month="*", day="*", hour="*", minute="*/10")
trigger1 = CronTrigger(year="*", month="*", day="*", hour="15", minute="50", second="0")
trigger2 = CronTrigger(year="*", month="*", day="*", day_of_week="6", hour="16", minute="0", second="0")
scheduler.add_job(keep_awake, trigger=trigger)
scheduler.add_job(daily_update_employee_list, trigger=trigger1)
scheduler.add_job(weekly_notify, trigger=trigger2)
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