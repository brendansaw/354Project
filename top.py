from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mysqldb import MySQL
from flask_login import login_user, logout_user, login_required, LoginManager, current_user, UserMixin
from user import User, create_user
from flask_bootstrap import Bootstrap
from flask_nav import Nav
from flask_nav.elements import *
from datetime import date
from useraccountforms import CustomerAccountForm, SellerAccountForm
from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, PasswordField, SubmitField, BooleanField, TextField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Email, EqualTo, Optional

app = Flask(__name__)

bootstrap = Bootstrap(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'cmpt354'
app.config['SECRET_KEY'] = 'test'

mysql = MySQL(app)

topbar = Navbar(View("Home", "home"))

nav = Nav()
nav.register_element('topbar', topbar)
nav.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    cursor = mysql.connection.cursor()
    # see if user is in DB
    cursor.execute(
        f"""SELECT `user_password`, `house_number`, `street_name`, `postal_code`, `province`, `city`, `email` 
        FROM user 
        WHERE userid='{user_id}'""")
    user = cursor.fetchall()[0]
    pw, hn, sn, pc, pv, c, em = user[0], user[1], user[2], user[3], user[4], user[5], user[6]
    cursor.execute(
        f"""SELECT first_name, last_name 
        FROM customer
        WHERE id='{user_id}'""")
    name = cursor.fetchall()[0]
    fn, ln = name[0], name[1]
    cursor.execute(
        f"""SELECT payment_method
        FROM customer_payment_method
        WHERE customerid='{user_id}'""")
    pm = cursor.fetchall()[0][0]

    cursor.close()
    return User(
        userid=user_id,
        password=pw,
        house_number=hn,
        street_name=sn,
        postal_code=pc,
        province=pv,
        city=c,
        email=em,
        fname=fn,
        lname=ln,
        payment_method=pm
    )


@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

#@auth.route('/logout')
#def logout():
#    return render_template('Logout')

@app.route('/signup', methods=['POST'])
def signup_post():
    username = request.form.get('username')
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    password = request.form.get('password')
    email = request.form.get('email')
    house_number = request.form.get('house_number')
    street_name = request.form.get('street_name')
    postal_code = request.form.get('postal_code')
    province = request.form.get('province')
    city = request.form.get('city')
    payment_method = request.form.get('payment_method')

    cursor = mysql.connection.cursor()
    # see if user is in DB
    cursor.execute(f"""SELECT * FROM user WHERE userid='{username}'""")
    user = cursor.fetchall()

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash("Username is already in use")
        return redirect(url_for('signup'))
    
    print(request.form)
    print(username, fname, lname, password, email, house_number, street_name, postal_code, province, city, payment_method)

    user_obj = User(
        userid=username,
        password=generate_password_hash(password, method='sha256'),
        house_number=house_number,
        street_name=street_name,
        postal_code=postal_code,
        province=province,
        city=city,
        email=email,
        fname=fname,
        lname=lname,
        payment_method=payment_method
    )

    #session['user'] = user_obj

    # add user to DB
    cursor.execute(f"""INSERT INTO user (`userid`, `user_password`, `house_number`, `street_name`, `postal_code`, `province`, `city`, `email`)
                       VALUES('{username}', '{generate_password_hash(password, method='sha256')}', '{house_number}', '{street_name}', '{postal_code}', '{province}', '{city}', '{email}')""")
    # add customer to DB
    cursor.execute(f"""INSERT INTO customer (id, first_name, last_name)
                       VALUES('{username}', '{fname}', '{lname}')""")
    cursor.execute(f"""INSERT INTO customer_payment_method (customerid, payment_method)
                       VALUES('{username}', '{payment_method}')""")
    mysql.connection.commit()
    cursor.close()

    # code to validate and add user to database goes here
    return redirect(url_for('login'))

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    cursor = mysql.connection.cursor()
    # see if user is in DB
    cursor.execute(f"""SELECT * FROM user WHERE userid='{username}'""")
    user = cursor.fetchall()
    cursor.close()
    print(user)
    if not user or (not check_password_hash(user[0][1], password) and user[0][1] != password): # if a user is found, we want to redirect back to signup page so user can try again
        flash("Username/Password is invalid")
        return redirect(url_for('login'))
    user2 = create_user(user[0][0])
    print("Jello")
    login_user(user2, remember=remember)
    return redirect(url_for('profile'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("logged_out"))

@app.route("/")
def home():
    cursor = mysql.connection.cursor()
    # get the first user
    cursor.execute('''SELECT * FROM customer;''')
    users = cursor.fetchall()
    user = users[0]
    session['user'] = user
    session['orderID'] = 999
    cursor.close()
    return render_template("index.html", user=current_user)

@app.route("/shopping_cart", methods=["GET", "POST"])
@login_required
def shopping_cart():
    cursor = mysql.connection.cursor()

    user = current_user

    # get the items in the cart
    cursor.execute(f'''SELECT P.product_name, PSC.quantity, P.price, P.price*PSC.quantity AS total_price
                       FROM product_in_shopping_cart AS PSC, product AS P 
                       WHERE customerid="{user.userid}" AND PSC.productid = P.productid;''')
    products = cursor.fetchall()
    cursor.close()

    # get the subtotal
    subtotal = sum([int(products[-1]*100) for products in products])/100
    session['subtotal'] = subtotal
    print(user)
    print(products)
    if request.method == "POST":
        if "sc" in request.form:
            return redirect(url_for(".home"))
        elif "checkout" in request.form:
            if len(products) == 0:
                flash("No products ordered!")
                return redirect(url_for(".shopping_cart"))
            else:
                return redirect(url_for(".checkout"))
        for p in products:
            #print(f"delete_{p[0]}")
            if f"delete_{p[0]}" in request.form:
                cursor = mysql.connection.cursor()
                cursor.execute(f'''DELETE FROM product_in_shopping_cart
                                   WHERE customerid="{user.userid}" AND productid IN (
                                       SELECT productid
                                       FROM product
                                       WHERE product_name="{p[0]}");''')
                mysql.connection.commit()
                cursor.close()
                print(f"deleting {p[0]}")
                return redirect(url_for(".redirect_on_delete"))

    cursor = mysql.connection.cursor() 
    # get the items in the cart
    cursor.execute(f'''SELECT P.product_name, PSC.quantity, P.price, P.price*PSC.quantity AS total_price
                       FROM product_in_shopping_cart AS PSC, product AS P 
                       WHERE customerid="{user.userid}" AND PSC.productid = P.productid;''')
    products = cursor.fetchall()
    cursor.close()

    return render_template("shopping_cart.html", items=products, subtotal=subtotal, user=current_user)

@app.route("/redirect")
@login_required
def redirect_on_delete():
    return redirect(url_for(".shopping_cart"))

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout(): 
    cursor = mysql.connection.cursor()

    user = current_user

    # get the subtotal
    subtotal = session['subtotal']

    if request.method == "POST":
        if "confirm" in request.form:
            ts = date.today()

            cursor = mysql.connection.cursor()

            cursor.execute(f"""SELECT orderid FROM store_order GROUP BY orderid ORDER BY orderid DESC""")

            orderID = cursor.fetchall()[0][0]+1

            subtotal = session['subtotal']

            print(orderID)

            cursor.execute(f"""INSERT INTO store_order (`customerid`, `orderid`, `cost`, `order_time`, `payment_method_used`)
                            VALUES ('{user.userid}', {orderID}, {subtotal*1.12}, '{ts}', '{user.payment_method}')""")
            mysql.connection.commit()

            cursor.execute(f"""DELETE FROM product_in_shopping_cart
                               WHERE customerid='{user.userid}'""")
            mysql.connection.commit()
            return redirect(url_for(".order_confirmed"))
            
        elif "cancel" in request.form:
            return redirect(url_for(".shopping_cart"))

    return render_template("checkout.html", user=current_user, subtotal=subtotal, user_dict={
        "Name": current_user.fname + " " + current_user.lname,
        "Email": current_user.email,
        "House Number": current_user.house_number,
        "Street Name": current_user.street_name,
        "Postal Code": current_user.postal_code,
        "Province": current_user.province,
        "City": current_user.city,
        "Payment Method": current_user.payment_method
    })

@app.route("/order_confirmed", methods=["GET", "POST"])
@login_required
def order_confirmed():
    # TODO: Fix orderID incrementing
    ts = date.today()

    orderID = session['orderID']

    if request.method == "POST":
        if "home" in request.form:
            return redirect(url_for(".home"))

    return render_template("order_confirmed.html", orderID=orderID, timestamp=ts, user=current_user)

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", name=current_user.fname+" "+current_user.lname, user=current_user)

@app.route("/logged_out")
def logged_out():
    return render_template("logged_out.html", user=current_user)

@app.route("/category/<selected_category>", methods=['GET', 'POST'])
def goToCategory(selected_category):
    actualSelectedCategory = selected_category.lower()
    if (actualSelectedCategory == "all"):
        actualSelectedCategory = "%"
    cursor = mysql.connection.cursor()
    productsToSelect = "product_name, price, sellerid, product_description, category_name, best_before_date"
    # preventing SQL injection from URL
    cursor.execute(f"SELECT { productsToSelect } FROM product WHERE LOWER(category_name) LIKE %(parameterInput)s", {'parameterInput': actualSelectedCategory})
    retVal = cursor.fetchall()
    cursor.close()
    table = []
    '''for i in retVal:
        temp = []
        #print(i, file=sys.stderr)
        for j in i:
            #print(j)
            '''

    if (request.method == "POST"):
        if (request.form['submitbutton'] == "home"):
            return redirect(url_for("home"))
    else:      
        return render_template("category.jinja2", selected_category=selected_category, retVal=retVal)


@app.before_request
def initNavBar():
    topbar = Navbar(View("Home", "home"))
    nav.register_element('topbar', topbar)

    topbar.items.append(View("Shopping Cart", "shopping_cart"))

    if (not current_user.is_authenticated):
        topbar.items.append(View("Login", "login"))
        topbar.items.append(View("Sign Up", "signup"))
    else:
        topbar.items.append(View("Logout", "logout"))
        topbar.items.append(View("Profile", "profile"))
        topbar.items.append(Text(current_user.userid))


    topbar.items.append(View("All", "goToCategory", selected_category = "All"))

    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT category_name FROM category''')
    retVal = cursor.fetchall()
    cursor.close()
    #topbar.items.append(View("Hello", "home"))
    
    for i in retVal:
        j = ''.join(i)  # to get the string
        topbar.items.append(View(j, "goToCategory", selected_category = j))
    
@app.route("/Orders")
def Orders():
    cursor = mysql.get_db().cursor()
    cursor.execute('''SELECT first_name, last_name,orderid,product_name,cost,order_Time,payment_method_used  FROM store_order, customer,product WHERE customer.id = store_order.customerid AND store_order.cost = product.price''')
    retVal = cursor.fetchall()
    cursor.close()
    return render_template('OrderHistory.html',orders = retVal)

@app.route('/account', methods=['GET', 'POST'])
def account():
    form = CustomerAccountForm()

    if form.validate_on_submit():
        db_connection = mysql.connection
        db_cursor = db_connection.cursor()
        
        for field in form:
            if field.name != 'submit' and field.name != 'csrf_token' and field.data != None and field.data != '':
                if field.name == 'first_name' or field.name == 'last_name':
                    db_cursor.execute('''
                                            UPDATE customer
                                            SET {} = %s
                                            WHERE id = 'H123'
                                      '''.format(field.name) ,
                                      (field.data,))
                else:
                    db_cursor.execute('''
                                            UPDATE user
                                            SET {} = %s
                                            WHERE userid = 'H123'
                                      '''.format(field.name) ,
                                      (field.data,))

                db_connection.commit()
                flash(f'Changes saved!', 'success')
    return render_template('account.html', title='Account', form=form)

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)