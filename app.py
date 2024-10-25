from flask import Flask, render_template, redirect, url_for, session, request, logging, flash, jsonify
from passlib.hash import sha256_crypt
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
import json

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

# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.hash(str(form.password.data))  # Mã hóa mật khẩu khi đăng ký

        # Create cursor
        myDatabase.connect()
       
        cmd = f'INSERT INTO "assetDB"."accounts" (user_id, email, account, password) VALUES (\'{name}\', \'{email}\', \'{username}\', \'{password}\');'
        # Execute query
        result = myDatabase.query2(cmd)
        log.error(result)
        if "An error occurred" in result:
            log.error("Có lỗi xảy ra khi thực hiện câu lệnh SQL.")
            
            #return render_template('register.html', error=error)
            flash('Có lỗi xảy ra khi thực hiện câu lệnh SQL', 'danger')
            flash(result)
        else:
            log.info("Câu lệnh SQL thực hiện thành công.")
            flash('You are now registered and can log in', 'success')
            return redirect(url_for('login'))
        # Close connection
        myDatabase.disconnect()
  
    return render_template('register.html', form=form)

# Query Database
@app.route('/query', methods=['GET', 'POST'])
@is_logged_in
def query_database():
    result = None
    columns = None
    error = None
    if request.method == 'POST':
        sql_query = request.form['sql_query']
        
        myDatabase.connect()
        try:
            columns, result = myDatabase.query2(sql_query)
            
            if isinstance(columns, str) and "An error occurred" in columns:
                error = columns
                columns = None
                result = None
            elif not columns:  # Nếu không có columns (ví dụ: INSERT, UPDATE, DELETE)
                result = "Truy vấn thực hiện thành công"
                columns = None
        except Exception as e:
            error = str(e)
        finally:
            myDatabase.disconnect()

    return render_template('query.html', result=result, columns=columns, error=error)


# Query and Add Rows
@app.route('/manage_table', methods=['GET', 'POST'])
@is_logged_in
def manage_table():
    result = None
    columns = None
    error = None
    if request.method == 'POST':
        table_name = request.form['table_name']
        cmd = f'SELECT * FROM "{myDatabase.schema_name}"."{table_name}";'
        
        myDatabase.connect()
        result = myDatabase.query2(cmd)
        myDatabase.disconnect()
        
        if isinstance(result[0], str):  # Nếu có lỗi
            error = result[0]
            result = None
        else:
            columns, result = result  # Tách tên cột và dữ liệu

    return render_template('manage_table.html', result=result, columns=columns, error=error)

# Thêm hàng vào bảng
@app.route('/add_row', methods=['POST'])
@is_logged_in
def add_row():
    table_name = request.form['table_name']
    columns = request.form.getlist('columns')
    values = request.form.getlist('values')

    # Tạo câu lệnh SQL để thêm hàng
    columns_str = ', '.join([f'"{col}"' for col in columns])
    values_placeholder = ', '.join([f"'{val}'" for val in values])
    
    cmd = f'INSERT INTO "{myDatabase.schema_name}"."{table_name}" ({columns_str}) VALUES ({values_placeholder}) RETURNING uid;'
    
    myDatabase.connect()
    try:
        result, _ = myDatabase.query2(cmd)
        
        if isinstance(result, str) and "An error occurred" in result:
            flash('Có lỗi xảy ra khi thêm dữ liệu: ' + result, 'danger')
            return redirect(url_for('manage_table'))
        else:
            # Kiểm tra xem result có phải là tuple không
            if isinstance(result, tuple) and len(result) > 0:
                flash('Thêm hàng thành công với UID: ' + str(result[0]), 'success')
            else:
                flash('Thêm hàng thành công', 'success')
            
            # Query lại bảng sau khi thêm hàng thành công
            cmd = f'SELECT * FROM "{myDatabase.schema_name}"."{table_name}";'
            columns, result = myDatabase.query2(cmd)
    finally:
        myDatabase.disconnect()
    
    return render_template('manage_table.html', result=result, columns=columns, table_name=table_name)

# Xóa hàng từ bảng
@app.route('/delete_row', methods=['POST'])
@is_logged_in
def delete_row():
    table_name = request.form['table_name']
    primary_key_column = request.form['primary_key_column']
    primary_key_value = request.form['primary_key_value']

    cmd = f'DELETE FROM "{myDatabase.schema_name}"."{table_name}" WHERE "{primary_key_column}" = \'{primary_key_value}\';'
    
    myDatabase.connect()
    try:
        result, _ = myDatabase.query2(cmd)
        
        if isinstance(result, str) and "An error occurred" in result:
            flash('Có lỗi xảy ra khi xóa dữ liệu: ' + result, 'danger')
        else:
            flash('Xóa hàng thành công', 'success')
        
        # Query lại bảng sau khi xóa hàng
        cmd = f'SELECT * FROM "{myDatabase.schema_name}"."{table_name}";'
        columns, result = myDatabase.query2(cmd)
    finally:
        myDatabase.disconnect()
    
    return render_template('manage_table.html', result=result, columns=columns, table_name=table_name)

# Cập nhật giá trị ô
@app.route('/update_cell', methods=['POST'])
@is_logged_in
def update_cell():
    table_name = request.form['table_name']
    primary_key_column = request.form['primary_key_column']
    primary_key_value = request.form['primary_key_value']
    column_name = request.form['column_name']
    new_value = request.form['new_value']

    cmd = f'UPDATE "{myDatabase.schema_name}"."{table_name}" SET "{column_name}" = \'{new_value}\' WHERE "{primary_key_column}" = \'{primary_key_value}\';'
    
    myDatabase.connect()
    try:
        result, _ = myDatabase.query2(cmd)
        
        if isinstance(result, str) and "An error occurred" in result:
            flash('Có lỗi xảy ra khi cập nhật dữ liệu: ' + result, 'danger')
        else:
            flash('Cập nhật dữ liệu thành công', 'success')

        # Query lại bảng sau khi cập nhật
        cmd = f'SELECT * FROM "{myDatabase.schema_name}"."{table_name}";'
        columns, result = myDatabase.query2(cmd)
    finally:
        myDatabase.disconnect()

    return render_template('manage_table.html', result=result, columns=columns, table_name=table_name)

# Cập nhật nhiều ô cùng lúc
@app.route('/update_cells', methods=['POST'])
@is_logged_in
def update_cells():
    table_name = request.form['table_name']
    update_row = int(request.form['update_row'])
    
    myDatabase.connect()
    try:
        # Lấy tên các cột
        cmd = f'SELECT * FROM "{myDatabase.schema_name}"."{table_name}" LIMIT 0;'
        columns, _ = myDatabase.query2(cmd)
        
        # Tạo câu lệnh UPDATE
        set_clauses = []
        for i, column in enumerate(columns):
            new_value = request.form.get(f'values-{update_row}-{i}')
            set_clauses.append(f'"{column}" = \'{new_value}\'')
        
        set_clause = ', '.join(set_clauses)
        primary_key_column = columns[0]
        primary_key_value = request.form.get(f'values-{update_row}-0')
        
        cmd = f'UPDATE "{myDatabase.schema_name}"."{table_name}" SET {set_clause} WHERE "{primary_key_column}" = \'{primary_key_value}\';'
        
        result, _ = myDatabase.query2(cmd)
        
        if isinstance(result, str) and "An error occurred" in result:
            flash('Có lỗi xảy ra khi cập nhật dữ liệu: ' + result, 'danger')
        else:
            flash('Cập nhật dữ liệu thành công', 'success')
        
        # Query lại bảng sau khi cập nhật
        cmd = f'SELECT * FROM "{myDatabase.schema_name}"."{table_name}";'
        columns, result = myDatabase.query2(cmd)
    finally:
        myDatabase.disconnect()
    
    return render_template('manage_table.html', result=result, columns=columns, table_name=table_name)

@app.template_filter('enumerate')
def enumerate_filter(iterable, start=0):
    return enumerate(iterable, start)

if __name__ == '__main__':
    app.secret_key='tanhungha@10'
    app.run(host='192.168.100.127',debug=True)
