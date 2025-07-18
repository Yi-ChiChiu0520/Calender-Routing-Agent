import os

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --------------------------------------------------------------
# Basic Chat Completion Example
# --------------------------------------------------------------


completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a limerick about the Python programming language",
        },
    ], # type: ignore
)

response = completion.choices[0].message.content
print(response)