from flask import Flask
from flask import render_template,request,redirect,url_for,session
from models import User,Question,Answer,Information,Following, Report_unique,Voting, Vote,ChatRecord, ChatConnection
from exts import db
from werkzeug.security import generate_password_hash, check_password_hash
from decorators import login_required, report_required
from datetime import datetime, timedelta
from sqlalchemy import or_
import flask_whooshalchemyplus
from flask_whooshalchemyplus import index_all
from flask_wtf import FlaskForm
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message, Mail
from flask_uploads import UploadSet, IMAGES, configure_uploads, ALL
from flask_socketio import SocketIO, emit, send, disconnect, join_room, leave_room, rooms
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

import config

app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)
flask_whooshalchemyplus.init_app(app)
mail = Mail(app)
# index_all(app)
admin = Admin(app,name=u'后台管理系统')
# db = SQLAlchemy(app)

nowTime=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# app.config['UPLOADED_PHOTO_DEST'] = os.path.dirname(os.path.abspath(__file__))


photos = UploadSet('PHOTO')
configure_uploads(app, photos)

@expose('/admin/')
def index(self):
	return self.render('admin/index.html')

class MyModelViewBase(ModelView):
	column_display_pk = True
	column_display_all_relations = True

class MyModelViewUser(MyModelViewBase):
	column_formatters = dict(
		password = lambda v, c, m, p: '***' + m.password[-2:])
	column_searchable_list = (User.username, )

admin.add_view(MyModelViewUser(User, db.session))
admin.add_view(ModelView(ChatRecord, db.session))

# adm.run(debug=True)

@app.route('/')
def index():
    context = {
        'questions': Question.query.order_by('-create_time').all()
    }
    if session.get('user_id'):
        user_id = session.get('user_id')
        user = User.query.filter(User.id == user_id).first()
        return render_template('index.html',user = user, **context)
    else:
        return render_template('index.html',**context)

@app.route('/login/',methods=["GET","POST"])
def login():
    if request.method=="GET":
        return render_template('login.html')
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter(User.email == email).first()

        if user:
            if check_password_hash(user.password, password) and user.confirmed==1:
                user.point = user.point + 5

                if user.point >= 50 and user.point < 100:
                    user.grade = 2
                elif user.point >= 100 and user.point < 200:
                    user.grade = 3
                elif user.point >= 200 and user.point < 500:
                    user.grade = 4
                else:
                    user.grade = 5

                session['user_id']=user.id
                session['login_time'] = user.last_login_time
                user.last_login_time = datetime.now()
                #如果想在31天内都不需要登录
                session.permanent=True
                db.session.add(user)
                db.session.commit()
                if user.admin==1:
                    return redirect(url_for('admin.index'))
                else:
                    return redirect(url_for('index'))
            else:
                return u'The password is wrong.'
        else:
            return u'The email is invalid.'

@app.route('/register/',methods=["GET","POST"])
def register():
    if request.method=="GET":
        return render_template('register.html')
    else:
        email = request.form.get('email')
        username = request.form.get('username')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        #check whether the email is already registered
        user = User.query.filter(User.email==email).first()

        if user:
            return u'This email is already registered. Please change another one'
        else:
    # check whether two passwords are the same
            if password1!=password2:
                return u'Passwords are not the same.'
            else:
                password=generate_password_hash(password1)
                user=User(email = email,
                          username = username,
                          password = password,
                          number_of_post = 0,
                          number_of_comment = 0,
                          point = 0,
                          grade = 1,
                          photo = "images/default.png",
                          confirmed = False,
                          admin = 0,
                          report_time = datetime.now() + timedelta(days=-100)
                          )

                info = Information(user_id = user.id)
                info.owner = user
                db.session.add(user)
                db.session.add(info)
                db.session.commit()
                token = generate_confirmation_token(user.email)

                confirm_url = url_for('confirm_email', token=token, _external=True)
                html = render_template('activate.html', confirm_url=confirm_url)
                subject = "Please confirm your email"
                send_email(user.email, subject, html)

                login_user(user)

                return redirect(url_for("unconfirmed"))
                # return redirect(url_for('login'))

#发布帖子
@app.route('/question/',methods=['GET','POST'])
@login_required
@report_required
def question():
    if request.method == 'GET':
        user_id = session.get('user_id')
        user = User.query.filter(User.id == user_id).first()
        return render_template('question.html',user=user)
    else:
        title = request.form.get('title')
        content = request.form.get('content')
        type = request.form.get('type')
        # if type:
        #     return type
        # else:
        #     return u'no type'
        if type == '1':
            kind = 1
        elif type == '2':
            kind = 2
        elif type == '3':
            kind = 3
        elif type == '4':
            kind = 4
        elif type == '5':
            kind = 5
        elif type == '6':
            kind = 6
        elif type == '7':
            kind = 7
        else:
            kind = 8
        question = Question(title=title,content=content,report_reasons_and_times = 'A@0|B@0|C@0|D@0', report_total = 0, type = kind)
        user_id=session.get('user_id')
        user=User.query.filter(User.id==user_id).first()

        user.number_of_post = user.number_of_post + 1
        user.point = user.point + 20

        if user.point >= 50 and user.point < 100:
            user.grade = 2
        elif user.point >= 100 and user.point < 200:
            user.grade = 3
        elif user.point >= 200 and user.point < 500:
            user.grade = 4
        else:
            user.grade = 5

        question.author = user
        # question.author_id = user_id
        flask_whooshalchemyplus.index_one_model(Question)
        db.session.add(question)
        db.session.commit()
        return redirect(url_for('index'))

@app.route('/detail/<question_id>/')
def detail(question_id):
    question_model = Question.query.filter(Question.id==question_id).first()
    author_id = question_model.author_id  # 帖子的作者
    author_user = User.query.filter(User.id == author_id).first()
    info = Information.query.filter(User.id == author_id).first()
    if session.get('user_id'):
        user_id = session.get('user_id')
        user = User.query.filter(User.id == user_id).first() #登录者
        return render_template('detail.html', user=user, info = info, author_user = author_user, question=question_model)
    else:
        return render_template('detail.html', info = info, author_user = author_user, question=question_model)


@app.route('/add_answer/',methods=['POST'])
@login_required
@report_required
def add_answer():
    question_id = request.form.get('question_id')
    content = request.form.get('answer_content')
    answer = Answer(content=content,report_reasons_and_times = 'A@0|B@0|C@0|D@0', report_total = 0)
    user_id = session.get('user_id')
    user = User.query.filter(User.id == user_id).first()

    user.number_of_comment = user.number_of_comment + 1
    user.point = user.point + 10

    if user.point >= 50 and user.point < 100:
        user.grade = 2
    elif user.point >= 100 and user.point < 200:
        user.grade = 3
    elif user.point >= 200 and user.point < 500:
        user.grade = 4
    else:
        user.grade = 5

    answer.author = user
    # answer.author_id = user_id
    answer.question = Question.query.filter(Question.id==question_id).first()
    db.session.add(answer)
    db.session.commit()
    return redirect(url_for('detail',question_id=question_id))

@app.route('/logout/',methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('login'))

#编辑个人信息
@app.route('/edit/', methods=['GET','POST'])
@login_required
def edit():
    if request.method == 'GET':
        return render_template('edit_personal_detail.html')
    else:
        user_id = session.get('user_id')
        user = User.query.filter(User.id == user_id).first()
        information = Information.query.filter(Information.user_id == user_id).first()

        username = request.form.get('username')
        gender = request.form.get('gender')
        age = request.form.get('age')
        major = request.form.get('major')
        group = request.form.get('group')  # group 代表class
        hobbies = request.form.get('hobbies')
        introduction = request.form.get('introduction')

        if username:
            user.username = username
        if gender:
            information.gender = gender
        if age:
            information.age = age
        if major:
            information.major = major
        if group:
            information.group = group
        if hobbies:
            information.hobbies = hobbies
        if introduction:
            user.introduction = introduction

        if 'photo' in request.files: #如果用户上传了头像
            filename = photos.save(request.files['photo'])
            url = "images/" + filename
            user.photo = url
        else: #如果用户没有上传了头像
            url = "images/default.png"
        db.session.commit()
        return redirect(url_for('info', user_id=user_id))

@app.route('/info/<user_id>/')
@login_required
def info(user_id):
    user_model = User.query.filter(User.id == user_id).first()
    info_model = Information.query.filter(Information.user_id == user_id).first()

    info_model.number_of_following = Following.query.filter(Following.user_id == user_id).count()
    info_model.number_of_followed = Following.query.filter(Following.followed_user_id == user_id).count()

    questions = {
        'questions': Question.query.filter(Question.author_id == user_id).all()
    }

    return render_template('default_personal_detail.html', **questions, user=user_model,info=info_model,time=session.get('login_time'))


@app.route('/search/', methods=['POST','GET'])
def search():
    search=request.form.get('q')
    if not search:
        return redirect(url_for('index'))
    return redirect(url_for('search_results', query=search))


@app.route('/search_results/<query>')
def search_results(query):
    results = Question.query.whoosh_search(query).all()

    if session.get('user_id'):
        user_id = session.get('user_id')
        user = User.query.filter(User.id == user_id).first()
        return render_template('search_results.html', user=user, query=query, results=results)
    else:
        return render_template('search_results.html', query=query, results=results)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email

@app.route('/confirm/<token>')
@login_required
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        return u'The confirmation link is invalid or has expired.'
    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        return u'Account already confirmed. Please login.'
    else:
        user.confirmed = True
        user.confirmed_on = datetime.now()
        db.session.add(user)
        db.session.commit()
    return redirect(url_for('index'))

def send_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender='forumaces@126.com'
        )
    mail.send(msg)

def login_user(user):
    user.point = user.point + 5

    if user.point >= 50 and user.point < 100:
        user.grade = 2
    elif user.point >= 100 and user.point < 200:
        user.grade = 3
    elif user.point >= 200 and user.point < 500:
        user.grade = 4
    else:
        user.grade = 5
    session['user_id'] = user.id
    session['login_time'] = user.last_login_time
    user.last_login_time = datetime.now()
    # 如果想在31天内都不需要登录
    session.permanent = True
    db.session.add(user)
    db.session.commit()

@app.route('/unconfirmed/')
@login_required
def unconfirmed():
    user_id = session.get('user_id')
    user = User.query.filter(User.id == user_id).first()
    if user.confirmed:
        return redirect(url_for('index'))
    return render_template('unconfirmed.html')

@app.route('/resend/')
@login_required
def resend_confirmation():
    user_id = session.get('user_id')
    user = User.query.filter(User.id == user_id).first()
    token = generate_confirmation_token(user.email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = render_template('activate.html', confirm_url=confirm_url)
    subject = "Please confirm your email"
    send_email(user.email, subject, html)
    return redirect(url_for('unconfirmed'))

@app.route('/following/<person_id>/', methods=['POST','GET'])
def following(person_id):
    user_id = session.get('user_id')
    user = User.query.filter(User.id == user_id).first()
    elseuser = User.query.filter(User.id == person_id).first()
    f = Following.query.filter(Following.user_id == person_id).all()
    list = []
    for values in f:
        id = values.followed_user_id
        user1 = User.query.filter(User.id == id).first()
        list.append(user1)
    return render_template('friend_list.html',list = list,user = user,elseuser=elseuser)

@app.route('/followed/<person_id>/', methods=['POST','GET'])
def followed(person_id):
    user_id = session.get('user_id')
    user = User.query.filter(User.id == user_id).first()
    elseuser = User.query.filter(User.id == person_id).first()
    f = Following.query.filter(Following.followed_user_id == person_id).all()
    list = []
    for values in f:
        id = values.user_id
        user1 = User.query.filter(User.id == id).first()
        list.append(user1)
    return render_template('friend_list.html',list = list,user = user,elseuser=elseuser)

@app.route('/follow/<person_id>/', methods=['POST','GET'])
def follow(person_id):
    user_id = session.get('user_id')
    if str(user_id)==person_id:
        return redirect(url_for('elseinfo', user_id=person_id))
    else:
        follow = Following(user_id=user_id, followed_user_id=person_id)
        db.session.add(follow)
        db.session.commit()
        return redirect(url_for('elseinfo', user_id=person_id))

@app.route('/report/<id>/<num>/', methods=['POST','GET'])
def report(id,num):
    if request.method == 'GET':
        return render_template('register.html')
    else:
        total_num=0
        question_model = Question.query.filter(Question.id == id).first()
        reason = request.form.get('reason')
        #若被举报的是问题，则num=1
        if num=='1':
            report_unique = Report_unique.query.filter(Report_unique.user_id==session.get('user_id'),Report_unique.option==1,Report_unique.option_id==id).first()
            if report_unique:
                return u'You can only report once.'
            else:
                #question_model = Question.query.filter(Question.id==id).first()
                number1=question_model.report_total+1
                question_model.report_total=number1
                if reason == 'A':
                    reasons_and_times = question_model.report_reasons_and_times
                    each_reason_and_time = reasons_and_times.split('|')  # 每个原因+次数
                    number = each_reason_and_time[0].split('@')  # A原因和次数
                    number2 = int(number[1])  # 把次数转换为int
                    number2 = number2 + 1  # 更新次数
                    number1 = str(number2)  # 改回string
                    question_model.report_reasons_and_times = "A@" + number1 + "|" + each_reason_and_time[1] + "|" + \
                                                          each_reason_and_time[2] + "|" + each_reason_and_time[3]
                    db.session.commit()
                elif reason == 'B':
                    reasons_and_times = question_model.report_reasons_and_times
                    each_reason_and_time = reasons_and_times.split('|')  # 每个原因+次数
                    number = each_reason_and_time[1].split('@')  # B原因和次数
                    number2 = int(number[1])  # 把次数转换为int
                    number2 = number2 + 1  # 更新次数
                    number1 = str(number2)  # 改回string
                    question_model.report_reasons_and_times = each_reason_and_time[0] + "|" + "B@" + number1 + "|" + \
                                                          each_reason_and_time[2] + "|" + each_reason_and_time[3]
                    db.session.commit()
                elif reason == 'C':
                    reasons_and_times = question_model.report_reasons_and_times
                    each_reason_and_time = reasons_and_times.split('|')  # 每个原因+次数
                    number = each_reason_and_time[2].split('@')  # C原因和次数
                    number2 = int(number[1])  # 把次数转换为int
                    number2 = number2 + 1  # 更新次数
                    number1 = str(number2)  # 改回string
                    question_model.report_reasons_and_times = each_reason_and_time[0] + "|" + each_reason_and_time[
                        1] + "|" + "C@" + number1 + "|" + each_reason_and_time[3]
                    db.session.commit()
                else:
                    reasons_and_times = question_model.report_reasons_and_times
                    each_reason_and_time = reasons_and_times.split('|')  # 每个原因+次数
                    number = each_reason_and_time[3].split('@')  # D原因和次数
                    number2 = int(number[1])  # 把次数转换为int
                    number2 = number2 + 1  # 更新次数
                    number1 = str(number2)  # 改回string
                    question_model.report_reasons_and_times = each_reason_and_time[0] + "|" + each_reason_and_time[
                        1] + "|" + each_reason_and_time[2] + "|" + "D@" + number1
                    db.session.commit()

                user_id = question_model.author_id
                total_num = question_model.report_total
                report = Report_unique(user_id=session.get('user_id'), option=1, option_id=id)
                db.session.add(report)
                db.session.commit()

                if total_num>50:
                    #举报次数超过50， 禁言
                    user = User.query.filter(User.id == user_id).first()
                    user.report_time = datetime.now()
                    db.session.commit()
        # 若被举报的是回答，则num=1
        elif num == '0':  # 举报回答
            report_unique = Report_unique.query.filter(Report_unique.user_id == session.get('user_id'),
                                                       Report_unique.option == 0, Report_unique.option_id == id).first()
            if report_unique:
                return u'You can only report once.'
            else:
                answer_model = Answer.query.filter(Answer.id == id).first()
                answer_model.report_total += 1

                # 数据库添加
                if reason == 'A':
                    reasons_and_times = answer_model.report_reasons_and_times
                    each_reason_and_time = reasons_and_times.split('|')  # 每个原因+次数
                    number = each_reason_and_time[0].split('@')  # A原因和次数
                    number2 = int(number[1])  # 把次数转换为int
                    number2 = number2 + 1  # 更新次数
                    number1 = str(number2)  # 改回string
                    question_model.report_reasons_and_times = "A@" + number1 + "|" + each_reason_and_time[1] + "|" + \
                                                          each_reason_and_time[2] + "|" + each_reason_and_time[3]
                    db.session.commit()
                elif reason == 'B':
                    reasons_and_times = answer_model.report_reasons_and_times
                    each_reason_and_time = reasons_and_times.split('|')  # 每个原因+次数
                    number = each_reason_and_time[1].split('@')  # B原因和次数
                    number2 = int(number[1])  # 把次数转换为int
                    number2 = number2 + 1  # 更新次数
                    number1 = str(number2)  # 改回string
                    question_model.report_reasons_and_times = each_reason_and_time[0] + "|" + "B@" + number1 + "|" + \
                                                          each_reason_and_time[2] + "|" + each_reason_and_time[3]
                    db.session.commit()
                elif reason == 'C':
                    reasons_and_times = answer_model.report_reasons_and_times
                    each_reason_and_time = reasons_and_times.split('|')  # 每个原因+次数
                    number = each_reason_and_time[2].split('@')  # C原因和次数
                    number2 = int(number[1])  # 把次数转换为int
                    number2 = number2 + 1  # 更新次数
                    number1 = str(number2)  # 改回string
                    question_model.report_reasons_and_times = each_reason_and_time[0] + "|" + each_reason_and_time[
                        1] + "|" + "C@" + number1 + "|" + each_reason_and_time[3]
                    db.session.commit()
                else:
                    reasons_and_times = answer_model.report_reasons_and_times
                    each_reason_and_time = reasons_and_times.split('|')  # 每个原因+次数
                    number = each_reason_and_time[3].split('@')  # D原因和次数
                    number2 = int(number[1])  # 把次数转换为int
                    number2 = number2 + 1  # 更新次数
                    number1 = str(number2)  # 改回string
                    question_model.report_reasons_and_times = each_reason_and_time[0] + "|" + each_reason_and_time[
                        1] + "|" + each_reason_and_time[2] + "|" + "D@" + number1
                    db.session.commit()
                user_id = answer_model.author_id
                total_num = answer_model.report_total
                report=Report_unique(user_id=session.get('user_id'),option=0,option_id=id)
                db.session.add(report)
                db.session.commit()

                if total_num>50:
                    #举报次数超过50， 禁言
                    user = User.query.filter(User.id == user_id).first()
                    user.report_time = datetime.now()
                    db.session.commit()
        return render_template('detail.html', question=question_model)

@app.route('/elseinfo/<user_id>/')
@login_required
def elseinfo(user_id):
    #要看的人
    else_user = User.query.filter(User.id == user_id).first()
    info_model = Information.query.filter(Information.user_id == user_id).first()

    info_model.number_of_following = Following.query.filter(Following.user_id == user_id).count()
    info_model.number_of_followed = Following.query.filter(Following.followed_user_id == user_id).count()

    questions = {
        'questions': Question.query.filter(Question.author_id == user_id).all()
    }
    #登录的人
    login_user_id = session.get('user_id')
    user = User.query.filter(User.id == login_user_id).first()
    return render_template('others_information.html', **questions, user=user, else_user = else_user, info=info_model,time=session.get('login_time'))

#用户自己删除自己的帖子，应该跳出一个对话框 --->“确定删除吗?”
@app.route('/delete/<question_id>/')
def delete_post(question_id):
    question = Question.query.filter(Question.id == question_id).first()
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('info',user_id=session.get('user_id')))

#发起投票
@app.route('/vote/', methods=['POST','GET'])
@login_required
def vote():
    if request.method == 'GET':
        return render_template('vote.html')
    else:
        user_id = session.get('user_id')
        title = request.form.get('title')
        option1 = request.form.get('option1')
        option1 = "A. " + option1
        option2 = request.form.get('option2')
        option2 = "B. " + option2
        option3 = request.form.get('option3')
        option3 = "C. " + option3
        option4 = request.form.get('option4')
        option4 = "D. " + option4
        if option3 == 'None'and option4 == 'None': #若只有两个选项
            vote = Vote(title=title,founder_id = user_id, sum_options = 0,
                          option1 = option1, sum_option1 = 0,
                          option2 = option2, sum_option2 = 0,
                          option3 = option3, sum_option3 = -1,
                          option4 = option4, sum_option4 = -1)
        elif option3 == 'None'and option4 != 'None': #若只有三个选项
            vote = Vote(title=title, founder_id=user_id, sum_options = 0,
                        option1=option1, sum_option1=0,
                        option2=option2, sum_option2=0,
                        option3=option4, sum_option3=0,
                        option4=option3, sum_option4=-1)
        elif option3 != 'None'and option4 == 'None': #若只有三个选项
            vote = Vote(title=title, founder_id=user_id, sum_options = 0,
                        option1=option1, sum_option1=0,
                        option2=option2, sum_option2=0,
                        option3=option3, sum_option3=0,
                        option4=option4, sum_option4=-1)
        else: #若有四个选项
            vote = Vote(title=title, founder_id = user_id, sum_options = 0,
                          option1 = option1, sum_option1 = 0,
                          option2 = option2, sum_option2 = 0,
                          option3 = option3, sum_option3 = 0,
                          option4 = option4, sum_option4 = 0)
        db.session.add(vote)
        db.session.commit()
        return redirect(url_for('vote_detail',vote_id=vote.id))


# 参与投票
@login_required
@app.route('/voting/', methods=['POST', 'GET'])
def voting():
    vote_id = request.form.get('vote_id')  # CC像detail界面里那么写，表单中有隐藏的一项
    option = request.form.get('option')
    user_id = session.get('user_id')

    vote = Vote.query.filter(Vote.id == vote_id).first()  # 找到这个投票
    vote.sum_options = vote.sum_options + 1
    db.session.commit()

    if option == 'A':
        vote.sum_option1 = vote.sum_option1 + 1
    elif option == 'B':
        vote.sum_option2 = vote.sum_option2 + 1
    elif option == 'C':
        vote.sum_option3 = vote.sum_option3 + 1
    else:
        vote.sum_option4 = vote.sum_option4 + 1
    db.session.commit()

    voting = Voting(vote_id=vote_id, option=option, user_id=user_id)
    db.session.add(voting)
    db.session.commit()
    return redirect(url_for('vote_detail', vote_id=vote_id))

#取消关注某人
@app.route('/delete_follow/<person_id>/', methods=['POST','GET'])
def delete_follow(person_id):
    user_id = session.get('user_id')
    follow = Following.query.filter(Following.user_id==user_id,Following.followed_user_id==person_id).first()
    db.session.delete(follow)
    db.session.commit()
    return redirect(url_for('elseinfo', user_id=person_id)) #?????


#显示所有投票
@app.route('/all_votes/')
def all_votes():
    context = {
        'questions': Vote.query.order_by('-create_time').all() #按时间从近到远排序
    }
    if session.get('user_id'):
        user_id = session.get('user_id')
        user = User.query.filter(User.id == user_id).first() #当前登录的人
        return render_template('index.html', user=user, **context, vote=1) #???
    else:
        return render_template('index.html', **context, vote=1) #????


# 查看某个投票详情（分两种） ---> 已参与过的投票 和 没有参与过的投票
@app.route('/vote/detail/<vote_id>')
def vote_detail(vote_id):
    vote = Vote.query.filter(Vote.id == vote_id).first()  # 得到该投票的详情
    author_id = vote.founder_id  # 投票的发起人
    author_user = User.query.filter(User.id == author_id).first()
    author_info = Information.query.filter(User.id == author_id).first()
    if session.get('user_id'):
        user_id = session.get('user_id')
        user = User.query.filter(User.id == user_id).first()  # 登录者

        # 判断 vote_id 这个投票，登录得用户有没有参与过
        voting = Voting.query.filter(Voting.vote_id == vote_id, Voting.user_id == user_id).first()
        if voting:  # 该用户参与过这个投票
            # my_voting = Voting.query.filter(Voting.vote_id == vote_id).first()
            return render_template('vote_detail.html', my_voting=voting, user=user, author_info=author_info,
                                   author_user=author_user, vote=vote)
        else:  # 该用户没有参与过这个投票
            return render_template('vote_detail.html', user=user, author_info=author_info, author_user=author_user, vote=vote)
    else:
        return render_template('vote_detail.html', author_info=author_info, author_user=author_user, vote=vote)

#显示某个分类下的所有帖子
@app.route('/choose/type/<num>')
def type(num):
    # return num
    if num == '1':
        # return u'111'
        context = {
            'questions': Question.query.filter(Question.type == 1).order_by('-create_time').all()
        }
    elif num == '2':
        # return u'222'
        context = {
            'questions': Question.query.filter(Question.type == 2).order_by('-create_time').all()
        }
    elif num == '3':
        # return u'333'
        context = {
            'questions': Question.query.filter(Question.type == 3).order_by('-create_time').all()
        }
    elif num == '4':
        # return u'444'
        context = {
            'questions': Question.query.filter(Question.type == 4).order_by('-create_time').all()
        }
    elif num == '5':
        # return u'555'
        context = {
            'questions': Question.query.filter(Question.type == 5).order_by('-create_time').all()
        }
    elif num == '6':
        # return u'666'
        context = {
            'questions': Question.query.filter(Question.type == 6).order_by('-create_time').all()
        }
    elif num == '7':
        # return u'777'
        context = {
            'questions': Question.query.filter(Question.type == 7).order_by('-create_time').all()
        }
    else:
        # return u'888'
        context = {
            'questions': Question.query.filter(Question.type == 8).order_by('-create_time').all()
        }
    if session.get('user_id'):
        user_id = session.get('user_id')
        user = User.query.filter(User.id == user_id).first()
        return render_template('index.html', user=user, **context)
    else:
        return render_template('index.html', **context)


@app.route('/change_password/', methods=['POST','GET'])
def change_password():
    if request.method=="GET":
        return render_template('change_password.html')
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        new_password1 = request.form.get('new_password1')
        new_password2 = request.form.get('new_password2')
        user = User.query.filter(User.email == email).first()

        if user:
            if check_password_hash(user.password, password):
                if new_password1==new_password2:
                    password = generate_password_hash(new_password1)
                    user.password=password
                    db.session.commit()
                else:
                    return u'Your passwords should be consistent'
            else:
                return u'The password is wrong.'
        else:
            return u'This account does not exist.'

# myID=2
# uid=1
@app.route('/chat/<uid>')
def chat(uid):
    session['else_id'] = uid
    return render_template('chat.html')


def selectConnection(id1, id2):
	connection1 = ChatConnection.query.filter(ChatConnection.u_id1==id1, ChatConnection.u_id2==id2)
	connection2 = ChatConnection.query.filter(ChatConnection.u_id1==id2, ChatConnection.u_id2==id1)
	if connection1.one_or_none() == None and connection2.one_or_none() == None:
		return None
	else:
		if connection1.one_or_none() == None:
			return connection2
		else:
			return connection1


# # show status and chatting history
# @socketio.on('connect', namespace='/test')
# def test_connect():
#     emit('my response', {'data': '(system):Connected!', 'time': str(nowTime)})
#
#     connection = selectConnection(myID, uid)
#     if connection == None:
#         create_connect = ChatConnection(u_id1=myID, u_id2=uid)
#         db.session.add(create_connect)
#         db.session.commit()
#     else:
#         connectionid = connection.first().id
#
#         records = ChatRecord.query.filter(ChatRecord.chat_id == connectionid).all()
#         # print(records)
#
#         for r in records:
#             t = r.create_time
#             if r.author_id == myID:
#                 r = r.content
#                 if r != "I'm connected!" and r != "Connected!":
#                     emit('my response', {'data': str(r), 'time': '(history ' + str(t) + '): '})
#             else:
#                 r = r.content
#                 if r != "I'm connected!" and r != "Connected!":
#                     emit('her response', {'data': str(r), 'time': '(history ' + str(t) + '): '})

# show status and chatting history
@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my response', {'data': '(system):Connected!', 'time': str(nowTime)})

    connection = selectConnection(session.get('user_id'), session['else_id'])
    if connection == None:
        create_connect = ChatConnection(u_id1=session.get('user_id'), u_id2=session['else_id'])
        db.session.add(create_connect)
        db.session.commit()
    else:
        connectionid = connection.first().id

        records = ChatRecord.query.filter(ChatRecord.chat_id == connectionid).all()
        # print(records)

        for r in records:
            t = r.create_time
            if r.author_id == session.get('user_id'):
                r = r.content
                if r != "I'm connected!" and r != "Connected!":
                    emit('my response', {'data': str(r), 'time': '(history ' + str(t) + '): '})
            else:
                r = r.content
                if r != "I'm connected!" and r != "Connected!":
                    emit('her response', {'data': str(r), 'time': '(history ' + str(t) + '): '})




# @socketio.on('my_room_event', namespace='/test')
# def send_room_message(message):
# 	connection = selectConnection(myID, uid)
# 	connectionid = selectConnection(myID, uid).first().id
# 	join_room(connectionid)
# 	content = message['data']
# 	connection = selectConnection(myID, uid)
# 	record = ChatRecord(content = content, author_id = myID, chat_id = connectionid)
# 	db.session.add(record)
# 	db.session.commit()
# 	t = record.create_time
# 	emit('my response', {'data': message['data'], 'time': '(history ' + str(t) + '): '}, room=connectionid)

@socketio.on('my_room_event', namespace='/test')
def send_room_message(message):
	connection = selectConnection(session.get('user_id'), session['else_id'])
	connectionid = selectConnection(session.get('user_id'), session['else_id']).first().id
	join_room(connectionid)
	content = message['data']
	connection = selectConnection(session.get('user_id'), session['else_id'])
	record = ChatRecord(content = content, author_id = session.get('user_id'), chat_id = connectionid)
	db.session.add(record)
	db.session.commit()
	t = record.create_time
	emit('my response', {'data': message['data'], 'time': '(history ' + str(t) + '): '}, room=connectionid)




# # close socket connection
# @socketio.on('disconnect_request', namespace = '/test')
# def test_disconnect():
# 	connection = selectConnection(myID, uid)
# 	connectionid = selectConnection(myID, uid).first().id
# 	emit('my response', {'data': '(system)Disconnected!', 'time': str(nowTime)})
# 	emit('my response', {'data': 'Out room: ' + str(connectionid), 'time': str(nowTime)})
# 	leave_room(connectionid)
# 	disconnect()

# close socket connection
@socketio.on('disconnect_request', namespace = '/test')
def test_disconnect():
	connection = selectConnection(session.get('user_id'), session['else_id'])
	connectionid = selectConnection(session.get('user_id'), session['else_id']).first().id
	emit('my response', {'data': '(system)Disconnected!', 'time': str(nowTime)})
	emit('my response', {'data': 'Out room: ' + str(connectionid), 'time': str(nowTime)})
	leave_room(connectionid)
	disconnect()




@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')





if __name__ == '__main__':
    socketio.run(app)


# if __name__ == '__main__':
#     app.run()



