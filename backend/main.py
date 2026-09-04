import os
import requests

from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, WatchlistStock, StockSnapshot
from market_data import get_stock_quote, get_stock_by_symbol

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path, override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = OpenAI(
    api_key=OPENAI_API_KEY
)

UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET")
UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI")

upstox_access_token = os.getenv("UPSTOX_ACCESS_TOKEN")

print("UPSTOX TOKEN LOADED:", bool(upstox_access_token))

app = FastAPI()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StockCreate(BaseModel):
    symbol: str


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {
        "status": "Smart Market Watchlist backend is running"
    }


@app.get("/watchlist")
def get_watchlist(db: Session = Depends(get_db)):
    stocks = db.query(WatchlistStock).all()
    result = []

    for stock in stocks:

        # Keep the old stored price as baseline for existing stocks
        if stock.last_seen_price is None:
            stock.last_seen_price = stock.price
            stock.last_seen_at = datetime.utcnow()

        market_stock = get_stock_by_symbol(stock.symbol)

        # If live API works, update latest price
        if market_stock:
            stock.price = market_stock["price"]
            stock.previous_price = market_stock["previous_close"]

        current_price = stock.price
        last_seen_price = stock.last_seen_price

        if last_seen_price == 0:
            since_last_check = 0
        else:
            since_last_check = (
                (current_price - last_seen_price)
                / last_seen_price
            ) * 100

        if stock.previous_price == 0:
            day_change = 0
        else:
            day_change = (
                (current_price - stock.previous_price)
                / stock.previous_price
            ) * 100

        result.append({
            "id": stock.id,
            "symbol": stock.symbol,
            "name": stock.name,
            "price": current_price,
            "day_change_percent": round(day_change, 2),
            "since_last_check_percent": round(since_last_check, 2),
            "meaningful_change": abs(since_last_check) >= 3,
            "last_seen_at": stock.last_seen_at
        })

    db.commit()

    return result

@app.post("/watchlist")
def add_stock(
    stock: StockCreate,
    db: Session = Depends(get_db)
):
    symbol = stock.symbol.upper().strip()

    existing_stock = (
        db.query(WatchlistStock)
        .filter(WatchlistStock.symbol == symbol)
        .first()
    )

    if existing_stock:
        raise HTTPException(
            status_code=400,
            detail="Stock already exists in watchlist"
        )

    market_stock = get_stock_by_symbol(symbol)

    if not market_stock:
        raise HTTPException(
            status_code=404,
            detail="Stock not found or market data unavailable"
        )

    new_stock = WatchlistStock(
        symbol=symbol,
        name=market_stock["name"],
        price=market_stock["price"],
        previous_price=market_stock["previous_close"],
        last_seen_price=market_stock["price"],
        last_seen_at=datetime.utcnow()
        )

    db.add(new_stock)
    db.commit()
    db.refresh(new_stock)

    snapshot = StockSnapshot(
        symbol=symbol,
        price=market_stock["price"]
    )

    db.add(snapshot)
    db.commit()

    return {
        "message": "Stock added successfully",
        "stock": {
            "symbol": new_stock.symbol,
            "name": new_stock.name,
            "price": new_stock.price,
            "previous_close": new_stock.previous_price,
            "volume": market_stock["volume"]
        }
    }


@app.delete("/watchlist/{symbol}")
def remove_stock(
    symbol: str,
    db: Session = Depends(get_db)
):
    stock = (
        db.query(WatchlistStock)
        .filter(
            WatchlistStock.symbol == symbol.upper()
        )
        .first()
    )

    if not stock:
        raise HTTPException(
            status_code=404,
            detail="Stock not found"
        )

    db.delete(stock)
    db.commit()

    return {
        "message": f"{symbol.upper()} removed successfully"
    }

@app.get("/upstox/login")
def upstox_login():
    auth_url = (
        "https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code"
        f"&client_id={UPSTOX_API_KEY}"
        f"&redirect_uri={UPSTOX_REDIRECT_URI}"
    )

    return RedirectResponse(auth_url)

@app.post("/watchlist/{symbol}/mark-seen")
def mark_stock_as_seen(
    symbol: str,
    db: Session = Depends(get_db)
):
    stock = (
        db.query(WatchlistStock)
        .filter(WatchlistStock.symbol == symbol.upper())
        .first()
    )

    if not stock:
        raise HTTPException(
            status_code=404,
            detail="Stock not found"
        )

    market_stock = get_stock_by_symbol(stock.symbol)

    if market_stock:
        stock.price = market_stock["price"]
        stock.previous_price = market_stock["previous_close"]

    stock.last_seen_price = stock.price
    stock.last_seen_at = datetime.utcnow()

    db.commit()

    return {
        "message": f"{stock.symbol} marked as seen",
        "price": stock.price
    }

@app.get("/upstox/callback")
def upstox_callback(code: str):
    global upstox_access_token

    url = "https://api.upstox.com/v2/login/authorization/token"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "code": code,
        "client_id": UPSTOX_API_KEY,
        "client_secret": UPSTOX_API_SECRET,
        "redirect_uri": UPSTOX_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    response = requests.post(
        url,
        headers=headers,
        data=data
    )

    result = response.json()

    if "access_token" not in result:
        return {
            "status": "error",
            "details": result
        }

    upstox_access_token = result["access_token"]

    return {
        "status": "success",
        "message": "Upstox connected successfully"
    }


@app.get("/upstox/test-price")
def test_upstox_price():
    if not upstox_access_token:
        return {
            "status": "error",
            "message": "Upstox is not connected. Please login first."
        }

    instrument_key = "NSE_EQ|INE002A01018"

    url = "https://api.upstox.com/v3/market-quote/ltp"

    headers = {
        "Authorization": f"Bearer {upstox_access_token}",
        "Accept": "application/json"
    }

    params = {
        "instrument_key": instrument_key
    }

    response = requests.get(
        url,
        headers=headers,
        params=params
    )

    return response.json()

@app.get("/market/test")
def market_test():

    reliance_key = "NSE_EQ|INE002A01018"

    data = get_stock_quote(reliance_key)

    if not data:
        raise HTTPException(
            status_code=503,
            detail="Unable to fetch market data"
        )

    return data

@app.get("/watchlist/{symbol}/ai-insight")
def get_ai_insight(
    symbol: str,
    db: Session = Depends(get_db)
):
    stock = (
        db.query(WatchlistStock)
        .filter(WatchlistStock.symbol == symbol.upper())
        .first()
    )

    if not stock:
        raise HTTPException(
            status_code=404,
            detail="Stock not found"
        )

    current_price = stock.price
    last_seen_price = stock.last_seen_price or stock.price

    if last_seen_price == 0:
        change = 0
    else:
        change = (
            (current_price - last_seen_price)
            / last_seen_price
        ) * 100

    prompt = f"""
You are an assistant inside a stock market watchlist.

Explain this stock movement in one short, simple sentence.

Stock: {stock.symbol}
Company: {stock.name}
Current price: INR {current_price}
Price when user last reviewed it: INR {last_seen_price}
Change since last review: {change:.2f}%
Attention threshold: 3%

Explain whether the movement deserves attention.
Do not give buy, sell, hold, investment, or financial advice.
"""

    try:
        response = openai_client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )

        return {
            "symbol": stock.symbol,
            "insight": response.output_text
        }

    except Exception as e:
        print("AI insight error:", e)

        # Fallback so our app still works if AI API fails
        if abs(change) >= 3:
            insight = (
                f"{stock.symbol} has moved {abs(change):.2f}% "
                "since your last review, crossing the 3% attention threshold."
            )
        else:
            insight = (
                f"{stock.symbol} has moved {abs(change):.2f}% "
                "since your last review, so no major change is detected."
            )

        return {
            "symbol": stock.symbol,
            "insight": insight,
            "source": "fallback"
        }