# main.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh
import base64
import os

# ==================== SETTINGS ====================
REFRESH_RATE = 30  # Data refresh rate in seconds

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(page_title="Dashboard", layout="wide")  # Must be first Streamlit command

# ==================== CUSTOM CSS ====================
st.markdown(
    """
    <style>
    /* Overall Background */
    body {
        background-color: #121212;
        color: #e0e0e0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Header Styling */
    .header {
        text-align: center;
        padding: 0px 0;
        font-size: 40px;
        font-weight: bold;
        color: #ffffff;
    }

    /* Container Styling */
    .location-container {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        transition: transform 0.2s;
    }

    .location-container:hover {
        transform: scale(1.02);
    }

    /* Metric Titles */
    .metric-title {
        font-size: 20px;
        color: #b0b0b0;
        margin-bottom: 5px;
    }

    /* Metric Values */
    .metric-value {
        font-size: 18px;
        color: #ffffff;
        font-weight: bold;
        display: flex;
        align-items: center;
    }

    /* Icon Styling */
    .metric-icon {
        margin-right: 8px;
        font-size: 20px;
    }

    /* Trend Graph Styling */
    .trend-graph {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .location-container {
            padding: 15px;
        }
        .metric-value {
            font-size: 18px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==================== DIRECTORY SETUP ====================
# Directory to store trend images
TREND_GRAPH_DIR = "trend_graphs"
os.makedirs(TREND_GRAPH_DIR, exist_ok=True)

# ==================== INITIALIZE SESSION STATE ====================
if 'price_history' not in st.session_state:
    st.session_state.price_history = {"PHR": [], "Wharton": [], "Ector": []}

# Initialize previous LMP for tracking changes
if 'previous_lmp' not in st.session_state:
    st.session_state.previous_lmp = {"PHR": None, "Wharton": None, "Ector": None}

# ==================== USER CREDENTIALS ====================
# Define user credentials
#USER_CREDENTIALS = {
 #   "Austin": "BeetsandBeans",
  #  "Alonzo": "BeetsandBeans"
#}

# ==================== LOGIN FUNCTION ====================
#def logout():
#    """Logs out the user by resetting session state."""
 #   st.session_state.logged_in = False
  #  st.session_state.username = ""
   # st.experimental_rerun()

#def login():
#    """Displays the login form and handles authentication."""
 #   st.markdown("<div class='header'>Login to Energy Dashboard</div>", unsafe_allow_html=True)

    # Initialize session state for login if not already done
  #  if 'logged_in' not in st.session_state:
   #     st.session_state.logged_in = False
    #    st.session_state.username = ""

   # if not st.session_state.logged_in:
   #    with st.form("login_form"):
    #        username = st.text_input("Username")
     #       password = st.text_input("Password", type="password")
      #      submit = st.form_submit_button("Login")

       # if submit:
        #    if username in USER_CREDENTIALS and password == USER_CREDENTIALS[username]:
         #       st.session_state.logged_in = True
          #      st.session_state.username = username
           #     st.success(f"Welcome, {username}!")
            #    st.experimental_rerun()  # Force rerun to display dashboard immediately
            #else:
           #     st.error("Invalid username or password.")

  #  if st.session_state.logged_in:
   #     st.sidebar.button("Logout", on_click=logout)

# ==================== SETTINGS ====================
API_URL = "https://api.tomorrow.io/v4/weather/forecast"
API_KEY = "ELbbfN1OHWLyHjTuQ6afA87WjgMw2r4D"  # Replace with your actual API key
LOCATIONS = {
    "PHR": "29.5066,-94.9927",      # Coordinates for Bacliff
    "Wharton": "29.5066,-95.7321",  # Coordinates for Newgulf/Wharton
    "Ector": "31.9951,-102.6157"    # Coordinates for Goldsmith
}

# ==================== WEATHER FETCH FUNCTION ====================
def fetch_weather_tomorrow(location):
    """
    Fetch weather data from Tomorrow.io API for a specific location.
    """
    coordinates = LOCATIONS[location]
    try:
        response = requests.get(
            API_URL,
            params={
                "location": coordinates,
                "apikey": API_KEY,
                "timesteps": "1d",
                "units": "imperial"  # Fetch data in Fahrenheit
            },
            timeout=10
        )
        response.raise_for_status()
        weather_data = response.json()
        
        # Extract relevant weather information
        forecast = weather_data.get("timelines", {}).get("daily", [])[0]
        temperature = forecast["values"]["temperatureAvg"]
        condition_code = forecast["values"]["weatherCode"]
        precipitation = forecast["values"].get("precipitationProbability", "N/A")
        condition_icon = get_condition_icon(condition_code)

        return {
            "Temperature": f"{temperature} °F",
            "Condition": condition_icon,
            "Precipitation": f"{precipitation}%"
        }
    except Exception as e:
        st.warning(f"Error fetching weather for {location}: {e}")
        return {"Temperature": "N/A", "Condition": "N/A", "Precipitation": "N/A"}

# ==================== CONDITION ICON FUNCTION (UPDATED) ====================
def get_condition_icon(condition_code):
    """
    Map Tomorrow.io condition codes to icons.
    """
    condition_code = str(condition_code).lower()
    if "rain" in condition_code or "drizzle" in condition_code:
        return "🌧️"
    elif "snow" in condition_code:
        return "❄️"
    elif "clear" in condition_code or "sunny" in condition_code:
        return "☀️"
    elif "cloud" in condition_code:
        return "☁️"
    elif "storm" in condition_code or "thunder" in condition_code:
        return "⛈️"
    elif "mist" in condition_code or "fog" in condition_code or "haze" in condition_code:
        return "🌫️"
    else:
        return ""  # Default/fallback icon


# ==================== PRICE FETCHING FUNCTION ====================
def fetch_price(location):
    """Fetch the price for a specific location."""
    url_map = {
        "PHR": "https://www.ercot.com/content/cdr/html/current_np6788.html",
        "Wharton": "https://www.ercot.com/content/cdr/html/current_np6788.html",
        "Ector": "https://www.ercot.com/content/cdr/html/current_np6788.html"
    }
    identifier_map = {
        "PHR": "BAC_RN_ALL",
        "Wharton": "TGS_GT01",
        "Ector": "RN_ECEC_HOLT"
    }

    try:
        # Get the correct URL and identifier for the location
        url = url_map.get(location, "")
        identifier = identifier_map.get(location, "")

        if not url or not identifier:
            st.warning(f"URL or identifier missing for {location}.")
            return None

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Scrape price data from the table
        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all("td", class_="tdLeft")
            if cells and cells[0].text.strip() == identifier:
                price_text = cells[3].text.strip().replace(',', '')
                try:
                    price = float(price_text)
                    return price
                except ValueError:
                    st.warning(f"Invalid price format for {location}: {price_text}")
        st.warning(f"No price data found for {location}.")
    except Exception as e:
        st.warning(f"Error fetching price for {location}: {e}")
    return None  # Return None to indicate missing data

# ==================== LMP FETCHING FUNCTION ====================
def fetch_lmp(location):
    """Fetch the LMP value for a given location."""
    url = "https://www.ercot.com/content/cdr/html/current_np6788.html"
    identifier_map = {
        "PHR": "BAC_RN_ALL",
        "Wharton": "TGS_GT01",
        "Ector": "RN_ECEC_HOLT"
    }

    try:
        identifier = identifier_map.get(location, "")
        if not identifier:
            raise ValueError(f"Unknown location: {location}")

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all("td", class_="tdLeft")
            if cells and cells[0].text.strip() == identifier:
                lmp = cells[1].text.strip()  # Extract the LMP value
                try:
                    return float(lmp)
                except ValueError:
                    st.warning(f"Invalid LMP format for {location}: {lmp}")
        st.warning(f"No LMP data found for {location}.")
    except Exception as e:
        st.warning(f"Error fetching LMP for {location}: {e}")
    return 0.0

# ==================== TREND GRAPH CREATION ====================
def create_trend_graph(location, price_history):
    """
    Create a trend graph image for the given location and return as file path.

    Args:
        location (str): The name of the location (e.g., "PHR", "Wharton").
        price_history (list): A list of tuples containing (timestamp, price).
                              Example: [(datetime1, 25.0), (datetime2, 30.0), ...]

    Returns:
        str: The file path to the generated graph image, or None if not enough data.
    """
    # Create a copy of price_history to avoid modifying the session state
    price_history_copy = price_history.copy()

    # Limit to the last 10 points
    price_history_copy = price_history_copy[-10:]

    # Pad with placeholders if fewer than 10 points
    while len(price_history_copy) < 10:
        last_timestamp = price_history_copy[0][0] if price_history_copy else datetime.now()
        price_history_copy.insert(0, (last_timestamp - timedelta(minutes=1), 0.0))

    # Extract timestamps and prices
    timestamps, prices = zip(*price_history_copy)

    # Check if there's enough data to draw a graph
    if len(prices) < 2:
        return None

    # Set the figure size to match the fixed label size (e.g., 150x75 pixels at 100 DPI)
    plt.figure(figsize=(1.5, 0.75), dpi=100)

    # Plot the trend as a continuous line
    plt.plot(range(len(prices)), prices, color="red", linewidth=2, marker='o', markersize=0)

    # Highlight upward and downward trends
    for i in range(1, len(prices)):
        color = "green" if prices[i] > prices[i - 1] else "red"
        plt.plot([i - 1, i], [prices[i - 1], prices[i]], color=color, linewidth=2)

    # Hide axes and add grid for clarity
    plt.axis("off")
    plt.tight_layout()

    # Save the graph with a transparent background
    graph_path = os.path.join(TREND_GRAPH_DIR, f"{location}_trend.png")
    plt.savefig(graph_path, bbox_inches="tight", pad_inches=0, transparent=True)
    plt.close()

    return graph_path

def fetch_and_update_data(selected_locations):
    current_time = datetime.now()
    one_hour_ago = current_time - timedelta(hours=1)

    data = {}

    for location in selected_locations:
        # Fetch weather data using Tomorrow.io API
        weather_data = fetch_weather_tomorrow(location)
        temp = weather_data["Temperature"]
        cond = weather_data["Condition"]

        # Fetch current price
        current_price = fetch_price(location)

        if current_price is None:
            st.warning(f"Skipping graph generation for {location} due to missing price data.")
            data[location] = {
                "Price": "0.0",
                "Change": "N/A",
                "Change_Color": "#ffffff",
                "Temperature": "N/A",
                "Condition": "N/A",
                "LMP": "N/A",
                "LMP_Color": "#ffffff",
                "Adder": "0.0",
                "Adder_Color": "#ffffff",
                "Trend_Graph_Path": None
            }
            continue

        # Fetch LMP value
        lmp = fetch_lmp(location)

        # Append to price history
        st.session_state.price_history[location].append(
            (current_time, current_price)
        )

        # Keep only data from the last hour
        st.session_state.price_history[location] = [
            (timestamp, price)
            for timestamp, price in st.session_state.price_history[location]
            if timestamp > one_hour_ago
        ]

        # Limit to the last 10 data points
        st.session_state.price_history[location] = st.session_state.price_history[location][-10:]

        # Calculate percentage change
        if len(st.session_state.price_history[location]) > 1:
            initial_price = st.session_state.price_history[location][0][1]
            percent_change = ((current_price - initial_price) / initial_price) * 100 if initial_price else 0.0
        else:
            percent_change = 0.0

        # Determine arrow and color for price change
        arrow = "↑" if percent_change > 0 else ("↓" if percent_change < 0 else "")
        color = "#00e676" if percent_change > 0 else ("#ff1744" if percent_change < 0 else "#ffffff")  # green/red/white

        # Fetch previous LMP to determine change
        previous_lmp = st.session_state.previous_lmp.get(location)
        st.session_state.previous_lmp[location] = lmp

        # Calculate LMP change
        if previous_lmp is not None:
            lmp_change = lmp - previous_lmp
            if lmp_change > 0:
                lmp_arrow = "↑"
                lmp_color = "#00e676"  # Green for increase
            elif lmp_change < 0:
                lmp_arrow = "↓"
                lmp_color = "#ff1744"  # Red for decrease
            else:
                lmp_arrow = ""
                lmp_color = "#ffffff"  # White for no change
        else:
            lmp_arrow = ""
            lmp_color = "#ffffff"

        # Calculate Adder (Price - LMP)
        adder = current_price - lmp
        if adder < 0:
            adder = 0.0

        # Determine color and arrow for Adder
        adder_color = "#00e676" if adder > 0 else "#ffffff"
        adder_arrow = "+" if adder > 0 else ""

        # Create trend graph
        graph_path = create_trend_graph(location, st.session_state.price_history[location])

        # Assign data
        data[location] = {
            "Price": f"{current_price:.2f}",
            "Change": f"{percent_change:+.2f}% {arrow}",
            "Change_Color": color,
            "Temperature": f"🌡️ {temp}",
            "Condition": f"{cond}",
            "LMP": f"${lmp:.2f} {lmp_arrow}",
            "LMP_Color": lmp_color,
            "Adder": f"${adder:.2f} {adder_arrow}" if adder != 0 else "0.0",
            "Adder_Color": adder_color,
            "Trend_Graph_Path": graph_path
        }

    return data


# ==================== DASHBOARD ====================
def dashboard():
    """Displays the Dashboard."""
    st.markdown("<div class='header'>Dashboard</div>", unsafe_allow_html=True)

    # Sidebar for user selections
    st.sidebar.title("Settings")

    # User Selection for Locations
    selected_locations = st.sidebar.multiselect(
        "Select Locations",
        options=["PHR", "Wharton", "Ector"],
        default=["PHR", "Wharton", "Ector"]
    )

    # Adjust Refresh Rate
    new_refresh_rate = st.sidebar.slider(
        "Refresh Rate (seconds)",
        min_value=30,
        max_value=60,
        value=30,
        step=5
    )

    # Update REFRESH_RATE based on user input
    global REFRESH_RATE
    REFRESH_RATE = new_refresh_rate

    # Auto-refresh the app every REFRESH_RATE seconds
    st_autorefresh(interval=REFRESH_RATE * 1000, key="autorefresh")  # Corrected interval

    # Fetch and update data
    data = fetch_and_update_data(selected_locations)

    for location, info in data.items():
        # Create a styled container for each location
        if info["Trend_Graph_Path"] and os.path.exists(info["Trend_Graph_Path"]):
            img_path = info["Trend_Graph_Path"]
            # Read the image and encode it to base64
            with open(img_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode()
            img_html = f'<img src="data:image/png;base64,{encoded_image}" class="trend-graph"/>'
        else:
            img_html = 'Graph will appear after data is available.'

        st.markdown(f"""
        <div class="location-container">
            <h2 style="color: #ffffff;">{location}</h2>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 150px; padding: 10px;">
                    <div class="metric-title">Price</div>
                    <div class="metric-value">${info["Price"]}</div>
                </div>
                <div style="flex: 1; min-width: 150px; padding: 10px;">
                    <div class="metric-title">Change</div>
                    <div class="metric-value" style="color: {info['Change_Color']};">{info["Change"]}</div>
                </div>
                <div style="flex: 1; min-width: 150px; padding: 10px;">
                    <div class="metric-title">Temperature</div>
                    <div class="metric-value">{info["Temperature"]}</div>
                </div>
                <div style="flex: 1; min-width: 150px; padding: 10px;">
                    <div class="metric-title">Condition</div>
                    <div class="metric-value">{info["Condition"]}</div>
                </div>
                <div style="flex: 1; min-width: 150px; padding: 10px;">
                    <div class="metric-title">LMP</div>
                    <div class="metric-value" style="color: {info['LMP_Color']};">💰{info["LMP"]}</div>
                </div>
                <div style="flex: 1; min-width: 150px; padding: 10px;">
                    <div class="metric-title">Adder</div>
                    <div class="metric-value" style="color: {info['Adder_Color']};">{info["Adder"]}</div>
                </div>
                <div style="flex: 2; min-width: 250px; padding: 10px;">
                    <div class="metric-title">Trend</div>
                    {img_html}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Optional: Add a footer or additional information
    st.markdown("""
    <div style="text-align: center; padding: 20px; color: #a0a0a0;">
        &copy; 2024 Energy Dashboard. All rights reserved.
    </div>
    """, unsafe_allow_html=True)

# ==================== MAIN FUNCTION ====================
def main():
    # Display the login form
  #  login()

    # If user is logged in, display the dashboard
  #  if st.session_state.logged_in:
        dashboard()

if __name__ == "__main__":
    main()
