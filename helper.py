import bcrypt
from flask import sessions, render_template, Flask, request,flash,redirect
import yfinance as yf


#Hash the password
def hashpassword(password):
    hashed = bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt())
    return hashed

#Check password
def checkpassword(password,queried_hash):
    if bcrypt.checkpw(password.encode("utf-8"),queried_hash):
        return True
    else:
        return False

#Error handler
def error(reason):
    return render_template("error.html",reason=reason)

#Order
def order_return(input_quantity,input_stock,input_price,input_broker,input_order_type):
    message = f"{input_order_type.capitalize()} Order for {input_quantity} {input_stock} at ${input_price} through {input_broker} placed"
    return render_template("order.html",message=message)

