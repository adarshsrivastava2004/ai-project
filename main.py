from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector

from planner_agent import handle   # your AI logic

app = FastAPI()

# -----------------------------
# CORS (for UI later)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="232774",   # <-- change this
        database="aiorders"
    )

# -----------------------------
# REQUEST SCHEMAS
# -----------------------------
class ChatRequest(BaseModel):
    message: str

class OrderRequest(BaseModel):
    customer_name: str
    amount: float

# -----------------------------
# CHAT ENDPOINT (AI)
# -----------------------------
@app.post("/chat")
def chat(req: ChatRequest):
    response = handle(req.message)
    return {"response": response}

# -----------------------------
# ADD ORDER ENDPOINT (LIVE DB)
# -----------------------------
@app.post("/add-order")
def add_order(order: OrderRequest):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
        INSERT INTO orders (customer_name, amount, created_at)
        VALUES (%s, %s, NOW())
        """

        cursor.execute(sql, (order.customer_name, order.amount))
        conn.commit()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Order added for {order.customer_name}",
            "customer": order.customer_name,
            "amount": order.amount
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
