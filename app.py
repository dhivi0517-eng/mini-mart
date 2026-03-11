from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

from models import db, User, Shop, Product, Order, OrderItem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multistore_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ================= HOME =================
@app.route('/')
def index():
    return render_template("index.html")


# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        if User.query.filter_by(email=request.form['email']).first():
            flash("Email already exists")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(request.form['password'])

        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=hashed_password,
            role=request.form['role']
        )
        db.session.add(user)
        db.session.commit()

        # If owner create shop
        if user.role == "owner":
            shop = Shop(
                name=request.form['shop_name'],
                address=request.form['shop_address'],
                owner_id=user.id
            )
            db.session.add(shop)
            db.session.commit()

        flash("Registered Successfully")
        return redirect(url_for('login'))

    return render_template("register.html")


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()

        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            if user.role == "owner":
                return redirect(url_for('owner_dashboard'))
            return redirect(url_for('shop_list'))

        flash("Invalid Credentials")

    return render_template("login.html")


# ================= LOGOUT =================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))


# ================= SHOP LIST =================
@app.route('/shops')
@login_required
def shop_list():
    shops = Shop.query.all()
    return render_template("shop_list.html", shops=shops)


# ================= SHOP PRODUCTS =================
@app.route('/shop/<int:shop_id>')
@login_required
def shop_products(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    products = Product.query.filter_by(shop_id=shop.id).all()
    return render_template("shop_products.html", shop=shop, products=products)


# ================= OWNER DASHBOARD =================
@app.route('/owner')
@login_required
def owner_dashboard():
    if current_user.role != "owner":
        return redirect(url_for('index'))

    shop = Shop.query.filter_by(owner_id=current_user.id).first()

    products = Product.query.filter_by(shop_id=shop.id).all()

    orders = Order.query.filter_by(shop_id=shop.id)\
                        .order_by(Order.id.desc())\
                        .all()

    return render_template("owner_dashboard.html",
                           shop=shop,
                           products=products,
                           orders=orders)


# ================= CUSTOMER ORDER HISTORY =================
@app.route('/my_orders')
@login_required
def my_orders():
    if current_user.role != "customer":
        return redirect(url_for('index'))

    orders = Order.query.filter_by(customer_id=current_user.id)\
                        .order_by(Order.id.desc())\
                        .all()

    return render_template("orders.html", orders=orders)


# ================= ADD PRODUCT =================
@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role != "owner":
        return redirect(url_for('index'))

    shop = Shop.query.filter_by(owner_id=current_user.id).first()

    if request.method == 'POST':

        image = request.files.get('image')
        filename = None

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        product = Product(
            name=request.form['name'],
            description=request.form['description'],
            price=float(request.form['price']),
            stock=int(request.form['stock']),
            image=filename,
            shop_id=shop.id
        )
        db.session.add(product)
        db.session.commit()

        flash("Product Added Successfully")
        return redirect(url_for('owner_dashboard'))

    return render_template("add_product.html")


# ================= ADD TO CART =================
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form['quantity'])

    if quantity <= 0:
        return redirect(request.referrer)

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    session['cart'] = cart

    flash("Added to Cart")
    return redirect(request.referrer)


# ================= CART =================
@app.route('/cart')
@login_required
def cart():
    cart = session.get('cart', {})
    items = []
    total = 0

    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if not product:
            continue

        subtotal = product.price * qty
        total += subtotal

        items.append({
            'product': product,
            'quantity': qty,
            'subtotal': subtotal
        })

    return render_template("cart.html", items=items, total=total)


# ================= PLACE ORDER =================
@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    cart = session.get('cart', {})

    if not cart:
        flash("Cart is empty")
        return redirect(url_for('shop_list'))

    payment_method = request.form['payment']

    first_product = Product.query.get(int(list(cart.keys())[0]))
    shop_id = first_product.shop_id

    order = Order(
        customer_id=current_user.id,
        shop_id=shop_id,
        total=0,
        payment_method=payment_method,
        status="Pending"
    )
    db.session.add(order)
    db.session.commit()

    total = 0

    for pid, qty in cart.items():
        product = Product.query.get(int(pid))

        if product.stock < qty:
            flash(f"Not enough stock for {product.name}")
            return redirect(url_for('cart'))

        subtotal = product.price * qty
        total += subtotal

        # Reduce stock
        product.stock -= qty

        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=qty
        )
        db.session.add(item)

    order.total = total
    db.session.commit()

    session.pop('cart', None)

    flash("Order Placed Successfully")
    return redirect(url_for('my_orders'))


# ================= UPDATE STATUS =================
@app.route('/update_status/<int:order_id>')
@login_required
def update_status(order_id):

    order = Order.query.get_or_404(order_id)

    # Security check
    if current_user.role == "owner":
        shop = Shop.query.filter_by(owner_id=current_user.id).first()

        if order.shop_id == shop.id:
            order.status = "Ready"
            db.session.commit()

    return redirect(url_for('owner_dashboard'))


# ================= INIT =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)