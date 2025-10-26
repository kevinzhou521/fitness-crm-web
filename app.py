from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread

print("Starting application...")
app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('fitness_clients.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        renewal_date TEXT,
        remaining_sessions INTEGER,
        renewal_amount REAL,
        remaining_venue_sessions INTEGER
    )
    ''')
    conn.commit()
    conn.close()

def send_reminder_email(client_name, renewal_date, recipient_email):
    sender_email = "your_email@gmail.com"  # 替换为你的 Gmail 地址
    sender_password = "your_app_password"  # 替换为 Gmail 应用专用密码
    msg = MIMEText(f"提醒：客户 {client_name} 的续课时间为 {renewal_date}，请联系！")
    msg['Subject'] = f"续课提醒: {client_name}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('1341605461@qq.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

def check_renewal_reminders():
    conn = get_db_connection()
    today = datetime.now()
    week_later = today + timedelta(days=7)
    clients = conn.execute("SELECT name, renewal_date FROM clients WHERE renewal_date <= ?", (week_later.strftime('%Y-%m-%d'),)).fetchall()
    conn.close()
    for client in clients:
        renewal_date = datetime.strptime(client['renewal_date'], '%Y-%m-%d')
        if today <= renewal_date <= week_later:
            send_reminder_email(client['name'], client['renewal_date'], "your_email@gmail.com")  # 替换为你的接收邮箱

@app.route('/')
def index():
    conn = get_db_connection()
    clients = conn.execute('SELECT * FROM clients').fetchall()
    conn.close()
    df = pd.read_sql_query("SELECT * FROM clients", sqlite3.connect('fitness_clients.db'))
    current_month = datetime.now().strftime("%Y-%m")
    monthly_renewals = df[pd.to_datetime(df['renewal_date']).dt.strftime("%Y-%m") == current_month]
    expected_income = monthly_renewals['renewal_amount'].sum()
    venue_cost_per_session = 50.0
    expected_expense = df['remaining_venue_sessions'].sum() * venue_cost_per_session
    return render_template('index.html', clients=clients, income=expected_income, expense=expected_expense)

@app.route('/add', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        renewal_date = request.form['renewal_date']
        remaining_sessions = int(request.form['remaining_sessions'])
        renewal_amount = float(request.form['renewal_amount'])
        remaining_venue_sessions = int(request.form['remaining_venue_sessions'])
        conn = get_db_connection()
        conn.execute('INSERT INTO clients (name, contact, renewal_date, remaining_sessions, renewal_amount, remaining_venue_sessions) VALUES (?, ?, ?, ?, ?, ?)',
                     (name, contact, renewal_date, remaining_sessions, renewal_amount, remaining_venue_sessions))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_client(id):
    conn = get_db_connection()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        renewal_date = request.form['renewal_date']
        remaining_sessions = int(request.form['remaining_sessions'])
        renewal_amount = float(request.form['renewal_amount'])
        remaining_venue_sessions = int(request.form['remaining_venue_sessions'])
        conn.execute('UPDATE clients SET name = ?, contact = ?, renewal_date = ?, remaining_sessions = ?, renewal_amount = ?, remaining_venue_sessions = ? WHERE id = ?',
                     (name, contact, renewal_date, remaining_sessions, renewal_amount, remaining_venue_sessions, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    conn.close()
    return render_template('update.html', client=client)

@app.route('/delete/<int:id>')
def delete_client(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM clients WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/check_reminders')
def check_reminders():
    check_renewal_reminders()
    return "续课提醒已检查！<a href='/'>返回</a>"

if __name__ == '__main__':
    try:
        print("Starting application...")
        init_db()
        print("Database initialized...")
        scheduler = BackgroundScheduler()
        print("Scheduler created...")
        scheduler.add_job(check_renewal_reminders, 'interval', days=1)
        print("Job added...")
        scheduler_thread = Thread(target=scheduler.start)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        print("Scheduler started in thread...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Error occurred: {e}")