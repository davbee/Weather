"""
Weather Data Application
========================

This Flask-based web application fetches and displays real-time weather data
for predefined locations and allows users to add new locations dynamically.
The application integrates with the OpenWeather API to retrieve weather
information and uses geopy for geocoding to fetch latitude and longitude
coordinates for locations.

Features:
---------
1. Displays weather data for a predefined list of locations, including:
   - Local time
   - City, state, and country
   - Coordinates (latitude and longitude)
   - Temperature (in Celsius)
   - Humidity
   - Weather conditions

2. Allows users to add new locations by entering the city, state, and country via a form.

3. Ensures that the weather data table contains unique entries by avoiding duplicate locations.

4. Automatically refreshes weather data for predefined locations when the page is loaded.

5. Sorts the weather data table by country, state, and city for better readability.

Technologies Used:
------------------
- Flask: Web framework for building the application.
- OpenWeather API: To fetch real-time weather data.
- geopy: To perform geocoding and retrieve latitude and longitude for locations.
- pytz: To handle time zones and display local times for locations.

How to Run:
-----------
1. Install the required dependencies:
    pip install flask requests python-dotenv geopy timezonefinder pytz

2. Set up the OpenWeather API key in a `.env` file:
    OWAPIKEY=your_openweather_api_key

3. Run the application:
    python getow.py

4. Open the application in your browser at:
    http://127.0.0.1:5000/api/weather/all

5. View the weather data for predefined locations or add new locations using the form.

"""
# getow.py
# Import necessary libraries
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
                # "fetch_timestamp": datetime.now(tz=timezone.utc).isoformat() + "Z",
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "conditions": data["weather"][0]["description"],
                "latitude": data["coord"]["lat"],  # Extract latitude
                "longitude": data["coord"]["lon"],  # Extract longitude
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


# Global variable to store weather data
weather_data = []


@app.route("/api/weather/all", methods=["GET", "POST"])
def get_all_weather_data():
    global weather_data  # Use the global weather_data list

    # Define locations with city, state, country, and timezone
    locations = {
        "delta": ("Delta", "BC", "Canada", "America/Vancouver"),
        "kelowna": ("Kelowna", "BC", "Canada", "America/Vancouver"),
        "saskatoon": ("Saskatoon", "SA", "Canada", "America/Regina"),
        "beijing": ("Beijing", "Beijing", "China", "Asia/Shanghai"),
        "hangzhou": ("Hangzhou", "Zhejiang", "China", "Asia/Shanghai"),
        "ningbo": ("Ningbo", "Zhejiang", "China", "Asia/Shanghai"),
        "shanghai": ("Shanghai", "Shanghai", "China", "Asia/Shanghai"),
        "shaoxing": ("Shaoxing", "Zhejiang", "China", "Asia/Shanghai"),
        "tokyo": ("Tokyo", "Tokyo", "Japan", "Asia/Tokyo"),
        "berkeley": ("Berkeley", "CA", "US", "America/Los_Angeles"),
        "cronton-on-hudson": ("Cronton-on-Hudson", "NY", "US", "America/New_York"),
        "yonkers": ("Yonkers", "NY", "US", "America/New_York"),
        "cronton": ("Cronton", "NY", "US", "America/New_York"),
        "honolulu": ("Honolulu", "HI", "US", "Pacific/Honolulu"),
        "lynnwood": ("Lynnwood", "WA", "US", "America/los_Angeles"),
        "milpitas": ("Milpitas", "CA", "US", "America/Los_Angeles"),
        "san jose": ("San Jose", "CA", "US", "America/Los_Angeles"),
    }

    # Refresh weather data for predefined locations
    refreshed_data = {}
    for location, (city, state, country, timezone) in locations.items():
        weather = fetch_weather_data(city, state, country)
        if weather:
            location_query = f"{city}, {state}, {country}"
            location = retry_geocode(location_query)
            if location:
                latitude = location.latitude
                longitude = location.longitude
                local_time = datetime.now(pytz.timezone(timezone)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                # Use a unique key (city, state, country) to ensure uniqueness
                key = (city.lower(), state.lower(), country.lower())
                refreshed_data[key] = {
                    # "fetch_timestamp": weather["fetch_timestamp"],
                    "local_time": local_time,
                    "city": city.title(),
                    "state": state.upper(),
                    "country": country.upper(),
                    "coordinates": f"{latitude:.6f}, {longitude:.6f}",  # Add coordinates
                    "temperature": f"{weather['temperature']:.1f}",
                    "humidity": weather["humidity"],
                    "conditions": weather["conditions"],
                }

    # Update the global weather_data list with refreshed data
    weather_data_dict = {
        (entry["city"].lower(), entry["state"].lower(), entry["country"].lower()): entry
        for entry in weather_data
    }
    weather_data_dict.update(refreshed_data)  # Merge refreshed data
    weather_data = list(weather_data_dict.values())  # Convert back to a list

    # Handle new location input from the user
    if request.method == "POST":
        new_location = request.form.get("location", "").strip()
        if new_location:
            try:
                city, state, country = new_location.split(",")
                city, state, country = city.strip(), state.strip(), country.strip()
                # Check if the location already exists in the weather_data list
                key = (city.lower(), state.lower(), country.lower())
                if key not in weather_data_dict:
                    weather = fetch_weather_data(city, state, country)
                    if weather:
                        location_query = f"{city}, {state}, {country}"
                        location = retry_geocode(location_query)
                        if location:
                            latitude = location.latitude
                            longitude = location.longitude
                            timezone = tf.timezone_at(
                                lng=location.longitude, lat=location.latitude
                            )
                            if not timezone:
                                timezone = "UTC"
                            local_time = datetime.now(pytz.timezone(timezone)).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                            # Add the new location's data to the dictionary
                            weather_data_dict[key] = {
                                # "fetch_timestamp": weather["fetch_timestamp"],
                                "local_time": local_time,
                                "city": city.title(),
                                "state": state.upper(),
                                "country": country.upper(),
                                "coordinates": f"{latitude:.6f}, {longitude:.6f}",  # Add coordinates
                                "temperature": f"{weather['temperature']:.1f}",
                                "humidity": weather["humidity"],
                                "conditions": weather["conditions"],
                            }
                            weather_data = list(
                                weather_data_dict.values()
                            )  # Update the list
            except ValueError:
                print(f"Invalid location format: {new_location}")

    # Sort data by country, then state, then city
    weather_data.sort(key=lambda x: (x["country"], x["state"], x["city"]))

    # Generate HTML table
    table_rows = ""
    for data in weather_data:
        table_rows += f"""
        <tr>
            <td>{data['local_time']}</td>
            <td>{data['city']}</td>
            <td>{data['state']}</td>
            <td>{data['country']}</td>
            <td>{data['coordinates']}</td>
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
                    <th>Local Time</th>
                    <th>City</th>
                    <th>State</th>
                    <th>Country</th>
                    <th>Coordinates</th>
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
