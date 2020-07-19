from flask import Flask, request
import stripe
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import jwt
import json

from flask_wtf.csrf import CsrfProtect
csrf = CsrfProtect()
import os
SECRET_KEY = os.urandom(32)


app = Flask(__name__)
#app.config['SECRET_KEY'] = SECRET_KEY
#csrf.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:biswa1234@localhost:5432/Stripe_Integration"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

stripe.api_key = "sk_test_N0iJfSR0GpyOvKBsbSUJbf7H00bpuDCPUD"
#stripe.api_key = "sk_test_51H4tmnC9Y8pTmB7V2vVrWAeGsI1uAMcuCld1wj0ko1m50vQNmwlVKzRJvKoe1nIijSLfyeDFqa5iJ9alpkn5JX1b005iBtDIgE"


class SessionInfo(db.Model):
    __tablename__ = 'SessionInfo'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String())
    sessionid = db.Column(db.String())
    status = db.Column(db.Integer())

    def __init__(self, userid, sessionid, status):
        self.userid = userid
        self.sessionid = sessionid
        self.status = status


@app.route("/getproducts", methods = ['GET'])
def getProducts():
    data=[]
    response = {}
    productList = stripe.Product.list()
    priceList = stripe.Price.list()
    for product in productList["data"]:
        for price in priceList["data"]:
            prodObject = {}
            if product["id"] == price["product"]:
                prodObject["productid"] = product["id"]
                prodObject["productName"] = product["name"]
                prodObject["description"] = product["description"]
                prodObject["priceId"] = price["id"]
                prodObject["amount"] = price["unit_amount_decimal"]
                prodObject["currency"] = price["currency"]
                prodObject["period"] = price["recurring"]["interval"]
                data.append(prodObject)
    response["status"] = 200
    response["data"] = data
    return response

@app.route("/createStripesession", methods=['POST'])
def createStripesession():
    response = {}
    data = request.json
    authHeader = request.headers.get('Authorization')
    auth_token = authHeader[7:]
    user_id = decode_auth_token(auth_token)
    if user_id=="IT":
        response["status"] = 404
        response["session_id"] = None
    else:
        suc_url = data.get("successUrl")
        can_url = data.get("cancelUrl")
        payment_method = data.get("payment_method_types")
        line_itmes_array = data.get("lineItems")
        modes = data.get("mode")
        sessionJson = stripe.checkout.Session.create(
                success_url=suc_url,
                cancel_url=can_url,
                payment_method_types=payment_method,
                line_items=line_itmes_array,
                mode=modes
                )
        response["status"] = 200
        response["session_id"] = sessionJson["id"]
        new_db_entry = SessionInfo(userid= user_id, sessionid = sessionJson["id"], status="unpaid")
        db.session.add(new_db_entry)
        db.session.commit()
    return response


@app.route("/payment-status", methods=['POST'])
def paymentStatus():
    data = request.json
    response = {}
    session_id = data["session_id"]
    row = SessionInfo.query.filter_by(sessionid=session_id).first()
    if row is None:
        response["status"] = 404
    else:
        response["status"] = 200
    response["paymentStatus"] = row.status
    return response


'''@app.route("/webhook", methods=['POST'])
def updatePayment():
    response = {}
    payload = request.json
    event = None
    print(payload)
    try:
        event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
                )
    except ValueError as e:
        response["status"] = 400
        response["message"] = "Invalid Payload"
        return response
    if event.type == 'checkout.session.completed':
        session = event.data.object
        handle_payments(session)
    else:
        response["status"] = 400
        response["message"]= "Unexpected Event Type"
        return response
    response["message"] = "Sucessfull event"
    response["status"] = 200  
    return response
'''
@app.route("/webhook", methods=['POST'])
def updatePayment():
    response = {}
    payload = request.get_data()
    endpoint_secret = "whsec_k8ohX8n86DfGooYIyngf9sFHxbGwxKM7"
    sig_header = request.headers['Stripe-Signature']
    event = None
    try:
        event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
                )
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            print(session["id"])
            handle_payments(session["id"])
    except ValueError as e:
        response["status"] = 400
        response["message"] = "Invalid Payload"
        return response
    except stripe.error.SignatureVerificationError as e:
        print(e)
        response["status"] = 400
        response["message"] = "Invalid signature" 
        return response
    response["message"] = "Sucessfull event"
    response["status"] = 200
    return response



def decode_auth_token(auth_token):
    try:
        key = "3$%^%&^ytfygf(kiiki_564"
        payload = jwt.decode(auth_token, key)
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError as e:
        return "IT"

def handle_payments(session):
    try:
        row = SessionInfo.query.filter_by(sessionid=session).first()
        row.status = "paid"
    except Exception as e:
        print(e)


if __name__ == '__main__':
    app.run()
