import json
import re
from llm import ask_llama
from sql_agent import execute_sql
from vector_agent import search


# ----------------------------
# Planner
# ----------------------------

def plan(question: str):
    prompt = f"""
You are a router for an AI system.

User question:
"{question}"

Choose tool:
- chat → greetings, small talk
- vector → complaints, feedback, issues, refund, delay, unhappy
- sql → counts, totals, averages, rankings, analytics
- both → only when clearly both are needed

Return ONLY JSON:
{{ "tool": "sql" | "vector" | "both" | "chat" }}
"""
    raw = ask_llama(prompt).strip()

    try:
        return json.loads(raw)
    except:
        return {"tool": "sql"}


# ----------------------------
# SQL extraction
# ----------------------------

def extract_sql(text: str) -> str:
    text = text.replace("```sql", "").replace("```", "").strip()
    match = re.search(r"(select .*?;)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


# ----------------------------
# SQL safety (simple + correct)
# ----------------------------

def is_safe_sql(sql: str) -> bool:
    """
    Allow all SELECT queries.
    Block only destructive commands.
    """
    sql_lower = sql.lower()

    blocked = ["delete", "drop", "update", "insert", "alter", "truncate"]
    if any(word in sql_lower for word in blocked):
        return False

    return sql_lower.strip().startswith("select")


# ----------------------------
# Numeric formatter
# ----------------------------

def format_numeric(question: str, value):
    q = question.lower()

    if "customer" in q:
        return f"There are {value} customers."

    if "order" in q:
        return f"There are {value} orders."

    if "revenue" in q or "amount" in q:
        return f"The total revenue is {round(value, 2)}."

    return str(value)


# ----------------------------
# Main handler
# ----------------------------

def handle(question: str):
    decision = plan(question)
    tool = decision.get("tool", "sql")

    print("Planner decision:", decision)

    # ---------- CHAT ----------
    if tool == "chat":
        return ask_llama(f"Reply naturally:\n{question}")

    # ---------- VECTOR ----------
    if tool == "vector":
        results = search(question)
        docs = results.get("documents", [[]])[0]

        if not docs:
            return "I couldn't find relevant complaints or feedback."

        return "Here are relevant findings:\n" + "\n".join(f"- {d}" for d in docs)

    # ---------- SQL ----------
    if tool == "sql":
        sql_prompt = f"""
You are an expert MySQL assistant.

Schema:
orders(id, customer_name, amount, created_at)

Rules:
- Use only this table
- Return ONLY SQL
- Do NOT explain

Question:
{question}
"""
        raw_sql = ask_llama(sql_prompt)
        sql = extract_sql(raw_sql)

        print("Generated SQL:", sql)

        if not is_safe_sql(sql):
            return "Blocked unsafe query."

        try:
            result = execute_sql(sql)
        except Exception as e:
            return f"SQL error: {str(e)}"

        print("SQL Result:", result)

        # Deterministic numeric handling
        if (
            isinstance(result, list)
            and len(result) == 1
            and isinstance(result[0], tuple)
            and len(result[0]) == 1
            and isinstance(result[0][0], (int, float))
        ):
            return format_numeric(question, result[0][0])

        # Otherwise let LLM summarize
        answer_prompt = f"""
Question: {question}
Result: {result}

Write a short factual answer.
"""
        return ask_llama(answer_prompt)

    # ---------- BOTH ----------
    if tool == "both":
        vec = search(question)
        docs = vec.get("documents", [[]])[0]

        sql_prompt = f"""
You are an expert MySQL assistant.

Schema:
orders(id, customer_name, amount, created_at)

Return ONLY SQL.

Question:
{question}
"""
        raw_sql = ask_llama(sql_prompt)
        sql = extract_sql(raw_sql)

        print("Generated SQL:", sql)

        if not is_safe_sql(sql):
            return "Blocked unsafe query."

        try:
            sql_result = execute_sql(sql)
        except Exception as e:
            return f"SQL error: {str(e)}"

        final_prompt = f"""
User question: {question}

Structured data:
{sql_result}

Semantic info:
{docs}

Give a concise helpful answer.
"""
        return ask_llama(final_prompt)

    return "I couldn't understand the request."
