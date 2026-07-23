import os
from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv

from services.weather_service import WeatherService
from agents.travel_planning_agent import TravelPlanningAgent
from agents.user_proxy_agent import UserProxyAgent
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.orchestrator_agent import OrchestratorAgent

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize singletons
load_dotenv()
weather_service = WeatherService()
planning_agent = TravelPlanningAgent(weather_service=weather_service)
proxy_agent = UserProxyAgent()
flight_agent = FlightAgent()
hotel_agent = HotelAgent()

orchestrator = OrchestratorAgent(
    planning_agent=planning_agent,
    proxy_agent=proxy_agent,
    flight_agent=flight_agent,
    hotel_agent=hotel_agent
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/plan', methods=['POST'])
def plan():
    data = request.json
    # Format incoming data
    current_request = {
        "origin_city": data.get("origin_city", "Mumbai"),
        "origin_loc": data.get("origin_loc", "Mumbai"),
        "destination_city": data.get("destination_city", "Delhi"),
        "destination_loc": data.get("destination_loc", "Delhi"),
        "date": data.get("date", "2026-07-29"),
        "meeting_time": data.get("meeting_time", "11:00 AM"),
        "return_required": data.get("return_required", True)
    }
    
    session['current_request'] = current_request
    
    # Generate initial strategy
    strategy = orchestrator.generate_strategy(current_request)
    session['strategy'] = strategy
    
    return jsonify({"strategy": strategy})

@app.route('/api/feedback', methods=['POST'])
def feedback():
    data = request.json
    user_input = data.get("feedback", "")
    strategy = session.get('strategy', {})
    current_request = session.get('current_request', {})
    
    feedback_res = orchestrator.process_feedback(strategy, user_input)
    
    if feedback_res["status"] == "approved":
        return jsonify({"status": "approved", "strategy": strategy})
    else:
        # Update constraints and re-plan
        current_request.update(feedback_res["new_constraints"])
        session['current_request'] = current_request
        new_strategy = orchestrator.generate_strategy(current_request)
        session['strategy'] = new_strategy
        return jsonify({"status": "modified", "strategy": new_strategy})

@app.route('/api/duration', methods=['POST'])
def duration():
    data = request.json
    try:
        meeting_hours = float(data.get("meeting_hours", 2))
    except (ValueError, TypeError):
        meeting_hours = 2.0
        
    strategy = session.get('strategy', {})
    current_request = session.get('current_request', {})
    
    if strategy.get("return_required"):
        strategy = orchestrator.calculate_return_date(current_request, strategy, meeting_hours)
        session['strategy'] = strategy
        
    return jsonify({"status": "ready", "strategy": strategy})

@app.route('/api/book', methods=['POST'])
def book():
    strategy = session.get('strategy', {})
    if not strategy:
        return jsonify({"error": "No active strategy found"}), 400
        
    itinerary = orchestrator.execute_bookings(strategy)
    return jsonify({"itinerary": itinerary})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
