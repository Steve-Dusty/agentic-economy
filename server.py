"""Seller agent — FastAPI server with x402 payment middleware.

Accepts payments on crypto (USDC) and fiat (Stripe) plans.
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import OpenAI
from payments_py import Payments, PaymentOptions
from payments_py.x402.fastapi import PaymentMiddleware

load_dotenv()

# --- Config ---
PLAN_ID_CRYPTO = os.environ["NVM_PLAN_ID_CRYPTO"]
PLAN_ID_FIAT = os.environ.get("NVM_PLAN_ID_FIAT", "")
AGENT_ID_CRYPTO = os.environ.get("NVM_AGENT_ID_CRYPTO", "")
AGENT_ID = os.environ.get("NVM_AGENT_ID", "")  # linked to fiat plan

# --- Payments SDK ---
payments = Payments.get_instance(
    PaymentOptions(
        nvm_api_key=os.environ["NVM_API_KEY"],
        environment=os.environ.get("NVM_ENVIRONMENT", "sandbox"),
    )
)

# --- OpenAI client ---
llm = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# --- FastAPI app ---
app = FastAPI(title="AI Research Seller Agent")

# Build routes for each plan — separate paths per payment method
routes = {
    # Crypto (USDC) endpoints
    "POST /api/crypto/ask": {
        "plan_id": PLAN_ID_CRYPTO,
        "agent_id": AGENT_ID_CRYPTO,
        "credits": 1,
    },
    "POST /api/crypto/summarize": {
        "plan_id": PLAN_ID_CRYPTO,
        "agent_id": AGENT_ID_CRYPTO,
        "credits": 3,
    },
}

if PLAN_ID_FIAT:
    routes.update({
        # Fiat (Stripe) endpoints
        "POST /api/fiat/ask": {
            "plan_id": PLAN_ID_FIAT,
            "agent_id": AGENT_ID,
            "credits": 1,
        },
        "POST /api/fiat/summarize": {
            "plan_id": PLAN_ID_FIAT,
            "agent_id": AGENT_ID,
            "credits": 3,
        },
    })

app.add_middleware(PaymentMiddleware, payments=payments, routes=routes)


# --- Free endpoints ---

@app.get("/")
async def root():
    return {"service": "AI Research Agent", "status": "running"}


@app.get("/pricing")
async def pricing():
    plans = {
        "crypto": {
            "plan_id": PLAN_ID_CRYPTO,
            "agent_id": AGENT_ID_CRYPTO,
            "endpoints": {
                "POST /api/crypto/ask": {"credits": 1, "description": "Ask any question (pay with USDC)"},
                "POST /api/crypto/summarize": {"credits": 3, "description": "Summarize text (pay with USDC)"},
            },
        },
    }
    if PLAN_ID_FIAT:
        plans["fiat"] = {
            "plan_id": PLAN_ID_FIAT,
            "agent_id": AGENT_ID,
            "endpoints": {
                "POST /api/fiat/ask": {"credits": 1, "description": "Ask any question (pay with card)"},
                "POST /api/fiat/summarize": {"credits": 3, "description": "Summarize text (pay with card)"},
            },
        }
    return plans


# --- Shared handler ---

async def _ask(request: Request):
    body = await request.json()
    query = body.get("query", "")
    if not query:
        return JSONResponse(status_code=400, content={"error": "Missing 'query' field"})
    response = llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful research assistant. Provide concise, factual answers."},
            {"role": "user", "content": query},
        ],
        max_tokens=1024,
    )
    return {"query": query, "answer": response.choices[0].message.content}


async def _summarize(request: Request):
    body = await request.json()
    text = body.get("text", "")
    if not text:
        return JSONResponse(status_code=400, content={"error": "Missing 'text' field"})
    response = llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize the following text concisely. Capture key points and main ideas."},
            {"role": "user", "content": text},
        ],
        max_tokens=512,
    )
    return {"summary": response.choices[0].message.content}


# --- Paid endpoints (protected by middleware) ---

@app.post("/api/crypto/ask")
async def crypto_ask(request: Request):
    return await _ask(request)

@app.post("/api/crypto/summarize")
async def crypto_summarize(request: Request):
    return await _summarize(request)

@app.post("/api/fiat/ask")
async def fiat_ask(request: Request):
    return await _ask(request)

@app.post("/api/fiat/summarize")
async def fiat_summarize(request: Request):
    return await _summarize(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
