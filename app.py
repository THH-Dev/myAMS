from flask import Flask, render_template, redirect, url_for, session, request, logging, flash
from passlib.hash import sha256_crypt
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators

from myLib.myDatabase import MyDatabase
from myLib.myLib import log

app = Flask(__name__)
myDatabase = MyDatabase()

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Index
@app.route('/')
def index():
    return render_template('home.html')

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Get articles
    msg = 'No Articles Found'
    return render_template('dashboard.html', msg=msg)


# About
@app.route('/about')
def about():
    return render_template('about.html')

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        log.error(username)
        log.error(password_candidate)
        
        # Query database to get password
        myDatabase.connect()
        password = myDatabase.getPasswordLogin(username)
        myDatabase.disconnect()

        # Compare password to login
        if password is not None:
            if sha256_crypt.verify(password_candidate, password[0]):
                # Passed
                session['logged_in'] = True
                session['username'] = username
                log.info(f'user {username} login success')
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login, check password again!'
                log.warning(f'user {username} cannot login by wrong password')
                return render_template('login.html', error=error)

        else:
            log.warning(f'user {username} cannot login by no account')
            error = 'Username not found!'
            return render_template('login.html', error=error)

    return render_template('login.html')



if __name__ == '__main__':
    app.secret_key='tanhungha@10'
    app.run(debug=True)