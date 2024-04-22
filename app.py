from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Configuración de la base de datos MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:juanesgc1@localhost:3306/financierapro'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Definición del modelo de usuario
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Float, nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)

    transactions = db.relationship('Transaction', backref='user')

    def __repr__(self):
        return f"User('{self.username}', '{self.balance}', '{self.account_number}')"

# Definición del modelo de transacción
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))  # 'transfer'
    amount = db.Column(db.Float, nullable=False)
    from_account = db.Column(db.String(50))
    to_account = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"Transaction('{self.type}', '{self.amount}', '{self.from_account}', '{self.to_account}')"

# Ruta de inicio
@app.route('/')
def home():
    return redirect(url_for('login'))

# Ruta de inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    messageLogin = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:   
            session['username'] = username
            session['balance'] = user.balance
            return redirect(url_for('account_status'))
        else:
            messageLogin = 'Invalid username or password'
    return render_template('login.html', messageLogin=messageLogin)

# Ruta de registro de usuario
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    messageSignup = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            messageSignup = 'Username already exists'
        elif username == "" or password == "":
            messageSignup = 'Username and Password are required'
        elif len(username) > 20 or len(password) != 6:
            messageSignup = 'Username must be less than 20 characters and password must be 6 characters'
        elif password != confirm_password:
            messageSignup = 'Passwords do not match'
        else:
            max_account_number = db.session.query(func.max(User.account_number)).scalar()
            if max_account_number is None:
                max_account_number = 0
            new_account_number = f'user{int(max_account_number) + 1:03}'
            new_user = User(username=username, password=password, balance=0.00, account_number=new_account_number)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('signup.html', messageSignup=messageSignup)

# Ruta del estado de la cuenta
@app.route('/account_status')
def account_status():
    username = session.get('username')
    balance = session.get('balance')
    messageTransfer = session.pop('messageTransfer', None)
    if username:
        user = User.query.filter_by(username=username).first()
        sender_transactions = Transaction.query.filter_by(user_id=user.id).all()
        receiver_transactions = [transaction for transaction in sender_transactions if transaction.from_account != username]
        sender_transactions = [transaction for transaction in sender_transactions if transaction not in receiver_transactions]
        account_info = {
            'username': username,
            'account_number': user.account_number,
            'balance': balance,
            'sender_transactions': sender_transactions,
            'receiver_transactions': receiver_transactions
        }
        return render_template('account_status.html', account_info=account_info, messageTransfer=messageTransfer)
    else:
        return redirect(url_for('login'))

# Ruta para transferir dinero
@app.route('/transfer', methods=['POST'])
def transfer():
    messageTransfer = ""
    if request.method == 'POST':
        amount = float(request.form['amount'])
        to_account = request.form['to_account']
        if not User.query.filter_by(username=to_account).first():
            messageTransfer = "Destination account not found."
        elif session['balance'] < amount:
            messageTransfer = "Insufficient balance."
        else:
            sender_user = User.query.filter_by(username=session['username']).first()
            receiver_user = User.query.filter_by(username=to_account).first()
            sender_user.balance -= amount
            receiver_user.balance += amount
            sender_transaction = Transaction(type='transfer', amount=amount, from_account=session['username'], to_account=to_account, user_id=sender_user.id)
            receiver_transaction = Transaction(type='transfer', amount=amount, from_account=session['username'], to_account=to_account, user_id=receiver_user.id)
            db.session.add(sender_transaction)
            db.session.add(receiver_transaction)
            db.session.commit()
            session['balance'] = sender_user.balance
            messageTransfer = "Transferencia exitosa."
    session['messageTransfer'] = messageTransfer 
    return redirect(url_for('account_status'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
