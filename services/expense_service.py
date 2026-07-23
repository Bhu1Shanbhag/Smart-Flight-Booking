class ExpenseService:
    """
    A utility service to estimate the total trip cost.
    """
    
    @staticmethod
    def calculate_estimated_cost(flight_cost: float, hotel_cost: float = 0.0) -> dict:
        """
        Calculates the estimated cost of the trip.
        """
        total = flight_cost + hotel_cost
        return {
            "flight_cost": flight_cost,
            "hotel_cost": hotel_cost,
            "total_estimated_cost": total,
            "currency": "INR"
        }
