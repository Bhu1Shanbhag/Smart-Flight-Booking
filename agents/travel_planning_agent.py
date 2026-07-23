class TravelPlanningAgent:
    """
    Semantic Kernel agent representing the travel planning intelligence of the system.
    """
    
    def __init__(self, weather_service):
        self.weather_service = weather_service
        
    def generate_travel_strategy(self, request_details: dict) -> dict:
        """
        Calculates travel times, evaluates weather, and proposes a strategy.
        If user time constraints (e.g. 'cannot leave before 8am') make same-day arrival impossible
        before the meeting, it schedules travel for the afternoon/evening prior with an overnight hotel stay.
        """
        import datetime
        import re
        from services.routing_service import RoutingService
        
        origin_city = request_details.get("origin_city", "Mumbai")
        origin_loc = request_details.get("origin_loc", "Andheri East")
        dest_city = request_details.get("destination_city", "Delhi")
        dest_loc = request_details.get("destination_loc", "Connaught Place")
        
        meeting_date_str = request_details.get("date", "2026-07-29")
        travel_date_str = meeting_date_str
        meeting_time_str = request_details.get("meeting_time", "09:00 AM")
        
        # Construct search queries
        origin_query = f"{origin_loc}, {origin_city}"
        dest_query = f"{dest_loc}, {dest_city}"
        origin_airport = f"{origin_city} International Airport"
        dest_airport = f"{dest_city} International Airport"
        
        # 1. Fetch weather (using city)
        weather_info = self.weather_service.get_weather_forecast(dest_city, meeting_date_str)
        buffer_mins = weather_info.get("travel_buffer_minutes_recommended", 0)
        
        def get_coords_with_fallback(query, city_fallback):
            coords = RoutingService.get_coordinates(query)
            if not coords:
                coords = RoutingService.get_coordinates(city_fallback)
                return coords, True
            return coords, False
            
        # Geocode locations (fallback to city-level if precise location not found on OSM)
        origin_coords, origin_is_fallback = get_coords_with_fallback(origin_query, origin_city)
        origin_airport_coords, _ = get_coords_with_fallback(origin_airport, origin_city)
        
        dest_airport_coords, _ = get_coords_with_fallback(dest_airport, dest_city)
        dest_coords, dest_is_fallback = get_coords_with_fallback(dest_query, dest_city)
        
        # Get driving times
        if origin_coords and origin_airport_coords:
            time_to_airport_mins = RoutingService.get_driving_duration_minutes(origin_coords, origin_airport_coords)
        else:
            time_to_airport_mins = 45 # Realistic default for major cities
            
        if dest_airport_coords and dest_coords:
            time_from_airport_mins = RoutingService.get_driving_duration_minutes(dest_airport_coords, dest_coords)
        else:
            time_from_airport_mins = 45
        
        # Calculate Date/Time strategy
        try:
            meeting_dt = datetime.datetime.strptime(meeting_time_str.strip(), "%H:%M")
        except ValueError:
            try:
                meeting_dt = datetime.datetime.strptime(meeting_time_str.strip(), "%I:%M %p")
            except ValueError:
                meeting_dt = datetime.datetime.strptime("09:00 AM", "%I:%M %p")
            
        # Flight Duration
        flight_duration_mins = 120
        if origin_airport_coords and dest_airport_coords:
            flight_duration_mins = RoutingService.estimate_flight_duration_minutes(origin_airport_coords, dest_airport_coords)
        
        airport_checkin_mins = 90
        airport_checkout_mins = 30
        
        # Optimal backward calculation for same-day travel
        total_same_day_transit_mins = (time_to_airport_mins + buffer_mins + 
                                       airport_checkin_mins + flight_duration_mins + 
                                       airport_checkout_mins + time_from_airport_mins + buffer_mins)
        
        optimal_same_day_leave_dt = meeting_dt - datetime.timedelta(minutes=total_same_day_transit_mins)
        
        # Check user constraints (e.g. "cannot leave before 8am", "leave after 8am", "leave at 7am")
        user_note = request_details.get("user_note", "").lower()
        time_match = re.search(r"(?:before|at|by|around|after|leave(?: at| by| before| around| after)?)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", user_note)
        if not time_match:
            time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", user_note)
            
        origin_text_for_reason = f"{origin_city} center" if origin_is_fallback else origin_loc
        dest_text_for_reason = f"{dest_city} center" if dest_is_fallback else dest_loc

        travel_day_before = False
        hotel_possible_flag = buffer_mins > 0

        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3)
            
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            
            user_leave_time = datetime.time(hour, minute)
            user_leave_dt = datetime.datetime.combine(meeting_dt.date(), user_leave_time)
            
            # Calculate arrival at venue if user leaves at user_leave_time on meeting day
            same_day_reach_airport_dt = user_leave_dt + datetime.timedelta(minutes=time_to_airport_mins + buffer_mins)
            same_day_flight_dept_dt = same_day_reach_airport_dt + datetime.timedelta(minutes=airport_checkin_mins)
            same_day_flight_arr_dt = same_day_flight_dept_dt + datetime.timedelta(minutes=flight_duration_mins)
            same_day_dest_airport_dt = same_day_flight_arr_dt + datetime.timedelta(minutes=airport_checkout_mins)
            same_day_venue_arrival_dt = same_day_dest_airport_dt + datetime.timedelta(minutes=time_from_airport_mins + buffer_mins)
            
            if same_day_venue_arrival_dt > meeting_dt:
                # Same-day travel causes late arrival! Must travel the day before.
                travel_day_before = True
            else:
                # Same-day travel works!
                leave_office_dt = user_leave_dt
                reach_airport_dt = same_day_reach_airport_dt
                flight_departure_dt = same_day_flight_dept_dt
                flight_arrival_dt = same_day_flight_arr_dt
                expected_arrival_at_venue_dt = same_day_venue_arrival_dt
                reason_text = (
                    f"User Constraint Applied: Leaving office at {leave_office_dt.strftime('%I:%M %p')}. "
                    f"You will arrive at {dest_text_for_reason} by {expected_arrival_at_venue_dt.strftime('%I:%M %p')}, on time for your {meeting_dt.strftime('%I:%M %p')} meeting. "
                    f"(Routing to airport: {time_to_airport_mins}m, Flight: {flight_duration_mins}m, Routing to venue: {time_from_airport_mins}m)."
                )
        else:
            # Standard optimal same-day calculation
            leave_office_dt = optimal_same_day_leave_dt
            reach_airport_dt = leave_office_dt + datetime.timedelta(minutes=time_to_airport_mins + buffer_mins)
            flight_departure_dt = reach_airport_dt + datetime.timedelta(minutes=airport_checkin_mins)
            flight_arrival_dt = flight_departure_dt + datetime.timedelta(minutes=flight_duration_mins)
            expected_arrival_at_venue_dt = meeting_dt
            reason_text = (
                f"Optimal Same-Day Itinerary: Departing office at {leave_office_dt.strftime('%I:%M %p')} ensures a smooth arrival at {dest_text_for_reason} "
                f"at {expected_arrival_at_venue_dt.strftime('%I:%M %p')} right before your meeting. "
                f"(Routing to airport: {time_to_airport_mins}m, Check-in: {airport_checkin_mins}m, Flight: {flight_duration_mins}m, Weather buffer: {buffer_mins}m)."
            )

        if travel_day_before:
            # Shift travel date to previous day
            try:
                meeting_date_obj = datetime.datetime.strptime(meeting_date_str, "%Y-%m-%d")
                travel_date_str = (meeting_date_obj - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            except Exception:
                travel_date_str = meeting_date_str

            # Schedule evening travel on the day before (e.g. depart office at 5:00 PM on the day before)
            leave_office_dt = datetime.datetime.combine(meeting_dt.date(), datetime.time(17, 0)) # 5:00 PM
            reach_airport_dt = leave_office_dt + datetime.timedelta(minutes=time_to_airport_mins + buffer_mins)
            flight_departure_dt = reach_airport_dt + datetime.timedelta(minutes=airport_checkin_mins)
            flight_arrival_dt = flight_departure_dt + datetime.timedelta(minutes=flight_duration_mins)
            leave_dest_airport_dt = flight_arrival_dt + datetime.timedelta(minutes=airport_checkout_mins)
            expected_arrival_at_venue_dt = leave_dest_airport_dt + datetime.timedelta(minutes=time_from_airport_mins + buffer_mins)

            hotel_possible_flag = True
            reason_text = (
                f"Schedule Optimized for Prior-Day Travel: Since departing after your requested time ({user_leave_time.strftime('%I:%M %p')}) on the meeting day "
                f"would cause you to arrive late at {same_day_venue_arrival_dt.strftime('%I:%M %p')} (after your {meeting_dt.strftime('%I:%M %p')} meeting), "
                f"outbound travel is scheduled for the evening prior on {travel_date_str}. "
                f"You will depart office at {leave_office_dt.strftime('%I:%M %p')}, board a {flight_departure_dt.strftime('%I:%M %p')} flight, and check into an executive budget hotel near {dest_text_for_reason}. "
                f"This guarantees you wake up near the venue and attend your {meeting_dt.strftime('%I:%M %p')} meeting relaxed and fully on time."
            )
            
        strategy = {
            "leave_office": leave_office_dt.strftime("%I:%M %p"),
            "reach_airport": reach_airport_dt.strftime("%I:%M %p"),
            "flight_departure": flight_departure_dt.strftime("%I:%M %p"),
            "flight_arrival": flight_arrival_dt.strftime("%I:%M %p"),
            "expected_arrival_at_venue": expected_arrival_at_venue_dt.strftime("%I:%M %p"),
            "return_required": request_details.get("return_required", True),
            "hotel_possible": hotel_possible_flag,
            "reason": reason_text,
            "origin": origin_query,
            "destination": dest_query,
            "origin_city": origin_city,
            "destination_city": dest_city,
            "date": travel_date_str, # Outbound flight & hotel date (day before)
            "meeting_date": meeting_date_str
        }
        
        return strategy
