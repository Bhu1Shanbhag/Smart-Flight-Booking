import json
import random

class WeatherService:
    """
    A simple deterministic utility service to get weather information.
    In a production system, this would call an external API like Open-Meteo.
    """
    
    @staticmethod
    def get_weather_forecast(location: str, date: str) -> dict:
        """
        Retrieves the weather forecast for a given location and date.
        """
        # Mock implementation
        conditions = ["Sunny", "Rain", "Snow", "Cloudy", "Clear"]
        # Use location length to make it deterministic for testing
        idx = (len(location) + len(date)) % len(conditions)
        condition = conditions[idx]
        
        # If Rain or Snow, suggest adding buffer time
        needs_buffer = condition in ["Rain", "Snow"]
        buffer_minutes = 30 if needs_buffer else 0
        
        return {
            "location": location,
            "date": date,
            "condition": condition,
            "temperature_celsius": 22 - (10 if condition == "Snow" else 0),
            "travel_buffer_minutes_recommended": buffer_minutes,
            "advisory": f"Expect {condition.lower()} conditions. Added {buffer_minutes} mins buffer." if needs_buffer else "Normal travel conditions."
        }
