import os
from flask import Response, request

lut_user_auth = set((user, pwd) for user, pwd in zip(os.getenv('WEB_USER_NAME', None).split(','), os.getenv('WEB_USER_PASSWD', None).split(',')) if user and pwd)
admin_auth = [tuple(os.environ['WEB_ADMIN'].split(','))]

def check_auth(auth, auth_table):
    return auth_table and auth and (auth.username, auth.password) in auth_table

def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        print(f"Check - {request.path}")
        auth_table = admin_auth if 'lut-log' in request.path else lut_user_auth
        if not check_auth(auth, auth_table):
            return Response(
                '未授權訪問，請提供正確帳密。', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(auth, *args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated