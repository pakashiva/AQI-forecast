from statsmodels.tsa.deterministic import CalendarFourier, DeterministicProcess
import pandas as pd

# feature creation for sarimax

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


