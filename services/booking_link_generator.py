import urllib.parse

class BookingLinkGenerator:
    """
    A utility service to generate booking links.
    """
    
    @staticmethod
    def generate_flight_link(source: str, destination: str, date: str) -> str:
        """
        Generates a Google Flights link for the given source, destination, and date.
        Date should be in YYYY-MM-DD format.
        """
        # Simplified URL structure for demonstration
        base_url = "https://www.google.com/travel/flights"
        query = f"{source} to {destination} on {date}"
        encoded_query = urllib.parse.quote(query)
        return f"{base_url}?q={encoded_query}"

    @staticmethod
    def generate_hotel_link(location: str, checkin_date: str, checkout_date: str) -> str:
        """
        Generates a Google Hotels link.
        """
        base_url = "https://www.google.com/travel/hotels"
        query = f"Hotels in {location} from {checkin_date} to {checkout_date}"
        encoded_query = urllib.parse.quote(query)
        return f"{base_url}?q={encoded_query}"
