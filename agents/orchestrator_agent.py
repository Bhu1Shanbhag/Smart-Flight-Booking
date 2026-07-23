import datetime
from concurrent.futures import ThreadPoolExecutor
from agents.travel_planning_agent import TravelPlanningAgent
from agents.user_proxy_agent import UserProxyAgent
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from services.expense_service import ExpenseService
from services.booking_link_generator import BookingLinkGenerator

class OrchestratorAgent:
    """
    Central controller managing the workflow state and background agent swarm execution.
    """
    
    def __init__(self, planning_agent: TravelPlanningAgent, proxy_agent: UserProxyAgent, 
                 flight_agent: FlightAgent, hotel_agent: HotelAgent):
        self.planning_agent = planning_agent
        self.proxy_agent = proxy_agent
        self.flight_agent = flight_agent
        self.hotel_agent = hotel_agent
        
    def generate_strategy(self, request: dict) -> dict:
        """Step 1: Generate initial or updated strategy based on request/constraints"""
        return self.planning_agent.generate_travel_strategy(request)
        
    def process_feedback(self, strategy: dict, user_input: str) -> dict:
        """Step 2: Process user feedback on the strategy"""
        return self.proxy_agent.process_strategy_feedback(strategy, user_input)
        
    def calculate_return_date(self, current_request: dict, strategy: dict, meeting_hours: float) -> dict:
        """Step 3: Calculate if a return flight is same-day evening or next morning based on meeting duration"""
        meeting_date_str = strategy.get("meeting_date", current_request.get("date"))
        try:
            meeting_date_obj = datetime.datetime.strptime(meeting_date_str, "%Y-%m-%d")
        except Exception:
            meeting_date_obj = datetime.datetime.now()

        try:
            meeting_time = datetime.datetime.strptime(current_request.get("meeting_time", "09:00 AM").strip(), "%I:%M %p").time()
        except ValueError:
            try:
                meeting_time = datetime.datetime.strptime(current_request.get("meeting_time", "09:00").strip(), "%H:%M").time()
            except ValueError:
                meeting_time = datetime.time(9, 0)
            
        meeting_start_dt = datetime.datetime.combine(meeting_date_obj.date(), meeting_time)
        meeting_end_dt = meeting_start_dt + datetime.timedelta(hours=meeting_hours)
        
        # 1 hour buffer + ~60 mins routing to airport + 90 mins check-in
        return_flight_departure_dt = meeting_end_dt + datetime.timedelta(hours=1, minutes=150)
        cutoff_time = datetime.time(22, 0) # 10:00 PM
        
        if return_flight_departure_dt.time() > cutoff_time:
            next_day_obj = meeting_date_obj + datetime.timedelta(days=1)
            strategy["return_date"] = next_day_obj.strftime("%Y-%m-%d")
        else:
            strategy["return_date"] = meeting_date_str
            
        return strategy

    def execute_bookings(self, strategy: dict) -> dict:
        """
        Step 4: Execute real background web surfer agents concurrently for flights and hotels.
        Runs FlightAgent and HotelAgent in parallel background threads.
        """
        print(f"\n[Orchestrator] Launching background Web Surfer agents concurrently for trip to {strategy.get('destination')}...")

        def run_flight():
            return self.flight_agent.find_and_rank_flights(strategy)

        def run_hotel():
            hotel_loc = f"{strategy.get('destination_loc', '')}, {strategy.get('destination_city', '')}".strip(" ,")
            if not hotel_loc:
                hotel_loc = strategy.get("destination", "Mumbai")
            return self.hotel_agent.recommend_hotel(
                location=hotel_loc,
                date=strategy.get("date") # Travel date (day before if staying overnight)
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_flight = executor.submit(run_flight)
            future_hotel = executor.submit(run_hotel)
            
            flight_recommendation = future_flight.result()
            hotel_recommendation = future_hotel.result()

        raw_flight_price = flight_recommendation.get("price")
        try:
            flight_cost = float(raw_flight_price) if raw_flight_price is not None else 0.0
        except (ValueError, TypeError):
            flight_cost = 0.0
            
        raw_hotel_price = hotel_recommendation.get("estimated_cost_per_night") if hotel_recommendation else 0.0
        try:
            hotel_cost = float(raw_hotel_price) if raw_hotel_price is not None else 0.0
        except (ValueError, TypeError):
            hotel_cost = 0.0
            
        estimated_costs = ExpenseService.calculate_estimated_cost(flight_cost, hotel_cost)
        
        flight_link = BookingLinkGenerator.generate_flight_link(
            source=strategy.get("origin", "Origin"),
            destination=strategy.get("destination"),
            date=strategy.get("date")
        )
        
        hotel_link = None
        if hotel_recommendation:
            hotel_link = BookingLinkGenerator.generate_hotel_link(
                location=strategy.get("destination"),
                checkin_date=strategy.get("date"),
                checkout_date=strategy.get("date")
            )
            
        return {
            "strategy": strategy,
            "flight": flight_recommendation,
            "hotel": hotel_recommendation,
            "estimated_costs": estimated_costs,
            "flight_link": flight_link,
            "hotel_link": hotel_link
        }
