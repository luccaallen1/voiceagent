import json
from datetime import datetime, timedelta
import asyncio
from .business_logic import (
    get_customer,
    get_customer_appointments,
    get_customer_orders,
    schedule_appointment,
    get_available_appointment_slots,
    prepare_agent_filler_message,
    prepare_farewell_message,
)


async def find_customer(params):
    """Look up a customer by phone, email, or ID."""
    phone = params.get("phone")
    email = params.get("email")
    customer_id = params.get("customer_id")

    result = await get_customer(phone=phone, email=email, customer_id=customer_id)
    return result


async def get_appointments(params):
    """Get appointments for a customer."""
    customer_id = params.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}

    result = await get_customer_appointments(customer_id)
    return result


async def get_orders(params):
    """Get orders for a customer."""
    customer_id = params.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}

    result = await get_customer_orders(customer_id)
    return result


async def create_appointment(params):
    """Schedule a new appointment."""
    customer_id = params.get("customer_id")
    date = params.get("date")
    service = params.get("service")

    if not all([customer_id, date, service]):
        return {"error": "customer_id, date, and service are required"}

    result = await schedule_appointment(customer_id, date, service)
    return result


async def check_availability(params):
    """Check available appointment slots."""
    start_date = params.get("start_date")
    end_date = params.get(
        "end_date", (datetime.fromisoformat(start_date) + timedelta(days=7)).isoformat()
    )

    if not start_date:
        return {"error": "start_date is required"}

    result = await get_available_appointment_slots(start_date, end_date)
    return result


async def agent_filler(websocket, params):
    """
    Handle agent filler messages while maintaining proper function call protocol.
    """
    result = await prepare_agent_filler_message(websocket, **params)
    return result


async def end_call(websocket, params):
    """
    End the conversation and close the connection.
    """
    farewell_type = params.get("farewell_type", "general")
    result = await prepare_farewell_message(websocket, farewell_type)
    return result


async def check_date(params):
    """Convert natural date text to YYYY-MM-DD format in clinic timezone."""
    from datetime import datetime, timedelta
    
    text = params.get("text", "").lower()
    
    # Get today's date
    today = datetime.now()
    
    # Parse natural language dates
    if "today" in text:
        target_date = today
    elif "tomorrow" in text:
        target_date = today + timedelta(days=1)
    elif "monday" in text:
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
    elif "tuesday" in text:
        days_ahead = 1 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
    elif "wednesday" in text:
        days_ahead = 2 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
    elif "thursday" in text:
        days_ahead = 3 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
    elif "friday" in text:
        days_ahead = 4 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
    elif "saturday" in text:
        days_ahead = 5 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
    elif "sunday" in text:
        days_ahead = 6 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        target_date = today + timedelta(days=days_ahead)
    else:
        # Default to tomorrow if can't parse
        target_date = today + timedelta(days=1)
    
    return {"date": target_date.strftime("%Y-%m-%d")}


async def bookings(params):
    """Get available appointment slots for a specific date."""
    date = params.get("date")  # Expected format: YYYY-MM-DD
    
    if not date:
        return {"error": "Date is required"}
    
    # Use the existing availability checker with date range
    start_date = f"{date}T00:00:00"
    end_date = f"{date}T23:59:59"
    
    result = await get_available_appointment_slots(start_date, end_date)
    
    # Convert to the expected format - list of times in HH:MM format
    if "available_slots" in result:
        times = []
        for slot in result["available_slots"]:
            # Extract time from ISO datetime
            time_part = slot.split("T")[1].split(":")[0:2]  # Get HH:MM
            time_str = ":".join(time_part)
            times.append(time_str)
        return {"times": times}
    
    return {"times": []}


async def create_event(params):
    """Create an appointment event with customer details."""
    name = params.get("name")
    email_lowercase = params.get("email_lowercase")
    phone = params.get("phone") 
    start_time = params.get("start_time")  # Expected: YYYY-MM-DDTHH:MM
    
    if not all([name, email_lowercase, phone, start_time]):
        return {"error": "All fields are required: name, email_lowercase, phone, start_time"}
    
    # For this demo, we'll create a mock booking
    # In a real system, this would integrate with calendar/booking system
    
    booking_id = f"BOOK{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "success": True,
        "booking_id": booking_id,
        "name": name,
        "email": email_lowercase,
        "phone": phone,
        "appointment_time": start_time,
        "message": f"Appointment booked for {name} on {start_time}"
    }


# Function definitions that will be sent to the Voice Agent API  
FUNCTION_DEFINITIONS = [
    {
        "name": "check_date",
        "description": """Convert natural date expressions into YYYY-MM-DD format in clinic timezone.
        Input natural language like 'today', 'tomorrow', 'Monday', 'next Tuesday', 'July 22nd'.
        Returns standardized date format for use with bookings function.""",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Natural language date expression (e.g., 'tomorrow', 'Monday', 'next week')",
                }
            },
            "required": ["text"],
        },
    },
    {
        "name": "bookings",
        "description": """Get list of available appointment times for a specific date.
        Input the YYYY-MM-DD date from check_date function.
        Returns list of available start times in 24-hour HH:MM format.""",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format from check_date function",
                }
            },
            "required": ["date"],
        },
    },
    {
        "name": "create_event",
        "description": """Create an appointment booking with customer details.
        Use after collecting customer information and time selection.
        All fields are required for successful booking.""",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Customer's full name as confirmed in spelling confirmation",
                },
                "email_lowercase": {
                    "type": "string", 
                    "description": "Customer's email address in lowercase",
                },
                "phone": {
                    "type": "string",
                    "description": "Customer's callback phone number",
                },
                "start_time": {
                    "type": "string",
                    "description": "Appointment start time in YYYY-MM-DDTHH:MM format (clinic timezone)",
                },
            },
            "required": ["name", "email_lowercase", "phone", "start_time"],
        },
    },
    {
        "name": "find_customer",
        "description": """Look up a customer's account information. Use context clues to determine what type of identifier the user is providing:

        Customer ID formats:
        - Numbers only (e.g., '169', '42') → Format as 'CUST0169', 'CUST0042'
        - With prefix (e.g., 'CUST169', 'customer 42') → Format as 'CUST0169', 'CUST0042'
        
        Phone number recognition:
        - Standard format: '555-123-4567' → Format as '+15551234567'
        - With area code: '(555) 123-4567' → Format as '+15551234567'
        - Spoken naturally: 'five five five, one two three, four five six seven' → Format as '+15551234567'
        - International: '+1 555-123-4567' → Use as is
        - Always add +1 country code if not provided
        
        Email address recognition:
        - Spoken naturally: 'my email is john dot smith at example dot com' → Format as 'john.smith@example.com'
        - With domain: 'john@example.com' → Use as is
        - Spelled out: 'j o h n at example dot com' → Format as 'john@example.com'""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID. Format as CUSTXXXX where XXXX is the number padded to 4 digits with leading zeros. Example: if user says '42', pass 'CUST0042'",
                },
                "phone": {
                    "type": "string",
                    "description": """Phone number with country code. Format as +1XXXXXXXXXX:
                    - Add +1 if not provided
                    - Remove any spaces, dashes, or parentheses
                    - Convert spoken numbers to digits
                    Example: 'five five five one two three four five six seven' → '+15551234567'""",
                },
                "email": {
                    "type": "string",
                    "description": """Email address in standard format:
                    - Convert 'dot' to '.'
                    - Convert 'at' to '@'
                    - Remove spaces between spelled out letters
                    Example: 'j dot smith at example dot com' → 'j.smith@example.com'""",
                },
            },
        },
    },
    {
        "name": "get_appointments",
        "description": """Retrieve all appointments for a customer. Use this function when:
        - A customer asks about their upcoming appointments
        - A customer wants to know their appointment schedule
        - A customer asks 'When is my next appointment?'
        
        Always verify you have the customer's account first using find_customer before checking appointments.""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID in CUSTXXXX format. Must be obtained from find_customer first.",
                }
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_orders",
        "description": """Retrieve order history for a customer. Use this function when:
        - A customer asks about their orders
        - A customer wants to check order status
        - A customer asks questions like 'Where is my order?' or 'What did I order?'
        
        Always verify you have the customer's account first using find_customer before checking orders.""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID in CUSTXXXX format. Must be obtained from find_customer first.",
                }
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "create_appointment",
        "description": """Schedule a new appointment for a customer. Use this function when:
        - A customer wants to book a new appointment
        - A customer asks to schedule a service
        
        Before scheduling:
        1. Verify customer account exists using find_customer
        2. Check availability using check_availability
        3. Confirm date/time and service type with customer before booking""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID in CUSTXXXX format. Must be obtained from find_customer first.",
                },
                "date": {
                    "type": "string",
                    "description": "Appointment date and time in ISO format (YYYY-MM-DDTHH:MM:SS). Must be a time slot confirmed as available.",
                },
                "service": {
                    "type": "string",
                    "description": "Type of service requested. Must be one of the following: Initial Consultation, Chiropractic Adjustment, Follow-up Visit, Wellness Check, Maintenance Care, or Pain Assessment",
                    "enum": ["Initial Consultation", "Chiropractic Adjustment", "Follow-up Visit", "Wellness Check", "Maintenance Care", "Pain Assessment"],
                },
            },
            "required": ["customer_id", "date", "service"],
        },
    },
    {
        "name": "check_availability",
        "description": """Check available appointment slots within a date range. Use this function when:
        - A customer wants to know available appointment times
        - Before scheduling a new appointment
        - A customer asks 'When can I come in?' or 'What times are available?'
        
        After checking availability, present options to the customer in a natural way, like:
        'I have openings on [date] at [time] or [date] at [time]. Which works better for you?'""",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO format (YYYY-MM-DDTHH:MM:SS). Usually today's date for immediate availability checks.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in ISO format. Optional - defaults to 7 days after start_date. Use for specific date range requests.",
                },
            },
            "required": ["start_date"],
        },
    },
    {
        "name": "end_call",
        "description": """End the conversation and close the connection. Call this function when:
        - User says goodbye, thank you, etc.
        - User indicates they're done ("that's all I need", "I'm all set", etc.)
        - User wants to end the conversation
        
        Examples of triggers:
        - "Thank you, bye!"
        - "That's all I needed, thanks"
        - "Have a good day"
        - "Goodbye"
        - "I'm done"
        
        Do not call this function if the user is just saying thanks but continuing the conversation.""",
        "parameters": {
            "type": "object",
            "properties": {
                "farewell_type": {
                    "type": "string",
                    "description": "Type of farewell to use in response",
                    "enum": ["thanks", "general", "help"],
                }
            },
            "required": ["farewell_type"],
        },
    },
]

# Map function names to their implementations
FUNCTION_MAP = {
    "check_date": check_date,
    "bookings": bookings,
    "create_event": create_event,
    "find_customer": find_customer,
    "get_appointments": get_appointments,
    "get_orders": get_orders,
    "create_appointment": create_appointment,
    "check_availability": check_availability,
    "agent_filler": agent_filler,
    "end_call": end_call,
}
