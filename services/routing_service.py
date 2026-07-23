import requests
import json
import urllib.parse
from typing import Tuple, Optional

class RoutingService:
    """
    Service to get real-time routing estimates using OpenStreetMap (Nominatim) and OSRM.
    Does not require API keys or credit cards.
    """
    
    @staticmethod
    def get_coordinates(address: str) -> Optional[Tuple[float, float]]:
        """
        Geocodes a string address to (latitude, longitude) using Nominatim.
        """
        if not address:
            return None
            
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address)}&format=json&limit=1"
            headers = {
                # Nominatim requires a user-agent to identify requests
                "User-Agent": "AI-FlightAgent-App/1.0"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return (lat, lon)
        except Exception as e:
            print(f"[RoutingService] Error geocoding '{address}': {e}")
            
        return None

    @staticmethod
    def get_driving_duration_minutes(origin_coords: Tuple[float, float], dest_coords: Tuple[float, float]) -> int:
        """
        Calls OSRM to get the driving time between two coordinates in minutes.
        OSRM expects coordinates as lon,lat.
        """
        try:
            origin_lat, origin_lon = origin_coords
            dest_lat, dest_lon = dest_coords
            
            # OSRM URL format: http://router.project-osrm.org/route/v1/driving/lon,lat;lon,lat
            url = f"http://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "Ok" and data.get("routes"):
                # Duration is in seconds
                duration_seconds = data["routes"][0]["duration"]
                return int(duration_seconds / 60)
                
        except Exception as e:
            print(f"[RoutingService] Error fetching route from OSRM: {e}")
            
        # Realistic fallback instead of fake data: estimate via Haversine and 30 km/h average city speed
        import math
        lat1, lon1 = origin_coords
        lat2, lon2 = dest_coords
        R = 6371.0
        dlon = math.radians(lon2 - lon1)
        dlat = math.radians(lat2 - lat1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = R * c
        driving_hours = distance_km / 30.0
        return max(15, int(driving_hours * 60))

    @staticmethod
    def estimate_flight_duration_minutes(origin_coords: Tuple[float, float], dest_coords: Tuple[float, float]) -> int:
        """
        Estimates flight duration using the Haversine distance formula between two GPS coordinates.
        Assumes an average speed of 800 km/h and a 40-minute overhead for taxi, takeoff, and landing.
        """
        import math
        
        lat1, lon1 = origin_coords
        lat2, lon2 = dest_coords
        
        # Radius of Earth in kilometers
        R = 6371.0
        
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        
        # Haversine formula
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = R * c
        
        # Time = Distance / Speed
        # Speed = 800 km/h
        flight_hours = distance_km / 800.0
        flight_minutes = int(flight_hours * 60)
        
        # Add 40 minutes overhead for taxi, takeoff, approach, and landing
        total_estimated_minutes = flight_minutes + 40
        return total_estimated_minutes
