import os
from flask import Response, request

def check_auth(auth):
    user = os.getenv('WEB_USER_NAME', None)
    pwd = os.getenv('WEB_USER_PASSWD', None)
    return user and pwd and auth and auth.username == user and auth.password == pwd

# 如果驗證失敗，返回 401 回應
def authenticate():
    return Response(
        '未授權訪問，請提供正確帳密。', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

# 裝飾器：需要驗證的路由使用它
def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not check_auth(auth):
            return authenticate()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated