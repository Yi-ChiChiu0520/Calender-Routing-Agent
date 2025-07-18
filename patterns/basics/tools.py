import json
import os

import requests
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import Optional


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------- Weather Tool Function -----------------------------
def get_weather(latitude, longitude):
    """This is a publicly available API that returns the weather of a location"""
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )
    data = response.json()
    return data["current"]


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current temperature for provided coordinates",
            "parameters":{
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required":["latitude", "longitude"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]

system_prompt = "You are a helpful weather assistant"

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Who is the president of the US"}
]

# ----------------------------- Initial Chat Completion Call -----------------------------
completion = client.chat.completions.create(
    model = "gpt-4o",
    messages = messages,
    tools = tools,
)

message = completion.choices[0].message

# ----------------------------- Check What the Model Returned -----------------------------
if message.content:
    print("Model replied:", message.content)
elif message.tool_calls:
    print("Model used a tool call")
else:
    print("No content or tool calls")

completion.model_dump()

def call_function(name, args):
    if name == "get_weather":
        return get_weather(**args)

tool_calls = completion.choices[0].message.tool_calls

# ----------------------------- Execute Tool Call (If Any) -----------------------------
if tool_calls:
    for tool_call in tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        messages.append(completion.choices[0].message)

        result = call_function(name, args)
        messages.append(
            {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
        )
else:
    print("LLM chose not to use any tool.")


class WeatherResponse(BaseModel):
    temperature: Optional[float] = Field(
        description="The current temperature in celsius for the given location"
    )
    response: str = Field(
        description="A natural language response to user's question"
    )

# ----------------------------- Final Chat Completion to Format Output -----------------------------
completion_2 = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages = messages,
    tools = tools,
    response_format = WeatherResponse
)

final_response = completion_2.choices[0].message.parsed

if final_response.temperature is not None:
    print(final_response.temperature)
else:
    print("No temperature data was retrieved.")

print(final_response.response)
