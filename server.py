import os
import time
from datetime import datetime, timezone

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Railway Ticket Booking", host="0.0.0.0", port=int(os.environ.get("PORT", 8001)))

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")
TWIML_BIN_URL = os.environ.get("TWIML_BIN_URL", "")

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


@mcp.tool()
def make_feedback_call(customer_phone: str, case_id: str, customer_name: str) -> dict:
    """Make an outbound Twilio phone call to collect customer feedback after a Salesforce case is closed."""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        return {"status": "ERROR", "message": "Twilio credentials not configured"}

    if not customer_phone:
        return {"status": "ERROR", "message": "No phone number provided"}

    twiml_url = (
        f"{TWIML_BIN_URL}"
        f"?case_id={case_id}"
        f"&name={customer_name}"
    )

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls.json"
    response = httpx.post(
        url,
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        data={
            "To": customer_phone,
            "From": TWILIO_PHONE_NUMBER,
            "Url": twiml_url,
        },
        timeout=30.0,
    )

    if response.status_code == 201:
        call_data = response.json()
        return {
            "status": "CALL_INITIATED",
            "call_sid": call_data.get("sid"),
            "to": customer_phone,
            "case_id": case_id,
            "customer_name": customer_name,
            "initiated_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "FAILED",
        "error": response.text,
        "status_code": response.status_code,
    }


@mcp.tool()
def send_case_update_sms(customer_phone: str, case_number: str, customer_name: str, status: str, message: str) -> dict:
    """Send an SMS notification to the customer when a Salesforce case status changes."""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        return {"status": "ERROR", "message": "Twilio credentials not configured"}

    if not customer_phone:
        return {"status": "ERROR", "message": "No phone number provided"}

    sms_body = (
        f"Hi {customer_name}, your support case {case_number} "
        f"has been updated to: {status}. {message}"
    )

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    response = httpx.post(
        url,
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        data={
            "To": customer_phone,
            "From": TWILIO_PHONE_NUMBER,
            "Body": sms_body,
        },
        timeout=30.0,
    )

    if response.status_code == 201:
        sms_data = response.json()
        return {
            "status": "SMS_SENT",
            "message_sid": sms_data.get("sid"),
            "to": customer_phone,
            "case_number": case_number,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "FAILED",
        "error": response.text,
        "status_code": response.status_code,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
