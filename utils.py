from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from collections import defaultdict
from calendar import monthrange
import os

def tw_current_time():
    return datetime.utcnow() + timedelta(hours=8)

def get_diff_days_date(days):
    return tw_current_time() - timedelta(days=days)

def datetim_strptime(dt_str):
    return datetime.strptime(dt_str, '%Y-%m-%d %H:%M')

def get_end_day(year, month):
    return monthrange(year, month)[1]

def get_month_ago(cur_dt, month_diff):
    return cur_dt - relativedelta(months=month_diff)

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

def auto_adjust_width(ws):
    # Automatically adjust width of an excel files columns
    # Ref: https://stackoverflow.com/questions/39529662/python-automatically-adjust-width-of-an-excel-files-columns
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter  # Get the column name
        # Since Openpyxl 2.6, the column name is  ".column_letter" as .column became the column number (1-based)
        for cell in col:
            try:  # Necessary to avoid error on empty cells
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2) * 1.5
        ws.column_dimensions[column].width = adjusted_width

def get_line_liff_mapping(case):
    mapping = defaultdict(lambda: defaultdict(str))
    for k, v in os.environ.items():
        try:
            k = k.upper()
            idx = k.index(f'_{case}_LINE_LIFF_ID')
            mapping[case][k[:idx].lower()] = v
        except:
            pass
    return mapping