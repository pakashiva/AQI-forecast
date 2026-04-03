from flask import Flask, render_template, request, jsonify , redirect , url_for ,session
from functools import wraps
from werkzeug.security import generate_password_hash , check_password_hash
from utils import create_future_exog , forecast_future
import pickle
import numpy as np
import xgboost as xgb
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)


# Database Handling
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db_sql = SQLAlchemy(app)

# schema creation

class Users(db_sql.Model):
    id = db_sql.Column(db_sql.Integer , primary_key = True , nullable = False)
    username = db_sql.Column(db_sql.String(200) , nullable = False , unique = True)
    email = db_sql.Column(db_sql.String(150) , nullable = False)
    password = db_sql.Column(db_sql.String(150) , nullable = False)

# session handling
app.config['SECRET_KEY'] = 'secrete_key'

def login_required(f):
    @wraps(f)
    def wrapper(*args , **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args , **kwargs)
    return wrapper


# LOAD MODEL
xgb_model = xgb.XGBRegressor()
xgb_model.load_model("models/delhi/xgb_model.json")

with open("models/delhi/features.pkl" , "rb") as f:
    features = pickle.load(f)

with open("models/delhi/last_50rows.pkl" , "rb") as f:
    last_data = pickle.load(f)

with open("models/delhi/sarimax_model.pkl", "rb") as f:
    sarimax_model = pickle.load(f)

with open("models/delhi/train_index.pkl", "rb") as f:
    train_index = pickle.load(f)



# ROUTES

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/sarimax')
@login_required
def sarimax():
    return render_template('sarimax.html')

@app.route('/xgboost')
@login_required
def xgboost():
    return render_template('xgboost.html')

@app.route('/register' ,methods = ['GET' , 'POST'])
def register():

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)

        if not email or '@' not in email:
            return "Invalid Email, try again"

        existing_user  = Users.query.filter_by(username = username).first()
        existing_email = Users.query.filter_by(email = email).first()

        if existing_user:
            return 'Username Already exists, try another'
        
        if existing_email:
            return 'This email Already exists, try another'
        
        new_user = Users(username = username , email = email , password = hashed_password)
        db_sql.session.add(new_user)
        db_sql.session.commit()

        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login' , methods = ['GET' , 'POST'])
def login():

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = Users.query.filter_by(email = email).first()

        if not email or '@' not in email:
            return "Invalid email or email doesn't exists"

        if user and check_password_hash(user.password , password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return "Invalid credentials"

    return render_template('login.html')

# SARIMAX API

@app.route('/predict_sarimax', methods=["POST"])
@login_required
def predict_sarimax():

    data = request.json

    years = int(data['years'])
    city = data['city']   # (for future multi-city support)

    steps = years * 365

    # Generate exogenous variables
    exog_future = create_future_exog(train_index, steps)

    # Forecast
    forecast_obj = sarimax_model.get_forecast(
        steps=steps,
        exog=exog_future
    )

    forecast = forecast_obj.predicted_mean
    conf_int = forecast_obj.conf_int()

    # 🔥 Reverse log transform
    forecast = np.exp(forecast)
    conf_int = np.exp(conf_int)

    # Convert to DataFrame
    forecast_df = forecast.to_frame(name='value')

    # 📊 Monthly aggregation (better UX)
    monthly = forecast_df.resample('ME').mean()

    lower = conf_int.iloc[:, 0].resample('ME').mean()
    upper = conf_int.iloc[:, 1].resample('ME').mean()

    return jsonify({
        "dates": monthly.index.strftime('%Y-%m').tolist(),
        "values": monthly['value'].tolist(),
        "lower": lower.tolist(),
        "upper": upper.tolist()
    })

@app.route('/predict_xgb' , methods = ['POST'])
@login_required
def predict_xgb():
    data = request.json

    steps = int(data['days'])

    vals = forecast_future(model=xgb_model , df=last_data , steps=steps , features=features)

    return jsonify({
        "dates" : vals.iloc[: , 0].astype(str).to_list(),
        "values" : vals.iloc[:,1].to_list()
    })

@app.route('/logout')
@login_required
def logout():
    session.pop("user_id", None)
    return redirect(url_for('login'))


@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = Users.query.get(session['user_id'])
        return dict(current_user = user)
    return dict(current_user = None)
    
if __name__ == '__main__':
    app.run(debug=True)