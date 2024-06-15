from market import app
from functools import wraps
from flask import render_template,redirect,url_for,flash, request
from market.models import Item,User,Feedback,Comment,PurchaseRequest
from market.forms import RegisterForm, LoginForm, PurchaseItemForm,  SellItemForm
from market import db
from flask_login import login_user, logout_user, login_required,current_user



@app.route('/')
@app.route('/home')
def home_page():
    return render_template('home.html')

@app.route('/about/<username>')
def about_page(username):
    return f'<h1> About Page of {username} </h1>'

@app.route('/market',methods=['GET','POST'])
@login_required
def market_page():
    purchase_form = PurchaseItemForm()
    selling_form = SellItemForm()
    if request.method=="POST":
        purchased_item=request.form.get('purchased_item')
        p_item_object=Item.query.filter_by(name=purchased_item).first()
        if p_item_object:
            if current_user.can_purchase(p_item_object):
                p_item_object.buy(current_user)
                flash(f"Congratulations! You purchased {p_item_object.name} for {p_item_object.price}$", category='success')
            else:
                flash(f"Unfortunately, you don't have enough money to purchase {p_item_object.name}!", category='danger')

        sold_item = request.form.get('sold_item')
        s_item_object = Item.query.filter_by(name=sold_item).first()
        if s_item_object:
            if current_user.can_sell(s_item_object):
                s_item_object.sell(current_user)
                flash(f"Congratulations! You sold {s_item_object.name} back to market!", category='success')
            else:
                flash(f"Something went wrong with selling {s_item_object.name}", category='danger')

        return redirect(url_for('market_page'))
    
    items_by_category = {}
    all_categories = set()  # To ensure all categories are accounted for

    if request.method=="GET":
        # Fetch all items from the database
        items = Item.query.filter_by(owner=None)

        # Group items by category
        for item in items:
            if item.category not in items_by_category:
                items_by_category[item.category] = []
            items_by_category[item.category].append(item)
            all_categories.add(item.category)

        # Fetch owned items of the current user
        owned_items = Item.query.filter_by(owner=current_user.id)

        # Render the market page with items grouped by category
        return render_template('market.html', items_by_category=items_by_category, all_categories=all_categories,
                            purchase_form=purchase_form, owned_items=owned_items, selling_form=selling_form)
    # Other parts of your route code

@app.route('/register',methods=['GET','POST'])
def register_page():
    form=RegisterForm()
    if form.validate_on_submit():
        user_to_create=User(username=form.username.data,
                            email_address=form.email_address.data,
                            password=form.password1.data
                            )
        db.session.add(user_to_create)
        db.session.commit()
        login_user(user_to_create)
        flash(f"Account created successfully! You are now logged in as {user_to_create.username}", category='success')
        return redirect(url_for('market_page'))
    
    if form.errors != {}:
        for err_msg in form.errors.values():
            flash(f'There was an error in creating the user: {err_msg}',category='danger')
    return render_template('register.html',form=form)

@app.route('/logout')
def logout_page():
    logout_user()
    flash("You have been logged out!", category='info')
    return redirect(url_for("home_page"))


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(username=form.username.data).first()
        if attempted_user and attempted_user.check_password_correction(
                attempted_password=form.password.data
        ):
            login_user(attempted_user)
            flash(f'Success! You are logged in as: {attempted_user.username}', category='success')
            return redirect(url_for('market_page'))
        else:
            flash('Username and password are not match! Please try again', category='danger')


    return render_template('login.html', form=form)

@app.route("/addbook", methods=["GET", "POST"])
def addbook():
    if request.method == "POST":
        if current_user.is_admin:  # Check if the current user is an admin
            # Extract book details from the form
            name = request.form.get('name')
            price = request.form.get('price')
            barcode = request.form.get('barcode')
            description = request.form.get('description')
            category=request.form.get('category')
            owner= request.form.get('owner')

            # Create a new item (book) object
            book = Item(
                name=name,
                price=price,
                barcode=barcode,
                description=description,
                category=category
            )

            # Add the book to the database
            db.session.add(book)
            db.session.commit()

            flash("Book added successfully!", category='success')
            return redirect(url_for('market_page'))
        else:
            flash("You are not authorized to add a book.", category='danger')
            return redirect(url_for('market_page'))
    
    return render_template('addbook.html')

@app.route('/current_owners')
def current_owners():
    # Retrieve all items from the database along with their current owners
    items = Item.query.all()
    return render_template('current_owners.html', items=items)

@app.route('/remove_owner/<int:item_id>', methods=['POST'])
def remove_owner(item_id):
    item = Item.query.get_or_404(item_id)
    item.owner = None
    db.session.commit()
    return redirect(url_for('current_owners'))

@app.route('/delete_book/<int:item_id>', methods=['POST'])
def delete_book(item_id):
    try:
        item = Item.query.get_or_404(item_id)
        
        # Delete related purchase requests first
        PurchaseRequest.query.filter_by(item_id=item_id).delete()
        
        # Now delete the item
        db.session.delete(item)
        db.session.commit()
        return redirect(url_for('market_page'))
    except Exception as e:
        db.session.rollback()
        # Handle any other exception, log the error or inform the user
        return str(e), 500

@app.route('/search', methods=['GET', 'POST'])
def search_books():
    if request.method == 'POST':
        book_name = request.form['book_name']
        book = Item.query.filter_by(name=book_name).first()
        if book:
            return render_template('book_found.html', book=book)
        else:
            return render_template('book_not_found.html', book_name=book_name)
    return render_template('search.html')

@app.route('/submit_feedback', methods=['GET', 'POST'])
def submit_feedback():
    if request.method == 'POST':
        book_id = request.form['book_id']
        feedback_text = request.form['feedback_text']
        user_id = current_user.id  # Assuming you are using Flask-Login for user authentication
        feedback = Feedback(user_id=user_id, item_id=book_id, feedback_text=feedback_text)
        db.session.add(feedback)
        db.session.commit()
        return redirect(url_for('market_page'))
    
    return render_template('submit_feedback.html')

@app.route('/feedbacks')
def view_feedbacks():
    feedbacks = Feedback.query.all()
    return render_template('feedbacks.html', feedbacks=feedbacks)

@app.route('/post_comment', methods=['POST','GET'])
@login_required
def post_comment():
    if request.method == 'POST':
        comment_text = request.form['comment_text']
        comment = Comment(user_id=current_user.id, text=comment_text)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('view_comments'))
    return render_template('post_comment.html')  # Redirect to homepage if not a POST request

@app.route('/view_comments')
@login_required
def view_comments():
    comments = Comment.query.order_by(Comment.timestamp.desc()).all()
    return render_template('view_comments.html', comments=comments)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('market_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/purchase', methods=['POST'])
def purchase():
    # Print form data for debugging
    print("Form data:", request.form)
    item_id = request.form.get('purchased_item')
    print("Received item_id:", item_id)  # Debugging line
    item = Item.query.get(item_id)
    print(item)
    if item:
        purchase_request = PurchaseRequest(user_id=current_user.id, item_id=item.id)
        db.session.add(purchase_request)
        db.session.commit()
        flash('Purchase request submitted. Waiting for admin approval.', 'info')
    else:
        flash('Item not found.', 'danger')
    return redirect(url_for('market_page'))

@app.route('/admin/purchase-requests')
@login_required  # Assuming you have a decorator to check admin permissions
def view_purchase_requests():
    requests = PurchaseRequest.query.filter_by(status='pending').all()
    return render_template('admin/purchase_requests.html', requests=requests)


@app.route('/admin/approve-purchase/<int:request_id>')
@login_required
def approve_purchase(request_id):
    purchase_request = PurchaseRequest.query.get(request_id)
    if purchase_request:
        user = User.query.get(purchase_request.user_id)
        item = Item.query.get(purchase_request.item_id)
        if item and user:
            if user.budget >= item.price:
                user.budget -= item.price
                item.owner = purchase_request.user_id
                purchase_request.status = 'approved'
                db.session.commit()
                flash('Purchase request approved and item ownership updated.', 'success')
            else:
                flash('User does not have enough budget to buy this item.', 'danger')
        else:
            flash('Item or user associated with purchase request not found.', 'danger')
    else:
        flash('Purchase request not found.', 'danger')
    return redirect(url_for('view_purchase_requests'))

@app.route('/admin/reject-purchase/<int:request_id>')
@login_required
def reject_purchase(request_id):
    purchase_request = PurchaseRequest.query.get(request_id)
    if purchase_request:
        purchase_request.status = 'rejected'
        db.session.commit()
        flash('Purchase request rejected.', 'info')
    else:
        flash('Purchase request not found.', 'danger')
    return redirect(url_for('view_purchase_requests'))





