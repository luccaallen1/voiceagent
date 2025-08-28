"""
Webhook-enabled functions for voice agent
Integrates with external APIs and services via HTTP webhooks
"""

import aiohttp
import asyncio
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Configuration for webhook endpoints
WEBHOOK_CONFIG = {
    "n8n_webhooks": {
        "url": "https://luccatora.app.n8n.cloud/webhook",
        "timeout": 10  # seconds
    },
    "booking_system": {
        "url": "https://your-booking-api.com/api/v1",
        "api_key": "your-api-key-here",
        "timeout": 10  # seconds
    },
    "calendar_service": {
        "url": "https://your-calendar-api.com/api",
        "api_key": "your-calendar-key",
        "timeout": 5
    },
    "crm_system": {
        "url": "https://your-crm.com/api/v2",
        "api_key": "your-crm-key",
        "timeout": 8
    }
}

async def call_webhook(endpoint_name, path, method="POST", data=None, params=None):
    """
    Generic webhook caller with error handling and retry logic
    
    Args:
        endpoint_name: Key in WEBHOOK_CONFIG
        path: API path to append to base URL
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Request body data
        params: Query parameters
    
    Returns:
        Response data or error dict
    """
    config = WEBHOOK_CONFIG.get(endpoint_name)
    if not config:
        return {"error": f"Unknown webhook endpoint: {endpoint_name}"}
    
    # Build URL - handle both with and without path
    if path:
        url = f"{config['url']}/{path}"
    else:
        url = config['url']
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Only add auth header if API key exists
    if config.get('api_key'):
        headers["Authorization"] = f"Bearer {config['api_key']}"
    
    logger.info(f"Calling webhook: {method} {url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=aiohttp.ClientTimeout(total=config['timeout'])
            ) as response:
                response_data = await response.json()
                
                if response.status >= 200 and response.status < 300:
                    logger.info(f"Webhook success: {response.status}")
                    return response_data
                else:
                    logger.error(f"Webhook error: {response.status} - {response_data}")
                    return {
                        "error": f"API error: {response.status}",
                        "details": response_data
                    }
                    
        except asyncio.TimeoutError:
            logger.error(f"Webhook timeout for {url}")
            return {"error": "Request timed out"}
        except Exception as e:
            logger.error(f"Webhook exception: {str(e)}")
            return {"error": str(e)}


# APPOINTMENT BOOKING FUNCTIONS WITH WEBHOOKS

async def check_date(params):
    """
    CheckDate function - converts natural language date to YYYY-MM-DD format
    Uses n8n webhook to process natural language dates like 'next saturday' or 'tomorrow'
    
    This function is called by the voice agent when users mention dates in natural language.
    """
    # Extract the natural language date input
    # The parameter name is 'text' as expected by the voice agent
    input_text = params.get("text", "")
    
    if not input_text:
        return {"error": "No date input provided"}
    
    # Call the n8n webhook with the exact format expected
    webhook_data = {
        "input": input_text  # n8n webhook expects 'input' field
    }
    
    logger.info(f"Calling CheckDate webhook with input: {input_text}")
    
    # Call the n8n webhook
    response = await call_webhook(
        "n8n_webhooks",
        "check_date",  # This appends to make: https://luccatora.app.n8n.cloud/webhook/check_date
        method="POST",
        data=webhook_data
    )
    
    if "error" in response:
        # If webhook fails, fall back to local parsing
        logger.warning(f"CheckDate webhook failed, using fallback: {response}")
        
        from datetime import datetime, timedelta
        text = input_text.lower()
        today = datetime.now()
        
        if "today" in text:
            target_date = today
        elif "tomorrow" in text:
            target_date = today + timedelta(days=1)
        elif "monday" in text:
            days_ahead = 0 - today.weekday()
            if days_ahead <= 0:
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
    
    # Return the response from n8n webhook
    # The webhook should return a date in YYYY-MM-DD format
    logger.info(f"CheckDate webhook response: {response}")
    return response


async def bookings(params):
    """
    Bookings function - checks availability for a specific day
    Uses n8n webhook to get available appointment times for the given date
    
    This function is called by the voice agent after check_date to find available slots.
    """
    # Extract the date parameter - should be in YYYY-MM-DD format from check_date
    date = params.get("date")
    
    if not date:
        return {"error": "Date is required"}
    
    # Call the n8n webhook with the exact format expected
    webhook_data = {
        "chatinput": date  # n8n webhook expects 'chatinput' field with YYYY-MM-DD format
    }
    
    logger.info(f"Calling Bookings webhook for date: {date}")
    
    # Call the n8n webhook
    response = await call_webhook(
        "n8n_webhooks",
        "bookings",  # This appends to make: https://luccatora.app.n8n.cloud/webhook/bookings
        method="POST",
        data=webhook_data
    )
    
    if "error" in response:
        # If webhook fails, fall back to mock data
        logger.warning(f"Bookings webhook failed, using fallback: {response}")
        
        # Return mock availability times for testing
        return {
            "times": ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"]
        }
    
    # Return the response from n8n webhook
    # The webhook should return available times in HH:MM format
    logger.info(f"Bookings webhook response: {response}")
    
    # If the webhook returns a different format, transform it here
    # Expected format for voice agent: {"times": ["09:00", "10:00", ...]}
    if "times" in response:
        return response
    elif "available_slots" in response:
        # Handle alternative response format
        return {"times": response["available_slots"]}
    elif isinstance(response, list):
        # If response is just a list of times
        return {"times": response}
    else:
        # Try to extract times from various possible formats
        return {"times": response.get("slots", response.get("availability", []))}


async def create_event(params):
    """
    create_event function - creates an appointment booking
    Uses n8n webhook to book the appointment with customer details
    
    This function is called by the voice agent after collecting customer information.
    """
    # Extract parameters - note the voice agent uses specific parameter names
    name = params.get("name")
    email_lowercase = params.get("email_lowercase")  # Voice agent sends lowercase email
    phone = params.get("phone")
    start_time = params.get("start_time")  # Format: YYYY-MM-DDTHH:MM
    
    # Validate required fields
    if not all([name, email_lowercase, phone, start_time]):
        missing_fields = []
        if not name: missing_fields.append("name")
        if not email_lowercase: missing_fields.append("email")
        if not phone: missing_fields.append("phone")
        if not start_time: missing_fields.append("appointment time")
        
        return {"error": f"Missing required fields: {', '.join(missing_fields)}"}
    
    # Prepare data for n8n webhook - using exact field names expected
    webhook_data = {
        "name": name,
        "number": phone,  # n8n webhook expects 'number' for phone
        "email": email_lowercase,
        "datetime": start_time  # Including the datetime for the appointment
    }
    
    logger.info(f"Calling create_event webhook for {name}, phone: {phone}, email: {email_lowercase}, time: {start_time}")
    
    # Call the n8n webhook
    response = await call_webhook(
        "n8n_webhooks",
        "create",  # This appends to make: https://luccatora.app.n8n.cloud/webhook/create
        method="POST",
        data=webhook_data
    )
    
    if "error" in response:
        # If webhook fails, return error message
        logger.error(f"create_event webhook failed: {response}")
        return {
            "success": False,
            "error": "Unable to complete booking at this time. Please call us at (256) 935-1911."
        }
    
    # Return success response
    logger.info(f"create_event webhook response: {response}")
    
    # Build success response for the voice agent
    booking_id = response.get("booking_id", f"BOOK{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    return {
        "success": True,
        "booking_id": booking_id,
        "confirmation_number": response.get("confirmation_code", booking_id),
        "name": name,
        "email": email_lowercase,
        "phone": phone,
        "appointment_time": start_time,
        "message": f"Appointment confirmed for {name} on {start_time}. Confirmation sent to {email_lowercase}."
    }


async def find_customer_webhook(params):
    """
    Look up customer via webhook to CRM or customer database
    """
    phone = params.get("phone")
    email = params.get("email")
    customer_id = params.get("customer_id")
    
    # Determine search parameter
    search_params = {}
    if phone:
        search_params["phone"] = phone
    elif email:
        search_params["email"] = email
    elif customer_id:
        search_params["id"] = customer_id
    else:
        return {"error": "No search criteria provided"}
    
    # Call CRM API
    response = await call_webhook(
        "crm_system",
        "customers/search",
        method="GET",
        params=search_params
    )
    
    if "error" in response:
        return {
            "found": False,
            "message": "Unable to find customer record"
        }
    
    customer = response.get("customer")
    if customer:
        return {
            "found": True,
            "customer_id": customer.get("id"),
            "name": customer.get("name"),
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "last_visit": customer.get("last_appointment_date"),
            "total_visits": customer.get("visit_count", 0),
            "notes": customer.get("notes")
        }
    else:
        return {
            "found": False,
            "message": "No customer found with that information"
        }


async def get_appointments_webhook(params):
    """
    Get customer's appointments via webhook
    """
    customer_id = params.get("customer_id")
    
    if not customer_id:
        return {"error": "Customer ID required"}
    
    response = await call_webhook(
        "booking_system",
        f"customers/{customer_id}/appointments",
        method="GET",
        params={"status": "upcoming"}
    )
    
    if "error" in response:
        return {
            "appointments": [],
            "message": "Unable to retrieve appointments"
        }
    
    appointments = response.get("appointments", [])
    return {
        "appointments": [
            {
                "date": apt.get("datetime"),
                "service": apt.get("service_name"),
                "provider": apt.get("provider_name"),
                "status": apt.get("status"),
                "confirmation": apt.get("confirmation_code")
            }
            for apt in appointments
        ],
        "count": len(appointments)
    }


# WEBHOOK FUNCTION MAP - Use these instead of the mock functions
WEBHOOK_FUNCTION_MAP = {
    "check_date": check_date,  # Now using n8n webhook
    "bookings": bookings,  # Now using n8n webhook
    "create_event": create_event,  # Now using n8n webhook
    "find_customer": find_customer_webhook,
    "get_appointments": get_appointments_webhook,
}


# Health check function to test webhook connectivity
async def test_webhooks():
    """
    Test all configured webhooks and return status
    """
    results = {}
    
    for endpoint_name, config in WEBHOOK_CONFIG.items():
        try:
            response = await call_webhook(
                endpoint_name,
                "health",
                method="GET"
            )
            results[endpoint_name] = {
                "status": "connected" if "error" not in response else "error",
                "response": response
            }
        except Exception as e:
            results[endpoint_name] = {
                "status": "error",
                "error": str(e)
            }
    
    return results