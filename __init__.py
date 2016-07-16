from flask import Flask, render_template, flash, redirect, url_for, request, session, send_from_directory

from werkzeug import secure_filename

import sqlite3
from contextlib import closing
import gc
import os

from functools import wraps

# local module
from content_manager import Content

# third party
from wtforms import Form, TextField, PasswordField, BooleanField, validators
from passlib.hash import sha256_crypt

import pygal


app = Flask(__name__)


# configration
app.config.update(
    DEBUG=True,
    DATABASE='my.db',
    SECRET_KEY='\xc9\xe7\xfd\xc4\x1f\xef`\x1b;6\xf6\xd9\xc5\xbe$o\xce\xc2\xb4p\x83\xa3[\r',
    UPLAOD_FOLDER=os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'media'),
    # UPLAOD_FOLDER=r'D:\WebRoot\FlaskProject\FlaskApp\FlaskApp\media'
)

TOPIC_LIST = Content()


# DATABASE operation
def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


# run in shell
def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', 'r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    db = connect_db()
    cur = db.cursor()
    return db, cur


# a decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("You need login first")
            return redirect(url_for('login'))
    return wrap


# routers
@app.route('/')
def homepage():
    flash("Hey, welcome back home~")
    return render_template('home.html')


@app.route('/dashboard/')
@login_required
def dashboard():
    # return str(TOPIC_LIST)
    return render_template('dashboard.html', TOPIC_LIST=TOPIC_LIST)


@app.errorhandler(404)
def page_not_found(error):
    try:
        return render_template('404.html')
    except Exception as e:
        return render_template('500.html', error=error)


@app.errorhandler(405)
def method_not_found(error):
    return render_template('405.html')


@app.route('/login/', methods=['POST', 'GET'])
def login():
    try:
        error = None
        if request.method == 'POST':

            username = request.form['username']
            password = request.form['password']

            db, cur = get_db()

            passwd_hash_tuple = cur.execute(
                'SELECT password FROM users WHERE username=?', [username]).fetchone()   # return a tuple

            if not passwd_hash_tuple:
                error = 'Invalid username'
            elif not sha256_crypt.verify(password, passwd_hash_tuple[0]):
                error = 'Invalid password'
            else:
                flash('Hey %s, you are in' % username)
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('dashboard'))

        gc.collect()
        return render_template('login.html', error=error)

    except Exception as e:
        return str(e)


@app.route('/logout/')
@login_required
def logout():
    session.pop('logged_in', None)
    flash("You have logged out")
    return redirect(url_for('dashboard'))


class RegistrationForm(Form):

    username = TextField(
        'Username', [validators.Length(min=4, max=20)])
    email = TextField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [validators.Required(
    ), validators.EqualTo('confirm', message='Passwords must match.')])
    confirm = PasswordField('Password Again')
    accept_tos = BooleanField(
        "<small>I accept it</small>", [validators.Required()])


@app.route('/register/', methods=['POST', 'GET'])
def register():
    try:
        form = RegistrationForm(request.form)

        if request.method == 'POST' and form.validate():
            username = form.username.data
            email = form.email.data
            password = sha256_crypt.encrypt(str(form.password.data))

            db, cur = get_db()

            x = cur.execute(
                'SELECT * FROM users WHERE username = ?', [username])

            if x.fetchall():
                flash("That username is already taken, please choose another")
                return render_template('register.html', form=form)

            else:
                cur.execute("INSERT INTO users (username, password, email) VALUES(?,?,?)", [
                            username, password, email])
                db.commit()

                flash("Thanks for registering!")

                cur.close()
                db.close()
                gc.collect()    # collect garbage

                session['logged_in'] = True
                session['username'] = username

                return redirect(url_for('dashboard'))

        return render_template('register.html', form=form)

    except Exception as e:
        return str(e)


@app.route('/pygalexample/')
def pygalexample():
    try:
        graph = pygal.Line()
        graph.title = '% Change Coolness of programming languages over time.'
        graph.x_labels = ['2011', '2012', '2013', '2014', '2015', '2016']
        graph.add('Python', [15, 31, 89, 200, 356, 900])
        graph.add('Java', [15, 45, 76, 80, 91, 95])
        graph.add('C++', [5, 51, 54, 102, 150, 201])
        graph.add('All others combined', [5, 15, 21, 55, 92, 105])
        graph_data = graph.render_data_uri()

        return render_template('graphing.html', graph_data=graph_data)
    except Exception as e:
        return str(e)


@app.route('/pygalmap/')
def pygalmap():
    try:
        supra = pygal.maps.world.SupranationalWorld()
        supra.add('Asia', [('asia', 1)])
        supra.add('Europe', [('europe', 1)])
        supra.add('Africa', [('africa', 1)])
        supra.add('North america', [('north_america', 1)])
        supra.add('South america', [('south_america', 1)])
        supra.add('Oceania', [('oceania', 1)])
        supra.add('Antartica', [('antartica', 1)])
        supra_data = supra.render_data_uri()

        return render_template('pygalmaps.html', supra_data=supra_data)
    except Exception as e:
        return str(e)


@app.route('/upload/', methods=['POST', 'GET'])
def upload():
    try:
        if request.method == 'POST':
            file = request.files['photo']
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLAOD_FOLDER'], filename))
                flash("Uploaded file to {}".format(
                    app.config['UPLAOD_FOLDER']))
            return redirect(url_for('dashboard'))
        return render_template('uploading.html')
    except Exception as e:
        return str(e)


@app.route('/media/<filename>/')
def media(filename):
    return send_from_directory(app.config['UPLAOD_FOLDER'], filename)


if __name__ == '__main__':

    app.run()
