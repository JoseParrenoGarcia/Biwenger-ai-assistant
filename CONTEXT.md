# Project: AI Senior Data Analyst

## Project
This project will build a chatbot that can act as your personal Senior Data Analyst.
This Sr Data Analyst will be able to:
- Clarify vague requests into specific data analysis tasks.
- Access data sources from Supabase
- Translate English requests into pandas queries or code, and execute it locally. Filtering, aggregations, sortings, etc.
- Generate visualizations using plotly.
- Summarize findings in clear English.

## Goals
To do this, we will have an LLM agent that can:
- Use tools to access Supabase data.
- Use tools to run Python code with pandas and plotly.
- Use tools to generate English summaries.
- Have context of the current conversation history.

From the UI persepctive, we will use Streamlit:
- A chat interface to interact with the Sr Data Analyst.
- Display data tables and visualizations (still to be define if inline in the chat or separate area).
- Allow user to clear chat history.

## Key files
TBC
