from datetime import datetime, timedelta

def tw_current_time():
    return datetime.utcnow() + timedelta(hours=8)