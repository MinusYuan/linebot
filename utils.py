from datetime import datetime, timedelta
from calendar import monthrange

def tw_current_time():
    return datetime.utcnow() + timedelta(hours=8)

def get_diff_days_date(days):
    return tw_current_time() - timedelta(days=days)

def get_end_day(year, month):
    return monthrange(year, month)[1]

def get_date_list(freq, end_dt):
    if freq == 'D':
        start_dt = get_diff_days_date(1)
    elif freq == 'W':
        start_dt = get_diff_days_date(7)
    elif freq == 'M':
        start_dt = end_dt.replace(day=1)

    date_lst = []
    while start_dt < end_dt:
        date_lst.append(start_dt)
        start_dt += timedelta(days=1)
    return date_lst
    