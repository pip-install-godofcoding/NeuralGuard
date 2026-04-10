"use client";

import { useState, useRef, useEffect } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────
interface SearchResult {
  answer: string;
  modelRequested: string;
  modelUsed: string;
  cacheHit: boolean;
  latencyMs: number;
  trustScore: number | null;
  tokenUsage: number;
}

// ─── Trust Score Gauge ───────────────────────────────────────────────────────
function TrustGauge({ score }: { score: number | null }) {
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    if (score === null) return;
    let start = 0;
    const end = score;
    const duration = 1200;
    const step = (end / duration) * 16;
    const timer = setInterval(() => {
      start += step;
      if (start >= end) {
        setDisplayed(end);
        clearInterval(timer);
      } else {
        setDisplayed(Math.floor(start));
      }
    }, 16);
    return () => clearInterval(timer);
  }, [score]);

  const color =
    score === null
      ? "#475569"
      : score >= 75
      ? "#10b981"
      : score >= 45
      ? "#f59e0b"
      : "#ef4444";

  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const progress =
    score !== null ? ((100 - displayed) / 100) * circumference : circumference;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
      <svg width="100" height="100" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={progress}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.05s linear, stroke 0.3s ease" }}
        />
      </svg>
      <div style={{ marginTop: "-72px", textAlign: "center", position: "relative" }}>
        <span style={{ fontSize: "22px", fontWeight: 700, color }}>
          {score === null ? "—" : displayed}
        </span>
        {score !== null && (
          <span style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)", display: "block" }}>
            / 100
          </span>
        )}
      </div>
      <div style={{ marginTop: "36px", fontSize: "11px", color: "rgba(255,255,255,0.5)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        Trust Score
      </div>
    </div>
  );
}

// ─── Animated Background Orbs ────────────────────────────────────────────────
function BackgroundOrbs() {
  return (
    <div style={{ position: "fixed", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 0 }}>
      <div style={{
        position: "absolute", top: "-20%", left: "-10%",
        width: "600px", height: "600px",
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)",
        animation: "orbFloat1 12s ease-in-out infinite",
      }} />
      <div style={{
        position: "absolute", bottom: "-20%", right: "-10%",
        width: "500px", height: "500px",
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%)",
        animation: "orbFloat2 15s ease-in-out infinite",
      }} />
      <div style={{
        position: "absolute", top: "40%", right: "20%",
        width: "300px", height: "300px",
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(16,185,129,0.08) 0%, transparent 70%)",
        animation: "orbFloat1 18s ease-in-out infinite reverse",
      }} />
      <style>{`
        @keyframes orbFloat1 {
          0%,100% { transform: translate(0,0) scale(1); }
          50% { transform: translate(30px,-40px) scale(1.05); }
        }
        @keyframes orbFloat2 {
          0%,100% { transform: translate(0,0) scale(1); }
          50% { transform: translate(-40px,30px) scale(1.08); }
        }
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(24px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse-ring {
          0% { box-shadow: 0 0 0 0 rgba(99,102,241,0.4); }
          70% { box-shadow: 0 0 0 12px rgba(99,102,241,0); }
          100% { box-shadow: 0 0 0 0 rgba(99,102,241,0); }
        }
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────
export default function SearchPage() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  async function handleSearch(e?: React.FormEvent) {
    e?.preventDefault();
    if (!prompt.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Unknown error");
      setResult(data);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  }

  const routingDowngraded =
    result && result.modelUsed !== result.modelRequested;

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #020617 0%, #0f0a2e 50%, #020617 100%)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      fontFamily: "'Inter', sans-serif",
      position: "relative",
    }}>
      <BackgroundOrbs />

      {/* Hero Section */}
      <div style={{
        position: "relative", zIndex: 1,
        display: "flex", flexDirection: "column", alignItems: "center",
        paddingTop: result ? "60px" : "15vh",
        paddingBottom: "40px",
        transition: "padding-top 0.5s ease",
        width: "100%",
        maxWidth: "760px",
        padding: result ? "60px 20px 40px" : "15vh 20px 40px",
      }}>

        {/* Logo */}
        <div style={{ marginBottom: "12px", display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            width: "40px", height: "40px",
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            borderRadius: "10px",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 0 24px rgba(99,102,241,0.4)",
          }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span style={{
            fontSize: "26px", fontWeight: 800, letterSpacing: "-0.02em",
            background: "linear-gradient(135deg, #818cf8, #6366f1, #a78bfa)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            NeuralGuard
          </span>
        </div>

        {!result && (
          <p style={{
            color: "rgba(255,255,255,0.4)", fontSize: "15px",
            marginBottom: "36px", textAlign: "center",
            lineHeight: 1.6, maxWidth: "420px",
          }}>
            Intelligent LLM proxy with semantic caching, smart routing & trust scoring
          </p>
        )}

        {/* Search Bar */}
        <form onSubmit={handleSearch} style={{ width: "100%", position: "relative" }}>
          <div style={{
            position: "relative",
            borderRadius: "16px",
            background: "rgba(255,255,255,0.06)",
            border: `1px solid ${focused ? "rgba(99,102,241,0.7)" : "rgba(255,255,255,0.12)"}`,
            backdropFilter: "blur(20px)",
            boxShadow: focused
              ? "0 0 0 3px rgba(99,102,241,0.15), 0 8px 32px rgba(0,0,0,0.4)"
              : "0 8px 32px rgba(0,0,0,0.3)",
            transition: "all 0.25s ease",
          }}>
            <textarea
              ref={textareaRef}
              id="search-input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder="Ask anything… (Enter to search, Shift+Enter for new line)"
              rows={3}
              style={{
                width: "100%", boxSizing: "border-box",
                background: "transparent",
                border: "none", outline: "none",
                color: "rgba(255,255,255,0.92)",
                fontSize: "16px", lineHeight: 1.6,
                padding: "18px 60px 18px 20px",
                resize: "none",
                fontFamily: "inherit",
              }}
            />
            <button
              type="submit"
              id="search-btn"
              disabled={!prompt.trim() || loading}
              style={{
                position: "absolute", right: "12px", bottom: "12px",
                width: "40px", height: "40px",
                borderRadius: "10px",
                background: prompt.trim() && !loading
                  ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
                  : "rgba(255,255,255,0.08)",
                border: "none", cursor: prompt.trim() && !loading ? "pointer" : "default",
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.2s ease",
                animation: prompt.trim() && !loading ? "pulse-ring 2s infinite" : "none",
              }}
            >
              {loading ? (
                <div style={{
                  width: "18px", height: "18px",
                  border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "white",
                  borderRadius: "50%",
                  animation: "spin 0.7s linear infinite",
                }} />
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12h14M12 5l7 7-7 7" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </button>
          </div>
          <p style={{ color: "rgba(255,255,255,0.2)", fontSize: "12px", marginTop: "8px", textAlign: "center" }}>
            Powered by NeuralGuard Proxy · Groq backend
          </p>
        </form>

        {/* Error */}
        {error && (
          <div style={{
            marginTop: "20px", padding: "14px 18px",
            background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: "12px", color: "#fca5a5", fontSize: "14px",
            width: "100%", animation: "fadeSlideUp 0.3s ease",
          }}>
            ⚠ {error}
          </div>
        )}
      </div>

      {/* Results Panel */}
      {result && (
        <div
          ref={resultsRef}
          style={{
            position: "relative", zIndex: 1,
            width: "100%", maxWidth: "760px",
            padding: "0 20px 80px",
            animation: "fadeSlideUp 0.4s ease",
          }}
        >
          {/* Meta Badges Row */}
          <div style={{
            display: "flex", flexWrap: "wrap", gap: "10px",
            marginBottom: "20px",
          }}>
            {/* Cache Hit */}
            <div style={{
              display: "flex", alignItems: "center", gap: "7px",
              padding: "8px 14px", borderRadius: "999px",
              background: result.cacheHit ? "rgba(16,185,129,0.15)" : "rgba(255,255,255,0.07)",
              border: `1px solid ${result.cacheHit ? "rgba(16,185,129,0.4)" : "rgba(255,255,255,0.1)"}`,
              fontSize: "13px", fontWeight: 600,
              color: result.cacheHit ? "#34d399" : "rgba(255,255,255,0.5)",
            }}>
              <span style={{ fontSize: "16px" }}>{result.cacheHit ? "⚡" : "🔮"}</span>
              {result.cacheHit ? "Served from Cache" : "Fresh LLM Call"}
            </div>

            {/* Latency */}
            <div style={{
              display: "flex", alignItems: "center", gap: "7px",
              padding: "8px 14px", borderRadius: "999px",
              background: "rgba(255,255,255,0.07)",
              border: "1px solid rgba(255,255,255,0.1)",
              fontSize: "13px", fontWeight: 600,
              color: "rgba(255,255,255,0.6)",
            }}>
              <span style={{ fontSize: "16px" }}>⏱</span>
              {result.latencyMs}ms
            </div>

            {/* Tokens */}
            {result.tokenUsage > 0 && (
              <div style={{
                display: "flex", alignItems: "center", gap: "7px",
                padding: "8px 14px", borderRadius: "999px",
                background: "rgba(255,255,255,0.07)",
                border: "1px solid rgba(255,255,255,0.1)",
                fontSize: "13px", fontWeight: 600,
                color: "rgba(255,255,255,0.6)",
              }}>
                <span style={{ fontSize: "16px" }}>🎯</span>
                {result.tokenUsage} tokens
              </div>
            )}

            {/* Model Routing */}
            <div style={{
              display: "flex", alignItems: "center", gap: "7px",
              padding: "8px 14px", borderRadius: "999px",
              background: routingDowngraded ? "rgba(245,158,11,0.12)" : "rgba(255,255,255,0.07)",
              border: `1px solid ${routingDowngraded ? "rgba(245,158,11,0.35)" : "rgba(255,255,255,0.1)"}`,
              fontSize: "13px", fontWeight: 600,
              color: routingDowngraded ? "#fbbf24" : "rgba(255,255,255,0.5)",
            }}>
              <span style={{ fontSize: "16px" }}>🔀</span>
              {routingDowngraded ? (
                <span>
                  <span style={{ textDecoration: "line-through", opacity: 0.6 }}>{result.modelRequested}</span>
                  {" → "}
                  <span>{result.modelUsed}</span>
                </span>
              ) : (
                <span>{result.modelUsed}</span>
              )}
            </div>
          </div>

          {/* Answer Card */}
          <div style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            backdropFilter: "blur(20px)",
            borderRadius: "16px",
            padding: "24px",
            marginBottom: "16px",
          }}>
            <div style={{
              fontSize: "11px", fontWeight: 600, letterSpacing: "0.1em",
              color: "rgba(255,255,255,0.35)", textTransform: "uppercase",
              marginBottom: "14px",
            }}>
              Answer
            </div>
            <p style={{
              color: "rgba(255,255,255,0.88)",
              fontSize: "15px", lineHeight: 1.75,
              whiteSpace: "pre-wrap", margin: 0,
            }}>
              {result.answer}
            </p>
          </div>

          {/* Trust Score Card */}
          <div style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
            backdropFilter: "blur(20px)",
            borderRadius: "16px",
            padding: "24px",
            display: "flex", alignItems: "center", gap: "28px",
          }}>
            <TrustGauge score={result.trustScore} />
            <div>
              <div style={{
                fontSize: "15px", fontWeight: 600,
                color: "rgba(255,255,255,0.85)", marginBottom: "6px",
              }}>
                {result.trustScore === null
                  ? "Trust score pending…"
                  : result.trustScore >= 75
                  ? "High factual confidence"
                  : result.trustScore >= 45
                  ? "Moderate confidence — verify key facts"
                  : "Low confidence — treat with caution"}
              </div>
              <p style={{
                margin: 0, fontSize: "13px",
                color: "rgba(255,255,255,0.35)", lineHeight: 1.6,
              }}>
                {result.trustScore === null
                  ? "The trust engine scores responses asynchronously. The score will appear on your next identical query (served from cache)."
                  : `Factuality evaluated asynchronously by the NeuralGuard trust engine using a scoring LLM.`}
              </p>
            </div>
          </div>

          {/* Try Again */}
          <div style={{ textAlign: "center", marginTop: "28px" }}>
            <button
              id="new-search-btn"
              onClick={() => { setResult(null); setPrompt(""); setTimeout(() => textareaRef.current?.focus(), 100); }}
              style={{
                background: "transparent",
                border: "1px solid rgba(255,255,255,0.15)",
                color: "rgba(255,255,255,0.5)",
                padding: "10px 24px", borderRadius: "999px",
                fontSize: "13px", cursor: "pointer",
                fontFamily: "inherit",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={e => {
                (e.target as HTMLButtonElement).style.borderColor = "rgba(99,102,241,0.5)";
                (e.target as HTMLButtonElement).style.color = "rgba(255,255,255,0.8)";
              }}
              onMouseLeave={e => {
                (e.target as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.15)";
                (e.target as HTMLButtonElement).style.color = "rgba(255,255,255,0.5)";
              }}
            >
              ← New Search
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
