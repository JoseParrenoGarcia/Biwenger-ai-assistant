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

## Current Implementation
- **Centralized OpenAI Client Directory**: A centralized directory (`llm_clients`) is used to load and configure the OpenAI client. This includes loading credentials from environment variables or a `secrets/openAI.toml` file.
- **Streamlit Chatbot Interface**: A simple chatbot interface is implemented using Streamlit. It supports:
  - Chat history rendering.
  - User input handling.
  - Streaming or non-streaming responses based on user preference.

## Possible ideas to expore to implement

#### Agent Additions
`PlannerAgent`: produces structured plan JSON; consumes user prompt + schema summary.
`ClarifierAgent`: generates disambiguation questions when planner marks uncertainty.
`CodeGenAgent`: translates plan step → pandas/SQL; performs self-check against available columns.
`RepairAgent`: takes traceback + original code → patched code (bounded diff).
`VizAgent`: ranks chart specs; enforces data volume thresholds.
`SummarizerAgent`: converts dataframe stats + plot context → narrative with caveats.
`PolicyAgent`: validates plan vs guardrails (row limits, restricted columns).
`ModelRouter`: rule-based selection (task tag → model id).

#### Context Objects (Structured)
`SessionState`: `messages[]`, `activePlan`, `dataframes{alias: {schema, rowCount, lineage}}`.
`SchemaCache`: tables, columns, semantic tags, last_refreshed.
`ToolManifest`: name, input schema, output schema, cost hint.
`PlanStep`: id, type, status (`pending|running|failed|done`), artifacts, retries.
`ObservationLog`: timing, token usage, errors.

#### Minimal New Files
`agents/planner.py`
`agents/clarifier.py`
`agents/code_gen.py`
`agents/repair.py`
`agents/viz.py`
`agents/summarizer.py`
`core/model_router.py`
`core/memory.py`
`core/plan_schema.py`
`tools/manifest.py`
`validation/policy.py`

#### Suggested Plan JSON (Example Skeleton
```json
{
  "version": "1.0",
  "intent": "aggregate_sales_by_region",
  "confidence": 0.82,
  "clarificationsNeeded": ["Define time range"],
  "steps": [
    {"id": "s1", "type": "fetch_schema", "targets": ["sales"], "expected_artifact": "sales_schema"},
    {"id": "s2", "type": "profile_columns", "targets": ["sales.region", "sales.amount"]},
    {"id": "s3", "type": "generate_query", "operation": "groupby_sum", "columns": ["region", "amount"]},
    {"id": "s4", "type": "execute_query", "engine": "pandas"},
    {"id": "s5", "type": "validate_result", "checks": ["row_count>0", "no_nulls:region"]},
    {"id": "s6", "type": "suggest_viz", "chart_candidates": ["bar"]},
    {"id": "s7", "type": "summarize", "style": "concise"}
  ],
  "risks": ["ambiguous time range", "high cardinality regions"],
  "policy_flags": []
}
```