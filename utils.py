from datetime import datetime, timedelta

def tw_current_time():
    return datetime.utcnow() + timedelta(hours=8)

def get_tomorrow_date():
    return (tw_current_time() + timedelta(minutes=30)).strftime("%Y%m%d")