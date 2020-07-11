from flask import Flask, request
import stripe
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import jwt


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:biswa1234@localhost:5432/Stripe_Integration"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

stripe.api_key = "sk_test_N0iJfSR0GpyOvKBsbSUJbf7H00bpuDCPUD"


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
    new_db_entry = SessionInfo(userid="userid1", sessionid = sessionJson["id"], status="unpaid")
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

@staticmethod
def decode_auth_token(auth_token):
    try:
        payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'))
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return 'Invalid token. Please log in again.'




if __name__ == '__main__':
    app.run()