from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import random
import string

db = SQLAlchemy()

def generate_shop_code():
    return "MM" + ''.join(random.choices(string.digits, k=4))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))

    shop = db.relationship('Shop', backref='owner', uselist=False)
    orders = db.relationship('Order', backref='customer')

class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    address = db.Column(db.String(200))
    shop_code = db.Column(db.String(10), unique=True, default=generate_shop_code)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    products = db.relationship('Product', backref='shop')
    orders = db.relationship('Order', backref='shop')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    description = db.Column(db.String(200))
    price = db.Column(db.Float)
    stock = db.Column(db.Integer)
    image = db.Column(db.String(200))
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))

    order_items = db.relationship('OrderItem', backref='product')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    total = db.Column(db.Float)
    status = db.Column(db.String(20), default="Pending")
    payment_method = db.Column(db.String(20))

    items = db.relationship('OrderItem', backref='order')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)