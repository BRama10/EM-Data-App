from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from datetime import datetime
import os
import pymysql

app = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'your secret key'

# Enter your database connection details below
#app.config['MYSQL_HOST'] = '35.245.16.5'
#app.config['MYSQL_USER'] = 'root'
#app.config['MYSQL_PASSWORD'] = 'BADED2023'
#app.config['MYSQL_DB'] = 'pythonlogin'

# Intialize MySQL
#mysql = MySQL(app)
db_user = os.environ.get('CLOUD_SQL_USERNAME')
db_password = os.environ.get('CLOUD_SQL_PASSWORD')
db_name = os.environ.get('CLOUD_SQL_DATABASE_NAME')
db_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')

def open_connection():
    unix_socket = '/cloudsql/{}'.format(db_connection_name)
    try:
        if os.environ.get('GAE_ENV') == 'standard':
            con = pymysql.connect(user=db_user, password=db_password, unix_socket=unix_socket, db=db_name, cursorclass=pymysql.cursors.DictCursor)
    except pymysql.MYSQLError as e:
        print(e)
    conn = con
    cursor = conn.cursor()
    return conn, cursor

@app.route('/')
def start():
    return redirect(url_for('home'))
        


@app.route('/login/', methods=['GET', 'POST'])
def login():
    msg = ''

    conn, cursor = open_connection()
    
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()

        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['account_type'] = account['account_type']
            session['name'] = account['name']

            return redirect(url_for('home'))
        else:
            msg = 'Incorrect username/password!'
        
    conn.close()
    return render_template('login.html', msg='')


@app.route('/logout/')
def logout():
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   session.pop('name', None)
   session.pop('account_type', None)
   return redirect(url_for('login'))


@app.route('/register/', methods=['GET', 'POST'])
def register():
    msg = ''

    conn, cursor = open_connection()
    
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        account_type= request.form['account_type']
        name = request.form['name']
        
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cursor.execute("INSERT INTO accounts VALUES (NULL, '{}', '{}', '{}', '{}', '{}')".format(username, password, email,account_type, name))
            conn.commit()
            msg = 'You have successfully registered! Now log in!'

            conn.close()
            return render_template('login.html', msg=msg)

    conn.close()
    return render_template('register.html', msg=msg)


@app.route('/home/')
def home():
    if 'loggedin' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))


@app.route('/profile/')
def profile():
    conn, cursor = open_connection()
    
    if 'loggedin' in session:
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()

        conn.close()
        return render_template('profile.html', account=account)

    conn.close()
    return redirect(url_for('login'))

@app.route('/userless/receivedata/', methods=['POST'])
def receive():
    conn, cursor = open_connection()
    
    response = request.get_json()
    print(response)
    
    file = open('col_names.txt', 'r')
    lines = file.readlines()
    x, contact_cols, data_cols = 0, [], []
    file.close()
    for d in range(len(lines)):
        lines[d] = lines[d].strip()
    while lines[x] != '--':
        contact_cols.append(lines[x])
        x+=1
    x+=1
    while x < len(lines):
        data_cols.append(lines[x])
        x+=1

    print(contact_cols)
    print(data_cols)

    contact_values =tuple([response.get(x)[0] for x in contact_cols])
    #contact_values[0] = contact_values[0].replace(':', '-')
    #contact_values = tuple(contact_values)
    data_values =list([response.get(x)[0] for x in data_cols])

    print(contact_values)
    


    if(data_values[3] == '' or data_values[3] == ' '):
        data_values[3] = '0'
    if(data_values[4] == '' or data_values[4] == ' '):
        data_values[4] = '0'

    print(data_values)
    data_values = tuple(data_values)
    
    cursor.execute("INSERT INTO `pythonlogin`.`contact` (`timestamp`, `language`, `name`, `unit_number`, `phone`, `email`) VALUES ('{}', '{}', '{}', '{}', '{}', '{}')".format(*contact_values))
    conn.commit()
    cursor.execute("INSERT INTO `pythonlogin`.`data` (`num_members`, `problem_types`, `problem_locations`, `winter_temp`, `summer_temp`, `bulb_type`, `lights`, `tv`, `fan`, `dishwasher`, `clothes`, `heat_setting`, `water_tap`, `shower`) VALUES ('{}', '{}', '{}', {}, {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(*data_values))
    conn.commit()

    # datetime object containing current date and time
    now = datetime.now()

    # dd/mm/YY H:M:S
    dt_string = now.strftime("%m/%d/%Y %H:%M:%S")

    cursor.execute("INSERT INTO `pythonlogin`.`app_log` (`name`, `time`, `action`) VALUES ('{}', '{}', '{}')".format('Server', dt_string, 'Form Submitted'))
    conn.commit()

    conn.close()
    return 'STATUS : SUCCESS'

@app.route('/results/')
def results():
    file = open('col_names.txt', 'r')
    lines = file.readlines()
    x, contact_cols, data_cols = 0, [], []
    file.close()
    for d in range(len(lines)):
        lines[d] = lines[d].strip()
    while lines[x] != '--':
        contact_cols.append(lines[x])
        x+=1
    x+=1
    while x < len(lines):
        data_cols.append(lines[x])
        x+=1

    conn, cursor = open_connection()
    cursor.execute("SELECT * FROM contact")
    contact = cursor.fetchall()
    cursor.execute("SELECT * FROM data")
    data = cursor.fetchall()
    contact = [list(x.values()) for x in contact]
    data = [list(x.values())[1:] for x in data]
    conn.close()
    print(contact)
    return render_template('data.html', contact = contact, data=data, contact_cols=contact_cols, data_cols=data_cols)

@app.route('/numbers/<z>')
def numbers(z):
    conn, cursor = open_connection()
    
    if 'loggedin' in session:
        print(type(z))
        z = int(z)
        if z > 1:
            conn.close()
            return 'PAGE IN PROGRESS ^_^'
    
        cursor.execute("SELECT * FROM `workday_numbers` WHERE `workday_numbers`.`id` = %s", (1,))
        vals=dict(cursor.fetchone())
        print(list(vals.values()))
        conn.close()
        return render_template('numbers.html', x = list(vals.values()))
    conn.close()
    return redirect(url_for('login'))
        


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8000', debug=True)
