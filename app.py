from flask import Flask, render_template, request, redirect, url_for, flash
import json, os, qrcode
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'vaulty_secret'

# Paths
DATA_FILE = os.path.join('data', 'users.json')

# ---------------------- Helper Functions ----------------------

def load_users():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def generate_qr(username):
    img = qrcode.make(username)
    qr_folder = os.path.join('static', 'qr')
    os.makedirs(qr_folder, exist_ok=True)
    img.save(os.path.join(qr_folder, f"{username}.png"))

def load_history():
    if not os.path.exists('data/history.json'):
        return {}
    with open('data/history.json', 'r') as f:
        return json.load(f)

def save_history(history):
    with open('data/history.json', 'w') as f:
        json.dump(history, f, indent=4)

def calculate_monthly_spending(history_list, username):
    current_month = datetime.now().strftime("%Y-%m")
    total_spent = 0
    for entry in history_list:
        if entry.startswith("You sent"):
            parts = entry.split("₹")
            if len(parts) > 1:
                try:
                    amount = int(parts[1].split(" ")[0])
                    total_spent += amount
                except:
                    continue
    return total_spent

# ---------------------- Routes ----------------------

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        phone = request.form['phone']
        balance = float(request.form['balance'])

        users = load_users()
        for user in users:
            if user['username'] == username:
                flash('Username already exists!')
                return redirect(url_for('register'))

        new_user = {
            'username': username,
            'password': password,
            'phone': phone,
            'balance': balance,
            'history': []
        }
        users.append(new_user)
        save_users(users)
        generate_qr(username)
        flash('Registration successful. You can now login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()

        for user in users:
            if user['username'] == username and user['password'] == password:
                return redirect(url_for('dashboard', username=username))

        flash("Invalid credentials. Try again.")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard/<username>')
def dashboard(username):
    users = load_users()
    current_user = next((u for u in users if u['username'] == username), None)
    if not current_user:
        return redirect(url_for('login'))

    contacts = [u for u in users if u['username'] != username]
    total_spent = calculate_monthly_spending(current_user.get('history', []), username)
    show_alert = total_spent > 1000

    return render_template('dashboard.html', user=current_user, contacts=contacts, total_spent=total_spent, show_alert=show_alert)

@app.route('/send/<username>', methods=['POST'])
def send_money(username):
    to_user = request.form['to_user']
    amount = int(request.form['amount'])

    users = load_users()

    sender = None
    receiver = None

    for user in users:
        if user['username'] == username:
            sender = user
        if user['username'] == to_user:
            receiver = user

    if sender and receiver and sender['balance'] >= amount:
        sender['balance'] -= amount
        receiver['balance'] += amount

        sender.setdefault('history', []).append(f"You sent ₹{amount} to {to_user}")
        receiver.setdefault('history', []).append(f"You received ₹{amount} from {username}")

        save_users(users)
        flash(f"₹{amount} sent to {to_user}!")
    else:
        flash("Transaction failed. Check username or balance.")

    return redirect(url_for('dashboard', username=username))

@app.route('/spendpage/<username>')
def spendpage(username):
    users = load_users()
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        return redirect(url_for('login'))
    return render_template('spend.html', user=user)

@app.route('/history/<username>')
def history(username):
    users = load_users()
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        return redirect(url_for('login'))

    total_spent = calculate_monthly_spending(user.get('history', []), username)
    show_alert = total_spent > 1000

    return render_template('history.html', user=user, total_spent=total_spent, show_alert=show_alert)

# ---------------------- Main ----------------------

if __name__ == '__main__':
    app.run(debug=True)
