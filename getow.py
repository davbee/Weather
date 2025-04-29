# filepath: [weather.py](http://_vscodecontentref_/1)
import os
from datetime import datetime

import pytz  # Add this import for timezone handling
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Load environment variables
load_dotenv()

app = Flask(__name__)

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
                "fetch_timestamp": datetime.utcnow().isoformat()
                + "Z",  # Add UTC timestamp
                "temperature": data["main"]["temp"],
                "conditions": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
            }
        else:
            return None
    except requests.exceptions.Timeout:
        print(f"Request to OpenWeather API timed out for {
            city}, {state}, {country}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


@app.route("/api/weather/current", methods=["GET"])
def get_current_weather():
    location = request.args.get("location", "").lower()

    # Supported locations
    supported_locations = {
        "berkeley": ("Berkeley", "CA", "US"),
        "milpitas": ("Milpitas", "CA", "US"),
        "san jose": ("San Jose", "CA", "US"),
        "seattle": ("Seattle", "WA", "US"),
        "delta": ("Delta", "BC", "Canada"),
        "kelowna": ("Kelowna", "BC", "Canada"),
        "hangzhou": ("Hangzhou", "Zhejiang", "China"),
        "shanghai": ("Shanghai", "Shanghai", "China"),
    }

    if location not in supported_locations:
        return jsonify({"error": "Location not supported"}), 404

    city, state, *country = supported_locations[location]
    # Default to US if no country is provided
    country = country[0] if country else "US"
    weather = fetch_weather_data(city, state, country)

    if not weather:
        return jsonify({"error": "Failed to fetch weather data"}), 500

    return jsonify(
        {
            "location": location,
            "current": weather,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/weather/all", methods=["GET"])
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
                    "fetch_timestamp": weather[
                        "fetch_timestamp"
                    ],  # Include fetch timestamp
                    "local_time": local_time,  # Include local time
                    "city": city,
                    "state": state,
                    "country": country,
                    "temperature": f"{weather['temperature']:.1f}",
                    "humidity": weather["humidity"],
                    "conditions": weather["conditions"],
                }
            )

    # Sort data by country, then state, then city
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
