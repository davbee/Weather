import os
from datetime import datetime, timezone
from time import sleep

import pytz
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize TimezoneFinder and Geolocator
tf = TimezoneFinder()
geolocator = Nominatim(user_agent="weather_app", timeout=10)

# OpenWeather API key
OPENWEATHER_API_KEY = os.getenv("OWAPIKEY")

# OpenWeather API endpoint
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


# Function to fetch real-time weather data from OpenWeather
def fetch_weather_data(city, state, country):
    params = {
        "q": f"{city},{state},{country}",
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",  # Use Celsius
    }
    try:
        response = requests.get(
            OPENWEATHER_URL, params=params, timeout=10
        )  # Set timeout to 10 seconds
        if response.status_code == 200:
            data = response.json()
            return {
                "fetch_timestamp": datetime.now(tz=timezone.utc).isoformat() + "Z",
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "conditions": data["weather"][0]["description"],
            }
        else:
            print(f"Failed to fetch weather data: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        print(f"Request to OpenWeather API timed out for {city}, {state}, {country}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def retry_geocode(location_query, retries=3, delay=5):
    for attempt in range(retries):
        try:
            location = geolocator.geocode(location_query)
            if location:
                return location
        except Exception as e:
            print(f"Geocoding attempt {attempt + 1} failed: {e}")
            sleep(delay)
    return None


@app.route("/api/weather/all", methods=["GET", "POST"])
def get_all_weather_data():
    # Define locations with city, state, country, and timezone
    locations = {
        "berkeley": ("Berkeley", "CA", "US", "America/Los_Angeles"),
        "milpitas": ("Milpitas", "CA", "US", "America/Los_Angeles"),
        "san jose": ("San Jose", "CA", "US", "America/Los_Angeles"),
        "seattle": ("Seattle", "WA", "US", "America/Los_Angeles"),
        "delta": ("Delta", "BC", "Canada", "America/Vancouver"),
        "kelowna": ("Kelowna", "BC", "Canada", "America/Vancouver"),
        "hangzhou": ("Hangzhou", "Zhejiang", "China", "Asia/Shanghai"),
        "shanghai": ("Shanghai", "Shanghai", "China", "Asia/Shanghai"),
    }

    # Fetch weather data for all locations
    weather_data = []
    for location, (city, state, country, timezone) in locations.items():
        weather = fetch_weather_data(city, state, country)
        if weather:
            local_time = datetime.now(pytz.timezone(timezone)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            weather_data.append(
                {
                    "fetch_timestamp": weather["fetch_timestamp"],
                    "local_time": local_time,
                    "city": city.title(),
                    "state": state.upper(),
                    "country": country.upper(),
                    "temperature": f"{weather['temperature']:.1f}",
                    "humidity": weather["humidity"],
                    "conditions": weather["conditions"],
                }
            )

    # Handle new location input from the user
    if request.method == "POST":
        new_location = request.form.get("location", "").strip()
        if new_location:
            try:
                city, state, country = new_location.split(",")
                city, state, country = city.strip(), state.strip(), country.strip()
                weather = fetch_weather_data(city, state, country)
                if weather:
                    location_query = f"{city}, {state}, {country}"
                    location = retry_geocode(location_query)
                    if location:
                        timezone = tf.timezone_at(
                            lng=location.longitude, lat=location.latitude
                        )
                        if not timezone:
                            timezone = "UTC"
                        local_time = datetime.now(pytz.timezone(timezone)).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        weather_data.append(
                            {
                                "fetch_timestamp": weather["fetch_timestamp"],
                                "local_time": local_time,
                                "city": city.title(),
                                "state": state.upper(),
                                "country": country.upper(),
                                "temperature": f"{weather['temperature']:.1f}",
                                "humidity": weather["humidity"],
                                "conditions": weather["conditions"],
                            }
                        )
                        # Sort the data after inserting the new location
                        weather_data.sort(
                            key=lambda x: (x["country"], x["state"], x["city"])
                        )
            except ValueError:
                print(f"Invalid location format: {new_location}")

    # Sort data by country, then state, then city (in case no new data was added)
    weather_data.sort(key=lambda x: (x["country"], x["state"], x["city"]))

    # Generate HTML table
    table_rows = ""
    for data in weather_data:
        table_rows += f"""
        <tr>
            <td>{data['fetch_timestamp']}</td>
            <td>{data['local_time']}</td>
            <td>{data['city']}</td>
            <td>{data['state']}</td>
            <td>{data['country']}</td>
            <td>{data['temperature']}°C</td>
            <td>{data['humidity']}%</td>
            <td>{data['conditions'].title()}</td>
        </tr>
        """

    html_table = f"""
    <html>
        <head>
            <title>Weather Data</title>
            <style>
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    table-layout: auto; /* Auto-fit column width */
                }}
                th, td {{
                    border: 1px solid black;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
            </style>
        </head>
        <body>
            <h1>Weather Data for All Locations</h1>
            <form method="POST">
                <label for="location">Enter a new location (City, State, Country):</label>
                <input type="text" id="location" name="location" required>
                <button type="submit">Add Location</button>
            </form>
            <table>
                <tr>
                    <th>Fetch Time (UTC)</th>
                    <th>Local Time</th>
                    <th>City</th>
                    <th>State</th>
                    <th>Country</th>
                    <th>Temperature (°C)</th>
                    <th>Humidity (%)</th>
                    <th>Conditions</th>
                </tr>
                {table_rows}
            </table>
        </body>
    </html>
    """

    return html_table


if __name__ == "__main__":
    app.run(debug=True, port=5000)
