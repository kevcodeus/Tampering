import base64
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'super_secret_lab_key'

# --- CONFIGURATION (Replace these!) ---
TELEGRAM_BOT_TOKEN = '8511321785:AAESpReOXlD4_CssZJ_F--g9J80Z1tohL6k'
TELEGRAM_CHAT_ID = '1836126231'

# --- MOCK DATA ---
users = {"admin": "password"}

products = [
    {"id": 1, "name": "MacBook Pro M3", "price": 2500, "image": "https://www.digitaltrends.com/wp-content/uploads/2023/02/macbook-pro-14-m2-max.jpg?p=1"},
    {"id": 2, "name": "iPhone 15 Pro", "price": 1200, "image": "https://tse2.mm.bing.net/th/id/OIP.PxLh2EpXxfVPfDnnMz6WnwHaEK?rs=1&pid=ImgDetMain&o=7&rm=3"},
    {"id": 3, "name": "Gaming PC", "price": 3500, "image": "https://dlcdnrog.asus.com/rog/media/1644549597584.webp"}
]

# --- HELPER: SEND TO TELEGRAM ---
def send_telegram_alert(product_name, price_paid, user):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set.")
        return

    message = (
        f"🚨 **New Order Received!** 🚨\n"
        f"User: {user}\n"
        f"Product: {product_name}\n"
        f"Payment Processed: ${price_paid}"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

# --- ROUTES ---

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('shop.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['user'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials! Try admin/password123')
    return render_template('login.html')

@app.route('/prepare_order/<int:product_id>')
def prepare_order(product_id):
    """
    This route simulates the client generating the 'secure' token.
    It creates a Base64 payload containing the price.
    """
    if 'user' not in session: return redirect(url_for('login'))
    
    # Find product
    product = next((p for p in products if p['id'] == product_id), None)
    if not product: return "Product not found", 404

    # VULNERABILITY: We are putting the price IN the payload sent to the client
    order_data = {
        "product_id": product['id'],
        "product_name": product['name'],
        "price": product['price'] 
    }
    
    # Encode to Base64
    json_str = json.dumps(order_data)
    b64_token = base64.b64encode(json_str.encode()).decode()
    
    return render_template('confirm_order.html', product=product, token=b64_token)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    """
    This is the VULNERABLE endpoint.
    It trusts the price inside the Base64 token sent by the form.
    """
    if 'user' not in session: return redirect(url_for('login'))

    token = request.form['payment_token']
    
    try:
        # 1. Decode the token
        decoded_bytes = base64.b64decode(token)
        decoded_str = decoded_bytes.decode()
        order_data = json.loads(decoded_str)
        
        # 2. Process Payment (Vulnerable: trusting order_data['price'])
        final_price = order_data['price']
        product_name = order_data['product_name']
        
        # 3. Send to Telegram
        send_telegram_alert(product_name, final_price, session['user'])
        
        return render_template('success.html', price=final_price, product=product_name)
        
    except Exception as e:
        return f"Tampering Detected or Invalid Token: {e}", 400

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)