from flask import Flask, render_template, request, jsonify
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
from statsmodels.tsa.deterministic import CalendarFourier, DeterministicProcess


app = Flask(__name__)

# =========================
# 🔥 LOAD MODEL ONCE
# =========================

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



# =========================
# 🔧 FEATURE CREATION
# =========================
def create_future_exog(index, steps):
    fourier = CalendarFourier(freq='YE', order=6)

    dp = DeterministicProcess(
        index=index,
        constant=True,
        order=1,
        seasonal=False,
        additional_terms=[fourier],
        drop=True
    )

    return dp.out_of_sample(steps=steps)

# for XGBoost

def forecast_future(model , df , steps , features):

    history = df.copy()
    preds = []
    future_dates = []
    
    last_dayofweek = history['dayofweek'].iloc[-1]
    last_day = history['day'].iloc[-1]
    last_trend = history['trend'].iloc[-1]
    last_month = history['month'].iloc[-1]

    last_date = history.index[-1]
    
    for i in range(steps):

        last_row = history.iloc[-1:].copy()
        
        pred = model.predict(last_row[features])[0]
        preds.append(round(pred))

        next_date = last_date + pd.Timedelta(days=1)
        future_dates.append(next_date)

        next_row = last_row.copy()
        next_row['aqi_value'] = pred

        new_dayofweek = (last_dayofweek + 1) % 7
        new_month = next_date.month  
        new_trend = last_trend + 1
        new_day = next_date.day

        next_row['dayofweek'] = new_dayofweek
        next_row['day'] = new_day
        next_row['month'] = new_month
        next_row['trend'] = new_trend

        
        next_row.index = [next_date]
        history = pd.concat([history , next_row])

        # lag feature update

        history['AQI_lag1'] =  history['aqi_value'].shift(1)
        history['AQI_lag7'] = history['aqi_value'].shift(7)
        history['AQI_lag30'] = history['aqi_value'].shift(30)

        # update rolling features

        history['rolling_mean'] = history['aqi_value'].rolling(window = 7).mean()
        history['rolling_std'] = history['aqi_value'].rolling(window = 7).std()

        last_dayofweek = new_dayofweek
        last_month = new_month
        last_day = new_day
        last_trend = new_trend
        last_date = next_date

        future_df = pd.DataFrame({
            'date' : future_dates,
            'value' : preds
        })

    
    return future_df




# =========================
# 🌐 ROUTES
# =========================
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/sarimax')
def sarimax():
    return render_template('sarimax.html')

@app.route('/xgboost')
def xgb():
    return render_template('xgboost.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

# =========================
# 🔮 SARIMAX API
# =========================
@app.route('/predict_sarimax', methods=["POST"])
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
def predict_xgb():
    data = request.json

    steps = int(data['days'])

    vals = forecast_future(model=xgb_model , df=last_data , steps=steps , features=features)

    return jsonify({
        "dates" : vals.iloc[: , 0].astype(str).to_list(),
        "values" : vals.iloc[:,1].to_list()
    })

    
if __name__ == '__main__':
    app.run(debug=True)