from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Ensure the static/tickets directory exists
if not os.path.exists('static/tickets'):
    os.makedirs('static/tickets')

def init_db():
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS contributions (id INTEGER PRIMARY KEY, name TEXT, amount REAL, month TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY, image_path TEXT, status TEXT, month TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS winnings (id INTEGER PRIMARY KEY, amount REAL, month TEXT)''')
        # Add default admin user
        c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if not c.fetchone():
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', generate_password_hash('password')))
        conn.commit()

@app.route('/')
def homepage():
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('SELECT name, SUM(amount) as total FROM contributions GROUP BY name')
        contributors = c.fetchall()
        total_pool = sum([row[1] for row in contributors]) if contributors else 0
        contributors = [(row[0], row[1], (row[1] / total_pool) * 100 if total_pool else 0) for row in contributors]
    return render_template('index.html', contributors=contributors)

@app.route('/tickets')
def tickets():
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM tickets')
        tickets = c.fetchall()
    return render_template('tickets.html', tickets=tickets)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = c.fetchone()
            if user and check_password_hash(user[2], password):
                session['admin'] = True
                return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        if 'upload_ticket' in request.form:
            ticket_image = request.files['ticket_image']
            month = request.form['month']
            image_path = f'static/tickets/{ticket_image.filename}'
            ticket_image.save(image_path)
            with sqlite3.connect('database.db') as conn:
                c = conn.cursor()
                c.execute('INSERT INTO tickets (image_path, status, month) VALUES (?, ?, ?)', (image_path, 'Pending', month))
                conn.commit()
        elif 'update_status' in request.form:
            ticket_id = request.form['ticket_id']
            status = request.form['status']
            with sqlite3.connect('database.db') as conn:
                c = conn.cursor()
                c.execute('UPDATE tickets SET status = ? WHERE id = ?', (status, ticket_id))
                conn.commit()
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM tickets')
        tickets = c.fetchall()
    return render_template('admin.html', tickets=tickets)

@app.route('/winnings')
def winnings():
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM winnings ORDER BY month DESC')
        monthly_winnings = c.fetchall()
    return render_template('winnings.html', monthly_winnings=monthly_winnings)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

import os

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
