# 🗓️ Calendar Routing Agent with OpenAI GPT-4o

This project is an intelligent calendar assistant that uses OpenAI's GPT-4o to:
- Detect whether a user query is a calendar-related request.
- Route the query to either a **new event creator** or an **event modifier**.
- Extract structured event details (name, date, participants).
- Return a natural language confirmation with optional calendar links.

> ⚙️ Powered by: Pydantic, OpenAI function calling, and structured prompt chaining.

---

## 🚀 Features

- 🔍 **Intent classification** (new_event, modify_event, or other)
- ✍️ **Natural language to structured format** via OpenAI chat.completions.parse
- 🛡️ **Confidence thresholding** for robust request handling
- 🧠 **LLM-powered parsing** for participants, event names, times, and changes
- 🧾 **Calendar link stub** generation for integration with external calendar systems

---

## 📦 Installation

Clone the repository:

```bash 
git clone https://github.com/your-username/Calender-Routing-Agent.git
cd calendar-routing-agent
```

## 🛠 Setup Instructions

Create a Virtual Environment and Install Dependencies
``` bash 
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 🔐 Create a .env File
Create a file named .env in the project root and add your OpenAI API key:
``` bash
OPENAI_API_KEY=your-openai-api-key
```
