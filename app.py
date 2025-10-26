from flask import Flask, request, render_template, redirect, url_for
import sqlite3
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread
from wechatpy import WeChatClient

print("Starting application...")
app = Flask(__name__)
app.secret_key = 'your_secret_key'

wechat_client = WeChatClient('your_appid', 'your_appsecret')

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
        remaining_venue_sessions INTEGER,
        openid TEXT
    )
    ''')
    conn.commit()
    conn.close()

def send_wechat_reminder(openid, message):
    wechat_client.message.send_text(openid, message)

def check_renewal_reminders():
    conn = get_db_connection()
    today = datetime.now()
    week_later = today + timedelta(days=7)
    clients = conn.execute("SELECT name, renewal_date, openid FROM clients WHERE renewal_date <= ?", (week_later.strftime('%Y-%m-%d'),)).fetchall()
    conn.close()
    for client in clients:
        renewal_date = datetime.strptime(client['renewal_date'], '%Y-%m-%d')
        if today <= renewal_date <= week_later:
            send_wechat_reminder(client['openid'], f"客户 {client['name']} 续课提醒：{client['renewal_date']}")

@app.route('/')
def index():
    conn = get_db_connection()
    clients = conn.execute('SELECT * FROM clients').fetchall()
    conn.close()
    expected_income = sum(c['renewal_amount'] for c in clients if c['renewal_date'] and datetime.strptime(c['renewal_date'], '%Y-%m-%d').strftime("%Y-%m") == datetime.now().strftime("%Y-%m"))
    expected_expense = sum(c['remaining_venue_sessions'] * 50.0 for c in clients)
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
        openid = request.form.get('openid', '')  # 可选字段
        conn = get_db_connection()
        conn.execute('INSERT INTO clients (name, contact, renewal_date, remaining_sessions, renewal_amount, remaining_venue_sessions, openid) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (name, contact, renewal_date, remaining_sessions, renewal_amount, remaining_venue_sessions, openid))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/check_reminders')
def check_reminders():
    check_renewal_reminders()
    return "续课提醒已检查！<a href='/'>返回</a>"

if __name__ == '__main__':
    try:
        print("Starting application...")
        init_db()
        scheduler = BackgroundScheduler()
        scheduler.add_job(check_renewal_reminders, 'interval', days=1)
        scheduler_thread = Thread(target=scheduler.start)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        print("Scheduler started in thread...")
        import os
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"Error occurred: {e}")