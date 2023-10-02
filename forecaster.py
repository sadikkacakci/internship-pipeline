import pandas as pd
from prophet import Prophet
import numpy as np
import logging
import sys
import os

logging.basicConfig(level=logging.INFO, 
                    format='[%(asctime)s] [%(levelname)s] %(message)s', 
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.getcwd()+"/logs")],
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


def prophet_preprocessor(data,value_feature):
    """
    Preprocesses time series data for use with Facebook Prophet forecasting.

    Args:
        data (pd.DataFrame): The input time series data.
        value_feature (str): The name of the feature to be used for forecasting.

    Returns:
        pd.DataFrame: Preprocessed data suitable for use with Prophet.
    """
    data = data.copy() 
    # Convert the 'Date' column to datetime format
    data['Date'] = pd.to_datetime(data['Date'])
    # Resample the data to 30-minute intervals and calculate the mean of 'value_feature' 
    data = data.resample('30T', on='Date')[value_feature].mean().reset_index()
    # Set the index to 'Date' and fill missing values by backfilling
    data = data.set_index('Date').asfreq('H')
    # Create a DataFrame for Prophet with 'ds' as the datetime index and 'y' as the target feature
    prophet_data = data[[value_feature]].interpolate(method='bfill')
    prophet_data['ds'] = prophet_data.index
    prophet_data['y'] = prophet_data[value_feature]
    # Reset the index and drop the original 'value_feature' column
    prophet_data.reset_index(drop=True,inplace=True)
    prophet_data.drop(columns=value_feature,inplace=True)    
    return prophet_data

def forecast_now(data, forecast_this_feature, train_window, forecasted_horizon):
    """
    Forecast a time series feature using Facebook Prophet.

    Args:
        data (pd.DataFrame): The input time series data.
        forecast_this_feature (str): The name of the feature to forecast.
        train_window (int): The number of hours in the training window.
        forecasted_horizon (int): The number of hours to forecast into the future.

    Returns:
        pd.DataFrame: Forecasted data including timestamps and forecasted values.
    """
    # Preprocess the data for Prophet
    prophet_train = prophet_preprocessor(data,forecast_this_feature)        
    # Create a Prophet model with specified parameters
    model = Prophet(
                        growth="linear",
                        seasonality_mode="multiplicative",
                            daily_seasonality=True,
                            weekly_seasonality=False,
                            yearly_seasonality=False,
                            changepoint_prior_scale=0.05,
                            seasonality_prior_scale=10,
                            holidays_prior_scale=10,
                            mcmc_samples=0,
                        )
    # Add hourly seasonality to the model
    model.add_seasonality(
                            name="hourly",
                            period=train_window,
                            fourier_order=10
                        )
    # Fit the Prophet model to the training data
    model.fit(prophet_train)
    # Create a future dataframe for forecasting
    future = model.make_future_dataframe(periods=forecasted_horizon, freq="H")
    # Generate forecasts using the trained model
    forecast = model.predict(future)
    # Prepare the result data by selecting relevant columns and renaming them
    result_data = pd.DataFrame()
    forecast = forecast[-forecasted_horizon:]
    forecast['y'] = forecast['yhat'].values
    forecast = forecast[['ds','y']]
    # Concatenate the original training data with the forecasted data
    result_data = pd.concat([prophet_train,forecast])
    return result_data

def multiple_feature_forecasting(data, feature_list, train_window, forecasted_horizon):
    """
    Perform forecasting for multiple features using Facebook Prophet.

    Args:
        data (pd.DataFrame): The input time series data.
        feature_list (list): List of features to forecast.
        train_window (int): The number of hours in the training window.
        forecasted_horizon (int): The number of hours to forecast into the future.

    Returns:
        pd.DataFrame: Forecasted data including timestamps, feature values, Sensor ID, and index.
    """
    result = {}
    # Determine the maximum Sensor ID for the result
    sensor_value = data['Sensor ID'].max()
    # Iterate through each feature in the feature list
    for feature in feature_list:
        # Perform forecasting for the current feature
        tempdf = forecast_now(data, feature, train_window, forecasted_horizon)
        # Store the forecasted values in the result dictionary
        result['Date'] = tempdf.ds
        result[feature] = tempdf.y
    # Create a DataFrame from the result dictionary
    result_df = pd.DataFrame(result)
    # Add the Sensor ID and index columns to the result DataFrame    
    result_df['Sensor ID'] = sensor_value
    result_df['H'] = result_df.index.values
    # Round the values in the DataFrame to 2 decimal places
    result_df = result_df.round(2)
    return result_df