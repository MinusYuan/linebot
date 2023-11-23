from datetime import datetime, timedelta

def tw_current_time():
    return datetime.utcnow() + timedelta(hours=8)

def get_tomorrow_date():
    return (tw_current_time() + timedelta(hours=1)).strftime("%Y%m%d")

def get_yesterday_date():
    return (tw_current_time() - timedelta(days=1)).strftime("%Y%m%d")