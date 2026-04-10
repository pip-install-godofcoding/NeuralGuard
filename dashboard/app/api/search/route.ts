import { NextRequest, NextResponse } from "next/server";

const PROXY_URL = process.env.NEXT_PUBLIC_PROXY_URL ?? "http://localhost:8000";
const NG_API_KEY = process.env.NEURALGUARD_API_KEY ?? "";

export async function POST(req: NextRequest) {
  try {
    const { prompt } = await req.json();

    if (!prompt || typeof prompt !== "string" || !prompt.trim()) {
      return NextResponse.json({ error: "Prompt is required" }, { status: 400 });
    }

    if (!NG_API_KEY) {
      return NextResponse.json(
        { error: "NEURALGUARD_API_KEY not set in environment" },
        { status: 503 }
      );
    }

    const start = Date.now();

    const upstream = await fetch(`${PROXY_URL}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${NG_API_KEY}`,
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [{ role: "user", content: prompt.trim() }],
        stream: false,
      }),
    });

    const latencyMs = Date.now() - start;

    if (!upstream.ok) {
      const text = await upstream.text();
      return NextResponse.json(
        { error: `Proxy error ${upstream.status}: ${text.slice(0, 300)}` },
        { status: upstream.status }
      );
    }

    const data = await upstream.json();

    const answer =
      data?.choices?.[0]?.message?.content ?? "(No response from model)";
    const modelRequested = "llama-3.3-70b-versatile";
    const modelUsed = data?.model ?? modelRequested;
    const cacheHit: boolean = data?.cache_hit ?? false;
    const trustScore: number | null = data?.trust_score ?? null;
    const tokenUsage: number = data?.usage?.total_tokens ?? 0;

    return NextResponse.json({
      answer,
      modelRequested,
      modelUsed,
      cacheHit,
      latencyMs,
      trustScore,
      tokenUsage,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
