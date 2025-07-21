from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import os
import logging
import sys
import smtplib

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logging.basicConfig(
    level = logging.INFO,
    stream=sys.stdout,  # Log to stdout instead of default stderr
    format = "%(asctime)s - %(levelname)s - %(message)s",
    datefmt= "%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4o"

# ----------------------------- Pydantic Schemas -----------------------------
class EventExtraction(BaseModel):
    """First step: Extract basic event information"""

    description: str = Field(description="Raw description of the event")
    is_calendar_event: bool = Field(
        description="Whether this text describes a calendar event"
    )
    confidence_score: float = Field(description="Confidence score between 0 and 1")

class EventDetails(BaseModel):
    """Second step: Parse specific event details"""

    name: str = Field(description="Name of the event")
    description: str = Field(description="Description of the event")
    location: str = Field(description="Location of the event")
    date: str = Field(
        description="Date and time of the event. Use ISO 8601 to format this value."
    )
    duration_minutes: int = Field(description="Expected duration in minutes")
    participants: list[str] = Field(description="List of participants")

class EventConfirmation(BaseModel):
    """Third step: Generate confirmation message"""

    confirmation_message: str = Field(
        description="Natural language confirmation message"
    )
    calendar_link: Optional[str] = Field(
        description="Generated calendar link if applicable"
    )
# ----------------------------- Step 1: Determine if Calendar Request -----------------------------
def extract_event_info(user_input: str) -> EventExtraction:
    logger.info("Starting event extraction analysis")
    logger.debug(f"Input text: {user_input}")

    today = datetime.now()
    date_context = f"Today is {today.strftime('%A, %B %d, %Y')}."

    completion = client.beta.chat.completions.parse(
        model = model,
        messages = [
            {
                "role": "system",
                "content": f"{date_context} Analyze if the text describes a calendar event.",
            },
            {"role": "user", "content": user_input},
        ],
        response_format = EventExtraction,
    )

    result = completion.choices[0].message.parsed
    logger.info(
        f"Extraction complete - Is calendar event: {result.is_calendar_event}, Confidence: {result.confidence_score:.2f}"
    )

    return result

# ----------------------------- Step 2: Parse Structured Event Details -----------------------------
def parse_event_details(description: str) -> EventDetails:
    logger.info("Starting event details parsing")

    today = datetime.now()
    date_context = f"Today is {today.strftime('%A, %B %d, %Y')}."

    completion = client.beta.chat.completions.parse(
        model = model,
        messages = [
            {
                "role": "system",
                "content": (
                    f"{date_context} Extract detailed event information. "
                    "When dates reference 'next Tuesday' or similar relative dates, use the current date as reference. "
                    "Format the date using full ISO 8601 format with time and time zone offset, e.g., '2025-07-24T14:00:00-07:00'."
                ),
            },
            {
                "role": "user",
                "content": description
            }
        ],
        response_format=EventDetails,
    )
    result = completion.choices[0].message.parsed
    logger.info(
        f"Parsed event details - Name: {result.name}, Date: {result.date}, Duration: {result.duration_minutes}min"
    )
    logger.info(f"Participants: {','.join(result.participants)}")
    return result

# ----------------------------- Step 3: Ask user for participants' emails -----------------------------
def email_invitation(participants: list[str]) -> list[str]:
    logger.info("Asking user for the emails of the participants")
    sys.stderr.flush()

    participants_email: list[str] = []
    for participant in participants:
        logger.info(f"Prompting for email of: {participant}")
        sys.stderr.flush()
        user_input = input(f"Please enter the email of the participants: {participant} \n")
        print(f"You entered: ", user_input)
        participants_email.append(user_input)

    return participants_email


# ----------------------------- Step 4: Send email to the participants emails -----------------------------
def send_email(to_emails: list[str], subject: str, message: str):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    msg.attach(MIMEText(message, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_emails, msg.as_string())
        logger.info(f"Email successfully sent to {msg['To']}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")



SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ----------------------------- Step 4: Add event to Google Calendar -----------------------------
def add_calendar_event(event_details: EventDetails, emails: list[str]):
    logger.info("Adding event to Google Calendar")

    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        start_time = event_details.date
        duration = event_details.duration_minutes

        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=duration)

        event = {
            "summary": event_details.name,
            "location": event_details.location,
            "description": event_details.description,
            "colorId": 5,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "America/Los_Angeles"
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "America/Los_Angeles"
            },
            "attendees": [{"email": email} for email in emails],
            "reminders": {
              "useDefault": True,
            },
        }

        event = service.events().insert(calendarId="primary", body=event).execute()

        print(f"Event created {event.get('htmlLink')}")

    except HttpError as error:
        print("An error occurred:", error)

# ----------------------------- Step ith: Generate Confirmation Message -----------------------------
def generate_confirmation(event_details: EventDetails) -> EventConfirmation:
    logger.info("Generating confirmation message")

    completion = client.beta.chat.completions.parse(
        model = model,
        messages = [
            {
                "role": "system",
                "content": "Generate a natural confirmation message for the event. Sign of with your name; Susie",
            },
            {"role": "user", "content": str(event_details.model_dump())},
        ],
        response_format=EventConfirmation
    )
    result = completion.choices[0].message.parsed
    logger.info("Confirmation message generated successfully")
    return result

# ----------------------------- Main Workflow -----------------------------
def process_calendar_request(user_input: str) -> Optional[EventConfirmation]:
    logger.info("Processing calendar request")
    logger.debug(f"Raw input: {user_input}")

    initial_extraction = extract_event_info(user_input)

    if(
        not initial_extraction.is_calendar_event
        or initial_extraction.confidence_score < 0.7
    ):
        logger.warning(
            f"Gate check failed - is_calendar_event: {initial_extraction.is_calendar_event}, confidence: {initial_extraction.confidence_score:.2f}"
        )
        return None

    logger.info("Gate check passed, proceeding with event processing")

    event_details = parse_event_details(initial_extraction.description)

    participants_emails = email_invitation(event_details.participants)


    confirmation = generate_confirmation(event_details)
    print(f"{confirmation.confirmation_message} \n")

    emails_string = ", ".join(participants_emails)

    send_confirmation = input(f"Could you please let me know if this email looks good to send? If Yes, then I will send this email to {emails_string}. If No, then I will output the email again and you can change it to your liking. Type [Yes\\No] \n")
    if send_confirmation.lower() == "yes":
        #call send email function
        send_email(
            to_emails=participants_emails,
            subject=event_details.name,
            message=confirmation.confirmation_message,
        )

    logger.info("Calendar request processing completed successfully")

    add_calendar_event(event_details, participants_emails)

# ----------------------------- Testing -----------------------------
# Valid calendar input
user_input = "Let's schedule a 1h team metting next Thursday at 2pm with Ethan to discuss the project roadmap."
result = process_calendar_request(user_input)

if result:
    print(f"Confirmation: {result.confirmation_message}")
    if result.calendar_link:
        print(f"Calendar Link: {result.calendar_link}")
else:
    print("This doesn't appear to be a calendar event request.")
