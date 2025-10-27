# Project: AI Senior Data Analyst

## Project
This project builds a chatbot that acts as your personal Senior Data Analyst. The agent can:
- Clarify vague requests into specific data analysis tasks.
- Access and load data from Supabase.
- Translate English requests into pandas code and execute it locally (filtering, aggregations, sorting, etc.).
- Summarize findings in clear English.
- (Planned) Generate visualizations using plotly.

## Goals
To do this, we will have an LLM agent that can:
- Use tools to access Supabase data.
- Use tools to run Python code with pandas and plotly.
- Use tools to generate English summaries.
- Have context of the current conversation history.

## Architecture
- **Centralized OpenAI Client Directory**: All OpenAI client configuration and loading is handled in a central directory (`llm_clients`). Credentials are loaded from environment variables or a `secrets/openAI.toml` file.
- **Tool Registry**: All callable tools are registered in a central registry (`tools/registry.py`). This ensures tool names and references are consistent and reduces manual errors.
- **Planner and Executor**: The agent first plans a minimal sequence of tool calls (planner phase), then executes them deterministically (executor phase).
- **Pandas Code Execution**: The agent can generate pandas code from natural language and execute it locally in a safe, validated environment (`tools/execute_pandas.py`). Security guardrails prevent unsafe operations.
- **Streamlit Chatbot Interface**: The UI is built with Streamlit, providing:
  - Chat history and user input handling.
  - Streaming or non-streaming responses (user toggle).
  - Display of plans, execution results, and generated pandas code.
  - Safe local execution of generated pandas code with immediate feedback.
  - Ability to clear chat/session state.

## Current Implementation
- Planning and execution phases are separated for clarity and safety.
- All tool specifications and Python callables are managed centrally.
- The chatbot can answer tool-related questions, propose action plans, and execute approved plans.
- Generated pandas code can be reviewed and executed locally, with results shown in the UI.

## Example Workflow
1. User enters a request in the chat.
2. The agent routes the request: answers directly or proposes a plan.
3. The plan is displayed for approval.
4. Upon approval, the agent executes the plan step-by-step.
5. Generated pandas code is shown and can be executed locally.
6. Results (dataframes, summaries) are displayed in the UI.

## Possible ideas to expore to implement

## Next Steps / Ideas
- Add agents for clarification, code repair, visualization, summarization, and policy validation.
- Expand context objects for richer session state and schema management.
- Integrate plotly for inline visualizations.
- Enhance error handling and user feedback.
-

#### Suggested Plan JSON (Example Skeleton
```json
{
  "steps": [
    {"tool": "load_biwenger_player_stats", "args": {}},
    {"tool": "english_to_pandas", "args": {"user_query": "best goalkeeper by total points", "table": "biwenger_player_stats"}}
  ],
  "why": "User wants to filter and rank goalkeepers by points.",
  "assumptions": ["Goalkeeper position exists in the dataset."]
}
```