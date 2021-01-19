#encoding: utf-8
from functools import wraps
from flask import session, redirect, url_for
from models import User
from datetime import datetime
#登陆限制的装饰器
def login_required(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        if session.get('user_id'):
            return func(*args,**kwargs)
        else:
            return redirect(url_for('login'))

    return wrapper


# def check_confirmed(func):
#     @wraps(func)
#     def decorated_function(*args, **kwargs):
#         user_id = session.get('user_id')
#         user = User.query.filter(User.id == user_id).first()
#         if user.confirmed is False:
#             return redirect(url_for('unconfirmed'))
#
#         return func(*args, **kwargs)
#
#     return decorated_function

#管理员限制的装饰器
def admin_required(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        if session.get('user_id'):
            id=session.get('user_id')
            user = User.query.filter(User.id == id).first()
            if user.admin==1:
                return func(*args,**kwargs)
            else:
                return redirect(url_for('login'))
        else:
            return redirect(url_for('login'))

    return wrapper

#禁言限制的装饰器
def report_required(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        if session.get('user_id'):
            id=session.get('user_id')
            user = User.query.filter(User.id == id).first()
            time=datetime.now()
            report_time=user.report_time
            days=(time-report_time).days
            if days>10:
                return func(*args,**kwargs)
            else:
                return u'Sorry, you are not allowed for this function.'
        else:
            return redirect(url_for('login'))

    return wrapper
