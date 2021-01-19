from exts import db
from datetime import datetime
from datetime import date
from jieba.analyse.analyzer import ChineseAnalyzer
import flask_whooshalchemyplus

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer,primary_key = True, autoincrement = True)
    email = db.Column(db.String(100), nullable = False, unique = True)
    username = db.Column(db.String(100), nullable = False)
    password = db.Column(db.String(100), nullable = False)

    number_of_post = db.Column(db.Integer)
    number_of_comment = db.Column(db.Integer)
    point = db.Column(db.Integer)
    grade = db.Column(db.Integer)
    register_time = db.Column(db.DateTime, default = datetime.now)
    last_login_time = db.Column(db.DateTime)
    introduction = db.Column(db.Text)
    photo = db.Column(db.String(100), nullable=True)  # 存储图片的路径

    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)

    report_time = db.Column(db.DateTime, nullable=True) #所有的数据都是这个固定的时间
    admin = db.Column(db.Integer) #判断是否是管理员

class Question(db.Model):
    __tablename__ = 'question'
    __searchable__ = ['content', 'title']
    __analyzer__ = ChineseAnalyzer()
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    type = db.Column(db.Integer, nullable=False)  # 用数字代替具体的分类
    title = db.Column(db.String(100), nullable = False)
    content = db.Column(db.Text, nullable = False)
    create_time = db.Column(db.DateTime, default = datetime.now)
    author_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    report_total = db.Column(db.Integer,nullable = True)
    report_reasons_and_times = db.Column(db.String(100), nullable = True)

    # answers = db.relationship('Answer',lazy='dynamic', cascade='all, delete-orphan',passive_deletes=True, backref=db.backref('question'))
    author = db.relationship('User',backref = db.backref('questions'))

    def __repr__(self):
        return '{0}(title={1})'.format(self.__class__.__name__, self.title)

class Answer(db.Model):
    __tablename__ = 'answer'
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    content = db.Column(db.Text, nullable = False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default = datetime.now)
    report_total = db.Column(db.Integer,nullable = True)
    report_reasons_and_times = db.Column(db.String(100), nullable = True)

    question = db.relationship('Question',backref = db.backref('answers',order_by = id.desc()))
    author = db.relationship('User',backref = db.backref('answers'))


class Information(db.Model):
    __tablename__ = 'info'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    gender = db.Column(db.String(100))
    birthday = db.Column(db.String(100))
    age = db.Column(db.Integer)
    major = db.Column(db.String(100))
    group = db.Column(db.String(100)) #i.e. class
    hobbies = db.Column(db.Text)

    number_of_followed = db.Column(db.Integer) #粉丝总数
    number_of_following = db.Column(db.Integer) #关注总数

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')) #foreign key (connect to the table "user")

    owner = db.relationship('User',backref = db.backref('information'))

class Following(db.Model):
    __tablename__ = 'follow'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)
    followed_user_id = db.Column(db.Integer)

class Report_unique(db.Model): #为限制一个用户只能举报一个帖子/回复一次
    __tablename__ = 'report'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=True)
    option = db.Column(db.Integer, nullable=True)
    option_id = db.Column(db.Integer, nullable=True)


class Vote(db.Model):  # 记录每个投票活动的具体选项等信息
    __tablename__ = 'vote'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    founder_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default=datetime.now)
    title = db.Column(db.String(100), nullable=False)

    option1 = db.Column(db.String(100), nullable=False)
    sum_option1 = db.Column(db.Integer, nullable=False)

    option2 = db.Column(db.String(100), nullable=False)
    sum_option2 = db.Column(db.Integer, nullable=False)

    option3 = db.Column(db.String(100), nullable=True)
    sum_option3 = db.Column(db.Integer, nullable=True)

    option4 = db.Column(db.String(100), nullable=True)
    sum_option4 = db.Column(db.Integer, nullable=True)

    sum_options = db.Column(db.Integer, nullable=False)

    author = db.relationship('User', backref=db.backref('votes'))

class Voting(db.Model): #记录每个用户自己的投票行为
    __tablename__ = 'voting'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vote_id = db.Column(db.Integer, db.ForeignKey('voting.id'))
    option = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

class ChatRecord(db.Model):
    __tablename__ = 'chatrecord'
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    content = db.Column(db.Text, nullable = False)
    create_time = db.Column(db.DateTime, default = datetime.now)
    author_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    chat_id = db.Column(db.Integer,db.ForeignKey('chatconnection.id'))
    # author = db.relationship('User',backref = db.backref('chatrecord'))

class ChatConnection(db.Model):
    __tablename__ = 'chatconnection'
    id = db.Column(db.Integer,primary_key = True, autoincrement = True)
    u_id1 = db.Column(db.Integer)
    u_id2 = db.Column(db.Integer)
