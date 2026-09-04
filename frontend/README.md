# Smart Market Watchlist

A full-stack market watchlist that focuses on one simple question:

> **What meaningfully changed since I last checked?**

Instead of only showing today's stock movement, Smart Market Watchlist remembers the price at which a user last reviewed each stock and highlights movements that happened while they were away.

## The Problem

Traditional watchlists mainly display current price and daily percentage change.

But when users return to a watchlist, the more useful question is often:

**"What changed since I last looked?"**

Smart Market Watchlist is designed around that idea.

## Key Features

- Add NSE-listed stocks using their trading symbol
- Fetch latest market information using the Upstox API
- Display current stock price
- Display today's percentage movement
- Track movement since the user's last review
- Flag meaningful changes that need attention
- Mark a stock as seen to establish a new comparison baseline
- Persist watchlist state using a backend database
- Generate a short Smart Insight explaining whether a movement deserves attention
- Graceful fallback when the external AI service is unavailable

## What Makes It Different?

A normal watchlist may tell a user:

`TCS is down 0.7% today.`

Smart Market Watchlist additionally answers:

`How much has TCS moved since I last reviewed it?`

Each stock stores a **last-seen price**.

The application calculates:

`Change Since Last Check = ((Current Price - Last Seen Price) / Last Seen Price) × 100`

For the MVP, an absolute movement of **3% or more** is considered meaningful and is labelled **Needs Attention**.

Smaller movements are labelled **No Major Change**.

The threshold is intentionally simple and explainable rather than being a black-box signal.

## Mark as Seen

Refreshing the page does not automatically erase an unseen movement.

A user explicitly clicks **Mark as Seen** after reviewing a stock.

That price then becomes the new baseline for future comparisons.

This separates:

- receiving new market data
- acknowledging a meaningful change

## Smart Insights

The backend includes an OpenAI integration that can generate a short natural-language explanation of a stock's movement.

The feature is designed to explain whether the movement crosses the application's attention threshold — **not to provide investment advice**.

If the AI service is unavailable, rate-limited, or has insufficient quota, the application falls back to a deterministic explanation so the core product continues to work.

## Tech Stack

### Frontend
- React
- Vite
- CSS

### Backend
- FastAPI
- Python
- SQLAlchemy

### Database
- SQLite for the MVP

### External Services
- Upstox API for market data
- OpenAI API for optional natural-language insights

## Architecture

`React Frontend → FastAPI Backend → SQLite Database`

The backend communicates with:

`FastAPI → Upstox Market Data API`

and optionally:

`FastAPI → OpenAI API`

The frontend never directly accesses private API credentials.

## Persistence

The MVP stores watchlist data and last-seen prices in SQLite.

This allows the application to preserve the user's comparison baseline across sessions on the same backend instance.

For a production multi-user system, SQLite would be replaced with a managed database such as PostgreSQL and watchlists would be associated with authenticated user accounts. This would enable reliable cross-device persistence.

## Handling External Service Failures

External APIs should not make the entire watchlist unusable.

The application therefore separates the core watchlist logic from optional external functionality.

For AI insights, a deterministic fallback is returned if the AI provider is unavailable.

For market data, the architecture is designed so previously stored values can be retained when a fresh quote cannot be obtained. A production version would additionally expose explicit freshness timestamps and cached/stale indicators to the user.

## Scaling the System

For a production-scale implementation:

- SQLite → PostgreSQL
- Add authenticated user accounts
- Cache frequently requested quotes using Redis
- Batch market-data requests where possible
- Introduce background workers for quote updates
- Add rate-limit handling and retry policies
- Run multiple FastAPI instances behind a load balancer
- Store explicit market-data freshness timestamps
- Use WebSockets for real-time updates where required

The MVP intentionally prioritizes a clear product idea and simple architecture over unnecessary infrastructure.

## Running Locally

### Backend

Create a `.env` file inside `backend/` containing the required credentials.

Example:

```env
UPSTOX_API_KEY=your_key
UPSTOX_API_SECRET=your_secret
UPSTOX_REDIRECT_URI=your_redirect_uri
UPSTOX_ACCESS_TOKEN=your_access_token
OPENAI_API_KEY=your_openai_key