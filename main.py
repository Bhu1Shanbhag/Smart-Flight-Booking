import os
from dotenv import load_dotenv

# Import Services
from services.weather_service import WeatherService

# Import Plugins
from plugins.web_surfer_plugin import WebSurferPlugin

# Import Agents
from agents.travel_planning_agent import TravelPlanningAgent
from agents.user_proxy_agent import UserProxyAgent
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.orchestrator_agent import OrchestratorAgent

def main():
    print("Initializing AI Corporate Travel Planner System...")
    load_dotenv()
    
    # Initialize Services
    weather_service = WeatherService()
    
    # Initialize Plugins
    web_surfer_plugin = WebSurferPlugin()
    
    # Initialize Agents
    planning_agent = TravelPlanningAgent(weather_service=weather_service)
    proxy_agent = UserProxyAgent()
    flight_agent = FlightAgent(web_surfer_plugin=web_surfer_plugin)
    hotel_agent = HotelAgent(web_surfer_plugin=web_surfer_plugin)
    
    # Initialize Orchestrator
    orchestrator = OrchestratorAgent(
        planning_agent=planning_agent,
        proxy_agent=proxy_agent,
        flight_agent=flight_agent,
        hotel_agent=hotel_agent
    )
    
    # Interactive User Input for Travel Request
    print("\n--- New Travel Request ---")
    origin_city = input("Enter origin city (e.g., Mumbai): ").strip()
    origin_loc = input("Enter specific origin location (e.g., Saxon AI): ").strip()
    dest_city = input("Enter destination city (e.g., Delhi): ").strip()
    dest_loc = input("Enter specific meeting location (e.g., Connaught Place): ").strip()
    date = input("Enter meeting date (YYYY-MM-DD): ").strip()
    meeting_time = ""
    while not meeting_time:
        meeting_time = input("Enter meeting time (e.g., 10:00 AM): ").strip()
        if not meeting_time:
            print("Error: Meeting time is required. Please provide a valid meeting time.")
    return_req_input = input("Is a return flight required? (y/n): ").strip().lower()
    
    initial_request = {
        "origin_city": origin_city if origin_city else "Mumbai",
        "origin_loc": origin_loc if origin_loc else "Andheri East",
        "destination_city": dest_city if dest_city else "Delhi",
        "destination_loc": dest_loc if dest_loc else "Connaught Place",
        "date": date if date else "2023-10-15",
        "meeting_time": meeting_time,
        "return_required": True if return_req_input == 'y' else False
    }
    
    print(f"\n[System] New Travel Request Received: {initial_request}")
    orchestrator.run_workflow(initial_request)

if __name__ == "__main__":
    main()
