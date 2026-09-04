import { useEffect, useState } from "react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
  const [stocks, setStocks] = useState([]);
  const [symbol, setSymbol] = useState("");
  const [insights, setInsights] = useState({});
  const [loadingInsight, setLoadingInsight] = useState({});

  const fetchStocks = () => {
    fetch(`${API_URL}/watchlist`)
      .then((response) => response.json())
      .then((data) => setStocks(data))
      .catch((error) => console.error("Error:", error));
  };

  useEffect(() => {
    fetchStocks();
  }, []);

  const addStock = async () => {
    if (!symbol.trim()) {
      alert("Please enter a stock symbol");
      return;
    }

    const response = await fetch(`${API_URL}/watchlist`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        symbol: symbol.trim(),
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      alert(error.detail);
      fetchStocks();
      return;
    }

    setSymbol("");
    fetchStocks();
  };

  const removeStock = async (symbol) => {
    await fetch(`${API_URL}/watchlist/${symbol}`, {
      method: "DELETE",
    });

    setInsights((prev) => {
      const updated = { ...prev };
      delete updated[symbol];
      return updated;
    });

    fetchStocks();
  };

  const markAsSeen = async (symbol) => {
    await fetch(`${API_URL}/watchlist/${symbol}/mark-seen`, {
      method: "POST",
    });

    setInsights((prev) => {
      const updated = { ...prev };
      delete updated[symbol];
      return updated;
    });

    fetchStocks();
  };

  const getAIInsight = async (symbol) => {
    setLoadingInsight((prev) => ({
      ...prev,
      [symbol]: true,
    }));

    try {
      const response = await fetch(
        `${API_URL}/watchlist/${symbol}/ai-insight`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to generate insight");
      }

      setInsights((prev) => ({
        ...prev,
        [symbol]: data.insight,
      }));
    } catch (error) {
      setInsights((prev) => ({
        ...prev,
        [symbol]: "Unable to generate insight right now.",
      }));
    } finally {
      setLoadingInsight((prev) => ({
        ...prev,
        [symbol]: false,
      }));
    }
  };

  return (
    <div className="app">
      <h1>Smart Market Watchlist</h1>

      <p className="subtitle">
        See what has meaningfully changed since your last check.
      </p>

      <div className="add-stock-box">
        <h2>Add Stock</h2>

        <input
          placeholder="Enter symbol e.g. RELIANCE"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              addStock();
            }
          }}
        />

        <button onClick={addStock}>
          Add to Watchlist
        </button>
      </div>

      <div className="watchlist">
        {stocks.map((stock) => (
          <div className="stock-card" key={stock.symbol}>
            <div className="stock-main">
              <div className="stock-name">
                <h2>{stock.symbol}</h2>
                <p>{stock.name}</p>
              </div>

              <div className="stock-info">
                <h3>₹{stock.price}</h3>

                <div>
                  <small>Today</small>
                  <span
                    className={
                      stock.day_change_percent >= 0
                        ? "positive"
                        : "negative"
                    }
                  >
                    {stock.day_change_percent >= 0 ? "+" : ""}
                    {stock.day_change_percent}%
                  </span>
                </div>

                <div>
                  <small>Since last check</small>
                  <span
                    className={
                      stock.since_last_check_percent >= 0
                        ? "positive"
                        : "negative"
                    }
                  >
                    {stock.since_last_check_percent >= 0 ? "+" : ""}
                    {stock.since_last_check_percent}%
                  </span>
                </div>

                <span
                  className={
                    stock.meaningful_change
                      ? "meaningful"
                      : "not-meaningful"
                  }
                >
                  {stock.meaningful_change
                    ? "Needs Attention"
                    : "No Major Change"}
                </span>

                <button
                  className="ai-btn"
                  onClick={() => getAIInsight(stock.symbol)}
                  disabled={loadingInsight[stock.symbol]}
                >
                  {loadingInsight[stock.symbol]
                    ? "Generating..."
                    : "Smart Insight"}
                </button>

                <button
                  className="seen-btn"
                  onClick={() => markAsSeen(stock.symbol)}
                >
                  Mark as Seen
                </button>

                <button
                  className="remove-btn"
                  onClick={() => removeStock(stock.symbol)}
                >
                  Remove
                </button>
              </div>
            </div>

            {insights[stock.symbol] && (
              <div className="ai-insight-box">
                <strong>Smart Insight</strong>
                <p>{insights[stock.symbol]}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;