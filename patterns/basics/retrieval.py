import os
import json

from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------ Knowledge Base Function ------------------

def search_kb(question: str):
    """Load the whole knowledge base from the JSON file"""

    with open("kb.json","r") as f:
        return json.load(f)

# ------------------ Tool Definition for OpenAI ------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": "Get the answer to the user's question from the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type":"string"},
                },
                "required": ["question"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    }
]

system_prompt = "You are a helpful assistant that answers questions from the knowledge base about our e-commerce store."

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "What is the return policy?"}
]

# ------------------ First Call: Ask LLM to Pick a Tool ------------------
completion = client.chat.completions.create(
    model = "gpt-4o",
    messages = messages,
    tools = tools,
)

completion.model_dump()

# ------------------ Function Dispatcher ------------------
def call_function(name, args):
    if name == "search_kb":
        return search_kb(**args)

# ------------------ Handle Tool Call ------------------
for tool_call in completion.choices[0].message.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    messages.append(completion.choices[0].message)

    result = call_function(name, args)
    messages.append(
        {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
    )

# ------------------ Structured Response Model ------------------
class KBResponse(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    source: int = Field(description="The record id of the answer.")

# ------------------ Second Call: Ask LLM to Interpret Tool Output ------------------
completion_2 = client.beta.chat.completions.parse(
    model = "gpt-4o",
    messages = messages,
    tools = tools,
    response_format = KBResponse,
)

final_response = completion_2.choices[0].message.parsed
print(final_response.answer)
print(final_response.source)

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Who is the president of the US?"}
]

completion_3 = client.beta.chat.completions.parse(
    model = "gpt-4o",
    messages = messages,
    tools = tools,
)

irrelevant_response = completion_3.choices[0].message.content
print(irrelevant_response)