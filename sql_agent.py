from db import get_connection
from llm import ask_llama
from vector_agent import search
import re


# -------------------------
# BASIC DB HELPERS
# -------------------------

def execute_sql(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def fetch_customers():
    rows = execute_sql("SELECT DISTINCT customer_name FROM orders")
    return [r[0] for r in rows]


def extract_customer(question: str):
    customers = fetch_customers()
    q = question.lower()

    for name in customers:
        if name.lower() in q:
            return name
    return None


# -------------------------
# SMALL TALK HANDLER
# -------------------------

def handle_smalltalk(question: str):
    q = question.lower().strip()

    if q in ["hi", "hello", "hey", "hii"]:
        return "Hello! How can I help you?"

    if "how are you" in q:
        return "I'm doing well. How can I assist you?"

    if "who are you" in q:
        return "I am your AI assistant for analyzing your order data."

    if "thanks" in q or "thank you" in q:
        return "You're welcome!"

    if "bye" in q:
        return "Goodbye! Have a great day."

    return None


# -------------------------
# INTENT DETECTION
# -------------------------

def detect_intent(question: str):
    q = question.lower()

    if any(word in q for word in ["complaint", "issue", "problem", "feedback", "refund", "experience", "late", "delay"]):
        return "vector"

    if any(word in q for word in ["pattern", "behavior", "behaviour", "activity", "trend"]):
        return "pattern"

    if any(word in q for word in ["top", "most", "highest"]):
        return "top"

    if any(word in q for word in ["least", "lowest"]):
        return "least"

    if any(word in q for word in ["average", "avg"]):
        return "average"

    if any(word in q for word in ["total", "sum", "revenue"]):
        return "sum"

    if any(word in q for word in ["how many", "count", "number of"]):
        return "count"

    return "llm_fallback"


# -------------------------
# ANALYTICS HANDLERS
# -------------------------

def handle_pattern(customer):
    total = execute_sql(
        "SELECT COUNT(*) FROM orders WHERE customer_name = %s",
        (customer,)
    )[0][0]

    avg_amount = execute_sql(
        "SELECT ROUND(AVG(amount),2) FROM orders WHERE customer_name = %s",
        (customer,)
    )[0][0]

    last7 = execute_sql(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE customer_name = %s
        AND created_at >= NOW() - INTERVAL 7 DAY
        """,
        (customer,)
    )[0][0]

    return (
        f"{customer} has placed {total} orders in total. "
        f"Their average order value is {avg_amount}. "
        f"They placed {last7} orders in the last 7 days."
    )


def handle_count(question, customer):
    q = question.lower()

    if "last 7" in q and customer:
        count = execute_sql(
            """
            SELECT COUNT(*)
            FROM orders
            WHERE customer_name = %s
            AND created_at >= NOW() - INTERVAL 7 DAY
            """,
            (customer,)
        )[0][0]
        return f"{customer} placed {count} orders in the last 7 days."

    if customer:
        count = execute_sql(
            "SELECT COUNT(*) FROM orders WHERE customer_name = %s",
            (customer,)
        )[0][0]
        return f"{customer} has placed {count} orders."

    count = execute_sql("SELECT COUNT(*) FROM orders")[0][0]
    return f"There are {count} total orders."


def handle_top():
    row = execute_sql("""
        SELECT customer_name, COUNT(*) AS c
        FROM orders
        GROUP BY customer_name
        ORDER BY c DESC
        LIMIT 1
    """)[0]

    return f"{row[0]} is the most active customer with {row[1]} orders."


def handle_least():
    row = execute_sql("""
        SELECT customer_name, COUNT(*) AS c
        FROM orders
        GROUP BY customer_name
        ORDER BY c ASC
        LIMIT 1
    """)[0]

    return f"{row[0]} is the least active customer with {row[1]} orders."


def handle_average(customer):
    if customer:
        avg_val = execute_sql(
            "SELECT ROUND(AVG(amount),2) FROM orders WHERE customer_name = %s",
            (customer,)
        )[0][0]
        return f"The average order value for {customer} is {avg_val}."

    avg_val = execute_sql("SELECT ROUND(AVG(amount),2) FROM orders")[0][0]
    return f"The average order value across all orders is {avg_val}."


def handle_sum(customer):
    if customer:
        total = execute_sql(
            "SELECT ROUND(SUM(amount),2) FROM orders WHERE customer_name = %s",
            (customer,)
        )[0][0]
        return f"{customer} has generated total revenue of {total}."

    total = execute_sql("SELECT ROUND(SUM(amount),2) FROM orders")[0][0]
    return f"The total revenue is {total}."


# -------------------------
# MAIN ENTRY
# -------------------------

def run_query(user_question: str) -> str:

    # 1. Smalltalk first
    smalltalk = handle_smalltalk(user_question)
    if smalltalk:
        return smalltalk

    # 2. Intent detection
    intent = detect_intent(user_question)
    customer = extract_customer(user_question)

    print("Intent:", intent)
    print("Customer:", customer)

    try:
        # 3. Vector layer (semantic questions)
        if intent == "vector":
            results = search(user_question)
            docs = results["documents"][0]

            if not docs:
                return "I could not find relevant records."

            return "Here are relevant results:\n" + "\n".join(f"- {d}" for d in docs)

        # 4. SQL analytics layer
        if intent == "pattern" and customer:
            return handle_pattern(customer)

        if intent == "count":
            return handle_count(user_question, customer)

        if intent == "top":
            return handle_top()

        if intent == "least":
            return handle_least()

        if intent == "average":
            return handle_average(customer)

        if intent == "sum":
            return handle_sum(customer)

        # 5. Fallback to LLM → SQL
        sql_prompt = f"""
You are an expert MySQL generator.

Table:
orders(id, customer_name, amount, created_at)

Return only valid SQL.

Question:
{user_question}
"""
        sql = ask_llama(sql_prompt).replace("```sql", "").replace("```", "").strip()
        print("LLM SQL:", sql)

        result = execute_sql(sql)

        answer_prompt = f"""
Question: {user_question}
Result: {result}

Give a short factual answer. Do not hallucinate.
"""
        return ask_llama(answer_prompt)

    except Exception as e:
        return f"Error: {str(e)}"
