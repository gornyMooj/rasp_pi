'''
- pandas script:
    - reads data from bme280
    - saves data every minute to csv
    - saves data every hour to csv + data from API
    - saves seprete files every 24hours
    - uploads data to TS - https://thingspeak.com/

- future improvements:
    - when there is no internet access, upload, wait and upload data when there is access
    - send email that there was no internet

'''
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import requests
import pprint
import time
import urllib

import board
from adafruit_bme280 import basic as adafruit_bme280

i2c = board.I2C()  # uses board.SCL and board.SDA
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

# creates the output directory if doesnt exist
out_folder = 'outputs_bme280'
out_path = os.path.join(os.getcwd(), out_folder)
if not os.path.exists(out_path):
    os.makedirs(out_path)

out_miute = pd.DataFrame(columns=['date', 'temp', 'humidity', 'pressure', 'altitude'])
out_hour = pd.DataFrame(columns=['date', 'hour', 'temp', 'humidity', 'pressure', 'altitude'])
out_api_data = pd.DataFrame(columns=['date', 'outside_temp', 'outside_humidity', 'winnd_speed'])


minute = datetime.now().minute
hour = datetime.now().hour
date = datetime.now().date()

minutes_file = datetime.now().strftime("%Y%m%d%H%M%S") + "_minutes.csv"
hour_file = datetime.now().strftime("%Y%m%d%H%M%S") + "_hours.csv"
api_file = datetime.now().strftime("%Y%m%d%H%M%S") + "_api.csv"


def get_data_weather_api():
    '''
    free api up to 10 000 requests per day
    '''
    url = f"https://api.open-meteo.com/v1/forecast?latitude=53.45&longitude=19.95&current=temperature_2m,,relative_humidity_2m,wind_speed_10m"
    response = requests.get(url)
    response = response.json()

    outside_temp = response['current']['temperature_2m']  # °C
    outside_humidity = response['current']['relative_humidity_2m']  # %
    winnd_speed = response['current']['wind_speed_10m']  # km/h

    return [outside_temp, outside_humidity, winnd_speed]


print(f'\n..stated at {datetime.now()}')


def upload_data_ts(temp, humidity, outside_temp, outside_humidity, winnd_speed):
    '''
    - uploads data to ThingSpeak;  can upload data wevery 20s
    '''
    params = urllib.parse.urlencode({
        'key': 'YOUR-KEY-TO-TS', 
        'field1': temp,
        'field2': humidity,
        'field3': outside_temp,
        'field4': outside_humidity,
        'field5': winnd_speed

    }).encode("utf-8")

    with urllib.request.urlopen("https://api.thingspeak.com/update", data=params) as ts:
        upload = ts.read()
        print(f'\nData uploaded to ThingSpeak at {datetime.now()} with this:  {upload}')
        
        

# CORE OF THE PROGRAM WITH ENDLESS LOOP
try:
    while True:
        temp = bme280.temperature
        humidity = bme280.relative_humidity
        pressure = bme280.pressure
        altitude = bme280.altitude
        # adding data to the dataframe
        out_miute.loc[len(out_miute.index)] = [datetime.now(), temp, humidity, pressure, altitude]

        print('\nSensor', list(out_miute.columns))
        print('Sensor: ', [datetime.now().strftime("%Y %m %d %H:%M:%S"), temp, humidity, pressure, altitude])

        # if the hour changes then the mean from previouse hour is saved
        if datetime.now().hour > hour:
            # select readings from previouse 10 min
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=10)
            selected_rows = out_miute[(out_miute['date'] >= start_time) & (out_miute['date'] <= end_time)]
            mean = selected_rows.mean()
            # adds means to out_hour
            out_hour.loc[len(out_hour.index)] = [datetime.now(), datetime.now().hour, mean['temp'], mean['humidity'],
                                                 mean['pressure'], mean['altitude']]

            response = get_data_weather_api()
            api_data = [datetime.now()] + response
            out_api_data.loc[len(out_api_data.index)] = api_data

            print('\nAPI', list(out_api_data.columns))
            print('API: ', api_data)

            # saving dataframes
            out_miute.to_csv(os.path.join(out_path, minutes_file), index=False)
            out_hour.to_csv(os.path.join(out_path, hour_file), index=False)
            out_api_data.to_csv(os.path.join(out_path, api_file), index=False)
            
            # uploading data to ThingSpeak
            try:
                upload_data_ts(mean['temp'], mean['humidity'], response[0], response[1], response[2])
            except:
                print('\nCould not send data to ThingSpeak!  buuuu.. ')

        # if the date changes then the mean is calculated + a new csv is created for minutes data
        if datetime.now().date() > date:
            # saving mean data for readings between 23:50 and 00:00
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=10)
            selected_rows = out_miute[(out_miute['date'] >= start_time) & (out_miute['date'] <= end_time)]
            mean = selected_rows.mean()
            # saves means to out_hour
            out_hour.loc[len(out_hour.index)] = [datetime.now(), datetime.now().hour, mean['temp'], mean['humidity'],
                                                 mean['pressure'], mean['altitude']]
            # Ssave data from api for 00:00
            response = get_data_weather_api()
            api_data = [datetime.now()] + response
            out_api_data.loc[len(out_api_data.index)] = api_data

            # saving data
            out_miute.to_csv(os.path.join(out_path, minutes_file), index=False)
            out_hour.to_csv(os.path.join(out_path, hour_file), index=False)
            out_api_data.to_csv(os.path.join(out_path, api_file), index=False)
            # clearing dataframes
            out_miute = pd.DataFrame(columns=['date', 'temp', 'humidity', 'pressure', 'altitude'])
            out_hour = pd.DataFrame(columns=['date', 'hour', 'temp', 'humidity', 'pressure', 'altitude'])
            out_api_data = pd.DataFrame(columns=['date', 'outside_temp', 'outside_humidity', 'winnd_speed'])
            # generating new names for the files
            minutes_file = datetime.now().strftime("%Y%m%d%H%M%S") + "_minutes.csv"
            hour_file = datetime.now().strftime("%Y%m%d%H%M%S") + "_hours.csv"
            api_file = datetime.now().strftime("%Y%m%d%H%M%S") + "_api.csv"

        minute = datetime.now().minute
        hour = datetime.now().hour
        date = datetime.now().date()

        time.sleep(60)

except KeyboardInterrupt:
    print("\nProgram interrupted by user. Closing gracefully.")


finally:
    # saving data
    out_miute.to_csv(os.path.join(out_path, minutes_file), index=False)
    out_hour.to_csv(os.path.join(out_path, hour_file), index=False)
    out_api_data.to_csv(os.path.join(out_path, api_file), index=False)

