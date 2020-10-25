from flask import sessions, render_template, Flask, request,flash,redirect, url_for
from flask_session import sessions
from flask_sqlalchemy import SQLAlchemy
import sqlite3
from datetime import datetime, timedelta
from helper import checkpassword, hashpassword, error, order_return
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from yahoo_fin.stock_info import *
import math
import pandas as pd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Stockova2.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "ed5532419593034ba81f7e7bb768dd39"


db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer,primary_key=True,nullable=False)
    username = db.Column(db.String,nullable=False)
    passwordhash = db.Column(db.String,nullable=False)
    date_created = db.Column(db.DateTime,default=datetime.now)

class transaction(db.Model):
    id = db.Column(db.Integer,primary_key=True,nullable=False)
    user_id = db.Column(db.Integer,nullable=False)
    stock = db.Column(db.String,nullable=False)
    price = db.Column(db.String,nullable=False)
    quantity = db.Column(db.Integer,nullable=False)
    transtype = db.Column(db.String,nullable=False)
    broker = db.Column(db.String,nullable=False)
    profitloss = db.Column(db.String,nullable=False)
    date_created = db.Column(db.DateTime,default=datetime.now)

class stock_inventory(db.Model):
    id = db.Column(db.Integer,primary_key=True,nullable=False)
    user_id = db.Column(db.Integer,nullable=False)
    stock = db.Column(db.String,nullable=False)
    price = db.Column(db.String,nullable=False)
    quantity = db.Column(db.Integer,nullable=False)
    broker = db.Column(db.String,nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@app.route("/home")
@login_required
def index():
    #Grab all existing stocks from stock_invetory
    user_id = current_user.id
    stock_list = stock_inventory.query.filter_by(user_id=user_id).all()
    current_price_list=[]
    close_price_list = []

    for stock in stock_list:
        price = get_live_price(stock.stock)
        df_list = get_data(stock.stock, start_date=datetime.today()-timedelta(days=1))
        close_price_list.append(df_list.iloc[0].loc["adjclose"])
        current_price_list.append(price)
    
    return render_template("index.html",user=current_user.username, stock_list=stock_list, price_list = current_price_list,close_price_list = close_price_list)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        #Check if user exists
        if User.query.filter_by(username=username).first() != None:
            user = User.query.filter_by(username=username).first()
            #Check if password matches
            queried_hash = user.passwordhash
            if checkpassword(password,queried_hash) == True:
                login_user(user,remember=True,duration = timedelta(days=10))
                return redirect("/")
            else:
                return error("Wrong Password")

        else:
            return error("Cannot match username")

    else:
        return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        user = User(username = username,passwordhash = hashpassword(request.form.get("password")))
        print(User.query.filter_by(username = username).first())
        if User.query.filter_by(username = username).first() == None:
            db.session.add(user)
            db.session.commit()
            return redirect("/")
        else:
            return error("Username already exists. Please select another username")
    else:
        return render_template("/register.html")

@app.route("/order",methods=["GET","POST"])
@login_required
def order():
    if request.method == "POST":
        #If any of the form cells didn't get filled in
        if not request.form.get("stock") or not request.form.get("price") or not request.form.get("quantity") or not request.form.get("type"):
            return error("Please fill in the whole form")
        #All stocks got filled in
        else:
            if math.isnan(get_live_price(request.form.get("stock"))) == True:
                return error("The stock you entered doesn't exist")
            else:
                user_id = current_user.get_id()
                input_stock = request.form.get("stock").upper()
                input_price = float(request.form.get("price"))
                input_quantity = int(request.form.get("quantity"))
                input_broker = str(request.form.get("broker"))
                input_order_type = request.form.get("type")
                #Buy Order
                if input_order_type == "buy":
                    #If this is a new stock in that broker for the user
                    if stock_inventory.query.filter_by(user_id=user_id,stock=input_stock,broker=input_broker).first() == None:
                        #Add into stock
                        print(input_broker)
                        entry = stock_inventory(user_id= user_id, 
                                                stock = input_stock, 
                                                price = input_price, 
                                                quantity = input_quantity, 
                                                broker = input_broker) 
                        #Add into transaction
                        order = transaction(user_id = user_id, 
                                    stock = input_stock, 
                                    price = input_price, 
                                    quantity = input_quantity, 
                                    transtype = input_order_type,
                                    broker = input_broker)
                        db.session.add(order)
                        db.session.add(entry)
                        db.session.commit()
                        return order_return(input_quantity,input_stock,input_price,input_broker,input_order_type)
                    #If not a new stock
                    else:
                        print("Buy Order, Existing Stock")
                        #Grab the existing stock number and average price
                        current_owned = stock_inventory.query.filter_by(user_id=user_id,stock=input_stock,broker=input_broker).first()
                        current_owned_price = float(current_owned.price)
                        current_owned_quantity = int(current_owned.quantity)
                        #Calculate the new average price
                        new_owned_quantity = current_owned_quantity + input_quantity
                        new_total = current_owned_price * current_owned_quantity + input_price * input_quantity
                        avg_price = new_total/(new_owned_quantity)
                        #Add into stock
                        current_owned.price = avg_price 
                        current_owned.quantity = new_owned_quantity
                        #Add into transaction
                        order = transaction(user_id = user_id, 
                                    stock = input_stock, 
                                    price = input_price, 
                                    quantity = input_quantity, 
                                    transtype = input_order_type,
                                    broker = input_broker)
                        db.session.add(order)
                        db.session.commit()                    
                        return order_return(input_quantity,input_stock,input_price,input_broker,input_order_type)
                #Sell Order
                else:
                    #If this is a new stock for the user
                    if stock_inventory.query.filter_by(user_id=user_id,stock=input_stock).first() == None:    
                        #The user doesn't own any of this stock, so can't sell.
                        return error("You don't own any of this stock")
                    #User owns this stock
                    else:
                        #Grab the existing stock number and average price
                        current_owned = stock_inventory.query.filter_by(user_id=user_id,stock=input_stock).first()
                        current_owned_price = float(current_owned.price)
                        current_owned_quantity = int(current_owned.quantity) 

                        if int(input_quantity) > int(current_owned_quantity):
                            return error("You don't have enough to sell!")
                        else:
                            
                            #Calculate profit or loss
                            #New quantity of stock = currently owned - user input
                            new_owned_quantity = current_owned_quantity - int(input_quantity)
                            #Change the order's profit and loss to (input quantity * (input price - currently owned stock's price)
                            profitloss = int(input_quantity) * (float(input_price) - current_owned_price)
                            order = transaction(user_id = user_id, 
                                    stock = input_stock, 
                                    price = input_price, 
                                    quantity = input_quantity, 
                                    transtype = input_order_type,
                                    broker = input_broker,
                                    profitloss = profitloss)
                            db.session.add(order)
                            db.session.commit()
                            #If there are no quantity of that stock left, remove entry from stock_inventory
                            if new_owned_quantity == 0:
                                db.session.delete(current_owned)
                                db.session.commit()
                            #If there are still quantity of that stock left, change entry in stock_inventory
                            else:
                                current_owned.quantity = new_owned_quantity
                                db.session.add(current_owned)
                                db.session.commit()
                            return order_return(input_quantity,input_stock,input_price,input_broker,input_order_type)
    else:
        return render_template("order.html")

@app.route("/history")
@login_required
def history():
    user_id = current_user.id
    transaction_list = transaction.query.filter_by(user_id=user_id).order_by(transaction.date_created.desc()).all()
    sum = 0
    for transactions in transaction_list:
        if transactions.profitloss != None:
            sum += transactions.profitloss
    return render_template("history.html",transaction_list = transaction_list, sum = sum)

@app.route("/info")
@login_required
def info():
    df_dict = get_financials("ERIC",yearly=False,quarterly=True)
    balance_sheet = df_dict["quarterly_balance_sheet"]
    income_statement = df_dict["quarterly_income_statement"]
    cash_flow = df_dict["quarterly_cash_flow"]
    return render_template("info.html",balance_sheet=[balance_sheet.to_html(classes="data",header="true")]
    ,income_statement=[income_statement.to_html(classes="data",header="true")]
    ,cash_flow=[cash_flow.to_html(classes="data",header="true")])

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)