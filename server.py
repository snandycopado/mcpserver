import os
import time
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Railway Ticket Booking", host="0.0.0.0", port=int(os.environ.get("PORT", 8001)))

FARES = {
    "sodepur": {"fare": 10, "time": "12:24 PM", "platform": 7, "distance": "17 km"},
    "dum dum": {"fare": 5, "time": "12:10 PM", "platform": 3, "distance": "8 km"},
    "baranagar": {"fare": 7, "time": "12:18 PM", "platform": 5, "distance": "12 km"},
}

DEFAULT_FARE = {"fare": 15, "time": "12:30 PM", "platform": 1, "distance": "unknown"}


@mcp.tool()
def get_fare_details(destination: str) -> dict:
    """Get train fare and schedule for a destination from Sealdah."""
    info = FARES.get(destination.lower(), DEFAULT_FARE)
    booking_ref = f"TKT-{int(time.time() * 1000)}"
    return {
        "origin": "Sealdah",
        "destination": destination,
        **info,
        "booking_ref": booking_ref,
    }


@mcp.tool()
def generate_payment_qr(amount: float, booking_ref: str) -> dict:
    """Generate UPI QR code for ticket payment."""
    return {
        "qr_url": f"https://your-server.com/qr/{booking_ref}",
        "upi_string": f"upi://pay?pa=railway@upi&am={amount}&tn={booking_ref}",
        "expires_in": 120,
    }


@mcp.tool()
def verify_payment(booking_ref: str) -> dict:
    """Check if UPI payment was completed."""
    return {
        "status": "SUCCESS",
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def generate_ticket(booking_ref: str) -> dict:
    """Issue final train ticket after payment confirmed."""
    return {
        "ticket_id": booking_ref,
        "status": "CONFIRMED",
        "valid_for": "Single journey",
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
