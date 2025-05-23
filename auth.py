import os
from flask import Response, request

user_auth = set((user, pwd) for user, pwd in zip(os.getenv('WEB_USER_NAME', None).split(','), os.getenv('WEB_USER_PASSWD', None).split(',')) if user and pwd)

def check_auth(auth):
    return user_auth and auth and (auth.username, auth.password) in user_auth

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
        return f(auth, *args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated