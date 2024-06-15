from market import db,login_manager
from market import app
from market import bcrypt
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id=db.Column(db.Integer(), primary_key=True)
    username=db.Column(db.String(length=30), nullable=False, unique=True)
    email_address=db.Column(db.String(length=50),nullable=False,unique=True)
    password_hash=db.Column(db.String(length=60),nullable=False)
    budget=db.Column(db.Integer(),nullable=False, default=1000)
    is_admin = db.Column(db.Boolean(), nullable=False, server_default='0')
    items=db.relationship('Item',backref='owned_user',lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)


    def can_sell(self, item_obj):
        return item_obj in self.items


    
    def can_purchase(self, item_obj):
        return self.budget >= item_obj.price
    

    @property
    def prettier_budget(self):
        if len(str(self.budget)) >= 4:
            return f'{str(self.budget)[:-3]},{str(self.budget)[-3:]}$'
        else:
            return f"{self.budget}$"
        
    @property
    def password(self):
        return self.password

    @password.setter
    def password(self, plain_text_password):
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self, attempted_password):
        return bcrypt.check_password_hash(self.password_hash, attempted_password)
    
    

class Item(db.Model):
    id=db.Column(db.Integer(), primary_key=True)
    name=db.Column(db.String(length=30), nullable=False, unique=True)
    price= db.Column(db.Integer(), nullable=False )
    barcode=db.Column(db.String(length=12), nullable=False,unique=True)
    description=db.Column(db.String(length=1024), nullable=False, unique=True)
    category=db.Column(db.String(),nullable=False)
    owner=db.Column(db.Integer(),db.ForeignKey('user.id'))
    

    def sell(self, user):
        self.owner = None
        user.budget += self.price
        db.session.commit()


    def buy(self, user):
        self.owner = user.id
        user.budget -= self.price
        db.session.commit()
    
    def __repr__(self):
        return f'Item {self.name}'


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    feedback_text = db.Column(db.String(length=500), nullable=False)

    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))
    item = db.relationship('Item', backref=db.backref('feedbacks', lazy=True, cascade="all, delete-orphan"))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.String(length=280), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class PurchaseRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    request_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship('User', backref='purchase_requests')
    item = db.relationship('Item', backref='purchase_requests')


with app.app_context():
    db.create_all()
    