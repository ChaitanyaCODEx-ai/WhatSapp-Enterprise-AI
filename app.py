import os
import json
import gradio as gr
import google.generativeai as genai

# =============================================================
# 1. GEMINI CONFIGURATION
# =============================================================
GEMINI_API_KEY = "AQ.Ab8RN6KpWRcycQR3pLFOTpC27oH-UzEQQYYbAx_YVorF7zgxUw"  # <-- Keep your real key here!

genai.configure(api_key=GEMINI_API_KEY)

# =============================================================
# 2. SYNTHETIC DATA (RAG Knowledge Base & Backend Database)
# =============================================================
KNOWLEDGE_BASE = [
    {
        "topic": "Return & Refund Policy",
        "text": "Customers can return items within 7 days of delivery. Electronics must be sealed and unused. Apparel can be tried on, but tags must remain intact. Refunds take 3 to 5 business days to credit to original payment source."
    },
    {
        "topic": "Exchange Policy",
        "text": "Exchanges are allowed within 7 days of delivery subject to stock availability. If the replacement item is out of stock, store credit or a full refund is immediately issued."
    },
    {
        "topic": "Warranty & Repairs",
        "text": "All electronic items come with a 1-year limited warranty against manufacturing defects. Physical drops, water damage, or unauthorized repairs void the warranty."
    },
    {
        "topic": "Shipping & Cancellation",
        "text": "Orders can be canceled free of charge before they reach 'Shipped' status. Once shipped, the order cannot be canceled and must go through standard return workflow."
    }
]

BACKEND_DB = {
    "orders": {
        "ORD-101": {"customer_id": "CUST-99", "item": "Acoustic Noise-Canceling Headphones", "category": "Electronics", "status": "Delivered", "delivered_days_ago": 2, "price": 120.00},
        "ORD-102": {"customer_id": "CUST-77", "item": "Air Pegasus Running Shoes (Size 9)", "category": "Apparel", "status": "Delivered", "delivered_days_ago": 3, "price": 85.00},
        "ORD-103": {"customer_id": "CUST-44", "item": "RGB Mechanical Keyboard", "category": "Electronics", "status": "Shipped", "delivered_days_ago": None, "price": 95.00}
    },
    "inventory": {
        "Air Pegasus Running Shoes (Size 10)": 4,
        "Air Pegasus Running Shoes (Size 11)": 0,
        "Acoustic Noise-Canceling Headphones": 12
    }
}

# =============================================================
# 3. AGENTIC TOOLS (RAG + Backend Execution Layer)
# =============================================================
last_tool_logs = []

def search_policy_kb(query: str) -> str:
    """Searches company knowledge base for policies on returns, refunds, warranty, and shipping."""
    global last_tool_logs
    last_tool_logs.append({
        "badge": "RAG RETRIEVAL",
        "color": "#00d26a",
        "icon": "🔍",
        "detail": f"Queried verified vector policy store for: <i>'{query}'</i>"
    })
    query_lower = query.lower()
    matches = [
        f"[{doc['topic']}] {doc['text']}"
        for doc in KNOWLEDGE_BASE
        if any(w in doc["text"].lower() or w in doc["topic"].lower() for w in query_lower.split())
    ]
    return "\n\n".join(matches) if matches else KNOWLEDGE_BASE[0]["text"]

def fetch_order_details(order_id: str) -> str:
    """Fetches real-time status and delivery details of an order from the database."""
    global last_tool_logs
    clean_id = order_id.upper().strip()
    last_tool_logs.append({
        "badge": "DATABASE LOOKUP",
        "color": "#00b4d8",
        "icon": "📦",
        "detail": f"Queried Order Management DB for ID: <code>{clean_id}</code>"
    })
    order = BACKEND_DB["orders"].get(clean_id)
    return json.dumps(order) if order else f"Order '{clean_id}' not found."

def check_inventory(item_name: str) -> str:
    """Checks stock availability for product exchanges or replacements."""
    global last_tool_logs
    last_tool_logs.append({
        "badge": "INVENTORY ERP",
        "color": "#f77f00",
        "icon": "📊",
        "detail": f"Live warehouse inventory checked for: <i>'{item_name}'</i>"
    })
    stock = BACKEND_DB["inventory"].get(item_name)
    return f"Stock for '{item_name}': {stock} units." if stock is not None else f"'{item_name}' is not in catalog."

def trigger_return_ticket(order_id: str, action_type: str, reason: str) -> str:
    """Creates a return, refund, or exchange ticket after eligibility is confirmed."""
    global last_tool_logs
    ticket_id = f"TICK-{order_id.upper()[-3:]}-99"
    last_tool_logs.append({
        "badge": "ACTION DISPATCHED",
        "color": "#e63946",
        "icon": "⚡",
        "detail": f"Created {action_type.upper()} Ticket <code>{ticket_id}</code> in Reverse Logistics"
    })
    return f"SUCCESS: {action_type.upper()} ticket {ticket_id} created for order {order_id}. Pickup scheduled within 48 hours."

my_tools = [search_policy_kb, fetch_order_details, check_inventory, trigger_return_ticket]

# =============================================================
# 4. INITIALIZE GEMINI AGENT
# =============================================================
system_instruction = """
You are an autonomous WhatsApp Enterprise Business Assistant for 'Apex Global Retail'.
1. Always ground policy and SLA questions using `search_policy_kb`.
2. When a customer asks about returning, exchanging, or canceling, inspect the order via `fetch_order_details`.
3. Check the 7-day policy window before calling `trigger_return_ticket`.
4. Format replies with bold headings, clean bullet points, and a friendly, professional WhatsApp tone.
"""

model = genai.GenerativeModel(
    model_name="gemini-3.6-flash",
    tools=my_tools,
    system_instruction=system_instruction
)

chat = model.start_chat(enable_automatic_function_calling=True)

# =============================================================
# 5. CHAT FUNCTION (With Styled Squircle Audit Cards)
# =============================================================
def agent_chat(user_message, history):
    global last_tool_logs
    last_tool_logs = []  # reset logs for new turn
    
    if not user_message or not user_message.strip():
        return "Please type a message."

    try:
        response = chat.send_message(user_message)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"Notice: {str(e)}"
        last_tool_logs.append({"badge": "SYSTEM NOTICE", "color": "#e63946", "icon": "❌", "detail": str(e)})

    # Visual Squircle Card for Agentic Execution Trace
    if last_tool_logs:
        trace_html = """
        <br>
        <div style="background: rgba(11, 20, 26, 0.85); border: 1px solid rgba(0, 168, 132, 0.4); border-radius: 16px; padding: 14px 20px; margin-top: 14px; box-shadow: 0 4px 18px rgba(0,0,0,0.35);">
            <div style="font-size: 0.88em; font-weight: 800; color: #25d366; letter-spacing: 0.8px; text-transform: uppercase; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                <span>🤖</span> Autonomous Agentic Execution Trace (Live Tools)
            </div>
        """
        for log in last_tool_logs:
            trace_html += f"""
            <div style="display: flex; align-items: baseline; gap: 10px; margin: 8px 0; font-size: 0.92em; line-height: 1.5;">
                <span style="background: {log['color']}; color: #000; font-size: 0.74em; font-weight: 800; padding: 3px 10px; border-radius: 6px; letter-spacing: 0.6px; white-space: nowrap;">{log['badge']}</span>
                <span style="color: #e9edef;">{log['detail']}</span>
            </div>
            """
        trace_html += "</div>"
        return bot_reply + trace_html
    else:
        return bot_reply

# =============================================================
# 6. WIDE-SCREEN WHATSAPP WEB UI
# =============================================================
custom_css = """
/* Full-Screen Modern Executive Dark Backdrop */
html, body, gradio-app {
    min-height: 100vh !important;
    background: radial-gradient(circle at 20% 20%, #0d2b24 0%, #0b141a 45%, #050b0e 95%) !important;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif !important;
    margin: 0 !important;
    padding: 10px 0 !important;
}

/* Wide-Screen Responsive Container (Breaks out of narrow box) */
.gradio-container {
    max-width: 1320px !important;
    width: 95% !important;
    margin: 15px auto !important;
    background: rgba(17, 27, 33, 0.9) !important;
    border: 1px solid rgba(0, 168, 132, 0.3) !important;
    border-radius: 24px !important;
    box-shadow: 0 25px 65px rgba(0, 0, 0, 0.65), 0 0 30px rgba(0, 168, 132, 0.12) !important;
    backdrop-filter: blur(25px) !important;
}

/* Header Styling */
#wa-topbar {
    background: linear-gradient(135deg, #075e54 0%, #008069 55%, #128c7e 100%);
    padding: 18px 28px;
    border-radius: 24px 24px 0 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.wa-brand {
    display: flex;
    align-items: center;
    gap: 18px;
}

.wa-avatar-badge {
    width: 54px;
    height: 54px;
    border-radius: 16px;
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.wa-title-group h1 {
    margin: 0 !important;
    font-size: 1.5rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    display: flex;
    align-items: center;
    gap: 8px;
}

.wa-verified {
    background: #25d366;
    color: #075e54;
    font-size: 13px;
    font-weight: 900;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.wa-status-text {
    margin: 4px 0 0 0;
    font-size: 0.88rem;
    color: #a7f3d0;
    display: flex;
    align-items: center;
    gap: 8px;
}

.pulsing-dot {
    width: 9px;
    height: 9px;
    background-color: #25d366;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.7);
    animation: pulse 1.8s infinite;
}

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.7); }
    70% { box-shadow: 0 0 0 8px rgba(37, 211, 102, 0); }
    100% { box-shadow: 0 0 0 0 rgba(37, 211, 102, 0); }
}

.wa-pill-tag {
    background: rgba(255, 255, 255, 0.15);
    color: #ffffff;
    padding: 7px 18px;
    border-radius: 30px;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    border: 1px solid rgba(255, 255, 255, 0.25);
}

/* Chat & Inputs Styling */
textarea, input[type="text"] {
    border-radius: 20px !important;
    padding: 14px 20px !important;
    font-size: 1rem !important;
    background: rgba(32, 44, 51, 0.9) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    color: #e9edef !important;
}

textarea:focus, input[type="text"]:focus {
    border-color: #25d366 !important;
    box-shadow: 0 0 14px rgba(37, 211, 102, 0.3) !important;
}

button.primary {
    background: linear-gradient(135deg, #00a884 0%, #25d366 100%) !important;
    color: #0b141a !important;
    font-weight: 800 !important;
    border-radius: 20px !important;
    font-size: 0.95rem !important;
    border: none !important;
}
"""

with gr.Blocks(title="WhatsApp Enterprise AI") as demo:
    # Full-Width Header
    gr.HTML("""
        <div id="wa-topbar">
            <div class="wa-brand">
                <div class="wa-avatar-badge">🛍️</div>
                <div class="wa-title-group">
                    <h1>Apex Global Store <span class="wa-verified">✓</span></h1>
                    <div class="wa-status-text">
                        <span class="pulsing-dot"></span> Online &bull; Replies Instantly &bull; Verified WhatsApp Cloud API
                    </div>
                </div>
            </div>
            <div class="wa-pill-tag">Meta Enterprise Concierge</div>
        </div>
    """)
    
    # Spacious Chatbot Interface
    gr.ChatInterface(
        fn=agent_chat,
        chatbot=gr.Chatbot(height=560),  # Taller, spacious window!
        textbox=gr.Textbox(
            placeholder="Type a message (e.g. 'What is your return policy?', 'Can I return order ORD-101?')...",
            container=False,
            scale=8
        ),
        examples=[
            "What is your return policy for apparel?",
            "Where is my order ORD-102?",
            "I want to return the headphones in order ORD-101 because they don't fit.",
            "Can I exchange my shoes for Size 10?"
        ]
    )

if __name__ == "__main__":
    demo.launch(css=custom_css)