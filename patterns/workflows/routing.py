from typing import Optional, Literal
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(
    level = logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt = "%Y-5m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4o"

# ----------------------------- Schema Definitions -----------------------------
class CalendarRequestType(BaseModel):
    """LLM output format to classify the type of calendar request"""
    request_type: Literal["new_event", "modify_event", "other"] = Field(
        description="Type of calendar request being made"
    )
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    description: str = Field(description="Cleaned description of the request")

class NewEventDetails(BaseModel):
    """Details for creating a new event"""
    name: str = Field(description="Name of the event")
    date: str = Field(description="Date of the event")
    duration_minutes: int = Field(description="Duration in minutes")
    participants: list[str] = Field(description="List of participants")

class Change(BaseModel):
    """Details for changing an existing event"""
    field: str = Field(description="Field to change")
    new_value: str = Field(description="New value for the field")

class ModifyEventDetails(BaseModel):
    """Details for modifying an existing event"""
    event_identifier: str = Field(
        description="Description to identify the existing event"
    )
    changes: list[Change] = Field(description="List of changes to make")
    participants_to_add: list[str] = Field(description="New participants to add")
    participants_to_remove: list[str] = Field(description="Participants to remove")

class CalendarResponse(BaseModel):
    """Final response format"""
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="User-friendly response message")
    calendar_link: Optional[str] = Field(description="Calendar link if applicable")

# ----------------------------- Routing Logic -----------------------------
def route_calendar_request(user_input: str) -> CalendarRequestType:
    """Router LLM call to determine the type of calendar request"""
    logger.info("Routing calendar request")

    completion = client.beta.chat.completions.parse(
        model = model,
        messages = [
            {
                "role": "system",
                "content": "Determine if this is a request to create a new calendar event or modify an existing one.",
            },
            {"role": "user", "content": user_input},
        ],
        response_format=CalendarRequestType
    )

    result = completion.choices[0].message.parsed
    logger.info(
        f"Request routed as: {result.request_type} with confidence: {result.confidence_score}"
    )

    return result

# ----------------------------- New Event Handler -----------------------------
def handle_new_event(description: str) -> CalendarResponse:
    """Process a new event request"""
    logger.info("Processing new event request")

    completion = client.beta.chat.completions.parse(
        model = model,
        messages = [
            {
                "role": "system",
                "content": "Extract details for creating a new calendar event. Convert any relative or natural language dates (e.g., 'next Tuesday') into ISO 8601 format (YYYY-MM-DD), assuming today is {TODAY}.",
            },
            {
                "role": "user",
                "content": description,
            }
        ],
        response_format = NewEventDetails,
    )

    details = completion.choices[0].message.parsed

    logger.info(f"New event: {details.model_dump_json(indent=2)}")

    return CalendarResponse(
        success = True,
        message = f"Created new event '{details.name}' for {details.date} with {', '.join(details.participants)}",
        calendar_link=f"calendar://new?event={details.name}",
    )

# ----------------------------- Modify Event Handler -----------------------------
def handle_modify_event(description: str) -> CalendarResponse:
    """Process an event modification request"""
    logger.info("Processing event modification request")

    completion = client.beta.chat.completions.parse(
        model = model,
        messages = [
            {
                "role": "system",
                "content": "Extract details for modifying an existing calendar event. - Use 'event_identifier' to describe the event being modified (e.g., its current name or participant list).- For each field change (e.g., time, date, name), add an entry to the 'changes' list with 'field' and 'new_value'.- Use exact field names like 'time', 'date', or 'name' (not phrases like 'meeting time').- Use natural language values like 'Wednesday at 3pm' for 'new_value'. - List participants to add in 'participants_to_add'. - List participants to remove in 'participants_to_remove'. Return the data in JSON matching the ModifyEventDetails model.",
            },
            {
                "role": "user", "content": description
            },
        ],
        response_format=ModifyEventDetails
    )
    details = completion.choices[0].message.parsed

    logger.info(f"Modified event: {details.model_dump_json(indent=2)}")

    return CalendarResponse(
        success=True,
        message = f"Modified event '{details.event_identifier}' with the requested changes",
        calendar_link=f"calendar://modify?event={details.event_identifier}",
    )

# ----------------------------- Master Routing Handler -----------------------------
def process_calendar_request(user_input: str) -> Optional[CalendarResponse]:
    """Main function implementing the routing workflow"""
    logger.info("Processing calendar request")

    route_result = route_calendar_request(user_input)

    if route_result.confidence_score < 0.7:
        logger.warning(f"Low confidence score: {route_result.confidence_score}")
        return None

    if route_result.request_type == "new_event":
        return handle_new_event(route_result.description)
    elif route_result.request_type == "modify_event":
        return handle_modify_event(route_result.description)
    else:
        logger.warning("Request type not supported")
        return None


# ----------------------------- Test Cases -----------------------------
# Valid new event
new_event_input = "Let's schedule a team meeting next Tuesday at 2pm with Alice and Bob"
result = process_calendar_request(new_event_input)
if result:
    print(f"Response: {result.message}")

# Another valid new event
new_event_input2 = "I want to schedule a team meeting next Thursday at 1pm with Ethan and Justin"
result = process_calendar_request(new_event_input2)
if result:
    print(f"Response: {result.message}")

# Valid modify event
modify_event_input = ("Can you move the team meeting with Alice and Bob to Wednesday at 3pm instead? And remove Alice and add Jamie")
result = process_calendar_request(modify_event_input)
if result:
    print(f"Response: {result.message}")

# Invalid input (non-calendar)
invalid_input = "What's weather like today?"
result = process_calendar_request(invalid_input)
if not result:
    print("Request not recognized as a calendar operation.")