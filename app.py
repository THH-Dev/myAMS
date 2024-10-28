from flask import Flask, render_template, redirect, url_for, session, request, logging, flash, jsonify, send_file
from passlib.hash import sha256_crypt
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
import json
import pandas as pd
import io
import os
from flask import __version__ as flask_version
from packaging import version

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
        username = request.form['username']
        password_candidate = request.form['password']

        log.error(username)
        log.error(password_candidate)
        
        if myDatabase.ensure_connection():
            password = myDatabase.getPasswordLogin(username)
            
            if password is not None:
                if sha256_crypt.verify(password_candidate, password[0]):
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
        else:
            error = 'Database connection failed'
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
        if myDatabase.ensure_connection():
            cmd = f'INSERT INTO "assetDB"."accounts" (user_id, email, account, password) VALUES (\'{name}\', \'{email}\', \'{username}\', \'{password}\');'
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
    sql_query = None  # Thêm biến để lưu lệnh SQL

    if request.method == 'POST':
        sql_query = request.form['sql_query']
        session['last_sql_query'] = sql_query  # Lưu lệnh SQL vào session
        
        if myDatabase.ensure_connection():
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

    # Lấy lệnh SQL cuối cùng từ session
    last_sql_query = session.get('last_sql_query', '')  # Nếu không có thì mặc định là rỗng

    return render_template('query.html', result=result, columns=columns, error=error, last_sql_query=last_sql_query)


# Query and Add Rows
@app.route('/manage_table', methods=['GET', 'POST'])
@is_logged_in
def manage_table():
    result = None
    columns = None
    error = None
    queried_table = request.args.get('table_name')  # Lấy tên bảng từ tham số URL
    table_names = myDatabase.get_table_names()
    log.info(f"queried_table:{queried_table}")
    if request.method == 'POST' or queried_table:
        if request.method == 'POST':
            queried_table = request.form['table_name']
        
        if myDatabase.ensure_connection():
            cmd = f'SELECT * FROM "{myDatabase.schema_name}"."{queried_table}";'
            columns, result = myDatabase.query2(cmd)
            
            if isinstance(columns, str):  # Nếu có lỗi
                error = columns
                result = None
                queried_table = None
            myDatabase.disconnect()
    
    return render_template('manage_table.html', result=result, columns=columns, error=error, table_names=table_names, queried_table=queried_table)

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
    
    if myDatabase.ensure_connection():
        try:
            result, _ = myDatabase.query2(cmd)
            
            if isinstance(result, str) and "An error occurred" in result:
                flash('Có lỗi xảy ra khi thêm dữ liệu: ' + result, 'danger')
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
    
    return redirect(url_for('manage_table', table_name=table_name))

# Xóa hàng từ bảng
@app.route('/delete_row', methods=['POST'])
@is_logged_in
def delete_row():
    table_name = request.form['table_name']
    primary_key_column = request.form['primary_key_column']
    primary_key_value = request.form['primary_key_value']

    cmd = f'DELETE FROM "{myDatabase.schema_name}"."{table_name}" WHERE "{primary_key_column}" = \'{primary_key_value}\';'
    
    if myDatabase.ensure_connection():
        try:
            result, _ = myDatabase.query2(cmd)
            
            if isinstance(result, str) and "An error occurred" in result:
                flash('Có lỗi xảy ra khi xóa dữ liệu: ' + result, 'danger')
            else:
                flash('Xóa hàng thành công', 'success')
        finally:
            myDatabase.disconnect()
    
    return redirect(url_for('manage_table', table_name=table_name))

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
    
    if myDatabase.ensure_connection():
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
    
    if myDatabase.ensure_connection():
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
        finally:
            myDatabase.disconnect()
    
    return redirect(url_for('manage_table', table_name=table_name))

# Tải xuống file Excel
@app.route('/download_excel/<table_name>')
@is_logged_in
def download_excel(table_name):
    if myDatabase.ensure_connection():
        try:
            cmd = f'SELECT * FROM "{myDatabase.schema_name}"."{table_name}";'
            columns, result = myDatabase.query2(cmd)
            
            df = pd.DataFrame(result, columns=columns)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            
            output.seek(0)
            
            if version.parse(flask_version) >= version.parse('2.0'):
                return send_file(
                    output,
                    as_attachment=True,
                    download_name=f"{table_name}.xlsx",
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else:
                return send_file(
                    output,
                    as_attachment=True,
                    attachment_filename=f"{table_name}.xlsx",
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
        finally:
            myDatabase.disconnect()

# Import file Excel
@app.route('/import_excel', methods=['POST'])
@is_logged_in
def import_excel():
    if 'file' not in request.files:
        flash('Không có file nào được chọn', 'danger')
        return redirect(url_for('manage_table'))
    
    file = request.files['file']
    table_name = request.form['table_name']
    
    if file.filename == '':
        flash('Không có file nào được chọn', 'danger')
        return redirect(url_for('manage_table'))
    
    if file and file.filename.endswith('.xlsx'):
        try:
            df = pd.read_excel(file)
            log.info(f'Importing {len(df)} rows into {table_name}')  # Log số lượng hàng sẽ được import
            
            if myDatabase.ensure_connection():
                # Xóa dữ liệu cũ trong bảng
                #cmd = f'DELETE FROM "{myDatabase.schema_name}"."{table_name}";'
                #result, _ = myDatabase.query2(cmd)
                
                #if isinstance(result, str) and "An error occurred" in result:
                #    flash('Có lỗi xảy ra khi xóa dữ liệu cũ: ' + result, 'danger')
                #    return redirect(url_for('manage_table'))
                
                # Import dữ liệu mới
                for _, row in df.iterrows():
                    columns = ', '.join([f'"{col}"' for col in df.columns])
                    values = ', '.join([f"'{val}'" for val in row])
                    cmd = f'INSERT INTO "{myDatabase.schema_name}"."{table_name}" ({columns}) VALUES ({values});'
                    result, _ = myDatabase.query2(cmd)
                    
                    if isinstance(result, str) and "An error occurred" in result:
                        flash('Có lỗi xảy ra khi thêm dữ liệu: ' + result, 'danger')
                        return redirect(url_for('manage_table'))
                
                flash('Import dữ liệu thành công', 'success')
                log.info(f'Successfully imported {len(df)} rows into {table_name}')  # Log thành công
        except Exception as e:
            flash(f'Có lỗi xảy ra khi import dữ liệu: {str(e)}', 'danger')
            log.error(f'Error importing data: {str(e)}')  # Log lỗi
        finally:
            myDatabase.disconnect()
        
        return redirect(url_for('manage_table', table_name=table_name))  # Chuyển hướng về manage_table
    else:
        flash('Chỉ chấp nhận file Excel (.xlsx)', 'danger')
        return redirect(url_for('manage_table'))

# Query Order Detail
@app.route('/query_orderdetail', methods=['GET', 'POST'])
@is_logged_in
def query_orderdetail():
    result = None
    error = None
    user_id = None
    columns = []  # Khởi tạo `columns` là danh sách rỗng
    user_id = request.form.get('user_id')
    #prd_id = request.form.get('prd_id')
    prd_id= request.form.get('prd_id')  # Lấy tên bảng từ tham số URL
 
    log.info(f"prd_id:{prd_id}")
    prd_id_cell_value = myDatabase.get_value_cell_column('prd_id','products')
    log.info(f"prd_id:{user_id}")
    user_id_cell_value = myDatabase.get_value_cell_column('user_id','users')

    if request.method == 'POST':
        #user_id = request.form['user_id']
        #prd_id = request.form.get('prd_id')

        if myDatabase.ensure_connection():
            if user_id:  # Nếu có user_id
                cmd = f'''
                    SELECT p.ord_detail_id AS "Order ID", 
                           p.prd_id AS "Mã sản phẩm",
                           p.prd_qty AS "Số lượng", 
                           p2.prd_name AS "Tên sản phẩm",
                           c.name AS "Tên danh mục", 
                           u.full_name AS "Họ Tên"
                    FROM "assetDB"."orderdetail" p
                    INNER JOIN "assetDB"."products" p2 ON p.prd_id = p2.prd_id
                    INNER JOIN "assetDB"."users" u ON p.user_id = u.user_id
                    INNER JOIN "assetDB"."categories" c ON c.cat_id = p2.cat_id
                    WHERE u.user_id = '{user_id}';
                '''
                try:
                    columns, result = myDatabase.query2(cmd)
                    if isinstance(columns, str) and "An error occurred" in columns:
                        error = columns
                        result = None
                    if result :
                        result =result
                    else:
                        error ="Không có dữ liệu"   
                except Exception as e:
                    error = str(e)
                finally:
                    myDatabase.disconnect()
            elif prd_id:  # Nếu có prd_id
                cmd = f'''
                    SELECT p.ord_detail_id AS "Order ID", 
                           p.prd_id AS "Mã sản phẩm",
                           p.prd_qty AS "Số lượng", 
                           p2.prd_name AS "Tên sản phẩm",
                           c.name AS "Tên danh mục", 
                           u.full_name AS "Họ Tên"
                    FROM "assetDB"."orderdetail" p
                    INNER JOIN "assetDB"."products" p2 ON p.prd_id = p2.prd_id
                    INNER JOIN "assetDB"."users" u ON p.user_id = u.user_id
                    INNER JOIN "assetDB"."categories" c ON c.cat_id = p2.cat_id
                    WHERE p.prd_id = '{prd_id}';
                '''
                try:
                    columns, result = myDatabase.query2(cmd)
                    if isinstance(columns, str) and "An error occurred" in columns:
                        error = columns
                        result = None
                    if result :
                        result =result
                    else:
                        error ="Không có dữ liệu"   
                except Exception as e:
                    error = str(e)
                finally:
                    myDatabase.disconnect()
    log.info(f'Error: {error}, Result: {result} ')
    if columns:
        return render_template('query_orderdetail.html', result=result, columns=columns, error=error, user_id=user_id, prd_ids = prd_id_cell_value, user_ids =user_id_cell_value )
    else:
        return render_template('query_orderdetail.html', result=result, columns=[], error=error, user_id=user_id , prd_ids = prd_id_cell_value,user_ids =user_id_cell_value)


@app.template_filter('enumerate')
def enumerate_filter(iterable, start=0):
    return enumerate(iterable, start)

if __name__ == '__main__':
    app.secret_key='tanhungha@10'
    app.run(host='192.168.100.127',debug=True)

