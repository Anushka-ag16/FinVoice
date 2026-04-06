import { NextRequest } from "next/server";

const SYSTEM_PROMPT = `You are FinVoice AI — a knowledgeable, friendly, and trustworthy financial advisor built specifically for Indian investors. You are embedded inside the FinVoice app.

## Your Capabilities
- Portfolio analysis, rebalancing advice, and drift correction
- Investment strategy for Indian markets: NSE/BSE equities, mutual funds (SIPs), gold (sovereign gold bonds, ETFs), fixed deposits, REITs, bonds
- Risk assessment, management, and behavioral coaching
- Tax-efficient investing: Section 80C, 80D, ELSS, LTCG, STCG, indexation
- SIP planning, goal-based investing, emergency fund guidance
- Market education — explain concepts clearly and simply
- Crash/stress test scenario discussion
- Comparing asset classes and helping with asset allocation

## Communication Guidelines
1. **Adapt to investor type**: If the user is a beginner, avoid jargon and use simple analogies. If experienced, include technical analysis, ratios, and data.
2. **Use Indian context**: Always use ₹ for currency. Use lakhs and crores for large numbers (e.g., ₹1,50,000 or ₹2.5 crore). Reference Indian instruments (Nifty 50, Sensex, ELSS, PPF, NPS, SGBs, etc.).
3. **Be balanced**: Always mention risks alongside opportunities. Never guarantee returns.
4. **Be concise**: Give clear, actionable answers. Use bullet points and structure.
5. **Use hedging language**: Say "historically", "tends to", "based on current data", "potential".
6. **Proactive**: If you notice issues in their portfolio (concentration risk, missing asset classes, drift), mention them naturally.

## Formatting
- Use markdown formatting for readability (bold, bullet points, headers).
- Use tables when comparing options.
- Keep responses focused — aim for 100-300 words unless the user asks for detail.

## Restrictions
- Never provide SEBI-registered investment advice. You are a decision-support tool.
- Never share made-up stock prices, NAVs, or returns. If you don't have data, say so.
- Never execute trades or promise to execute trades.
- End with the disclaimer when giving specific investment recommendations: "📋 *FinVoice is a decision-support tool. Consult a SEBI-registered advisor for personalized advice.*"
`;

export async function POST(req: NextRequest) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    return new Response(
      JSON.stringify({ error: "OPENAI_API_KEY not configured" }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }

  const { message, history } = await req.json();

  // Build messages array
  const messages: { role: string; content: string }[] = [
    { role: "system", content: SYSTEM_PROMPT },
  ];

  // Add conversation history (cap at last 20)
  if (Array.isArray(history)) {
    for (const msg of history.slice(-20)) {
      const role = msg.role === "assistant" ? "assistant" : "user";
      messages.push({ role, content: msg.content || "" });
    }
  }

  messages.push({ role: "user", content: message });

  // Call OpenAI with streaming
  const openaiRes = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: "gpt-4o",
      messages,
      stream: true,
      temperature: 0.7,
      max_tokens: 1024,
    }),
  });

  if (!openaiRes.ok) {
    const errText = await openaiRes.text();
    return new Response(
      JSON.stringify({ error: `OpenAI error: ${openaiRes.status} ${errText}` }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }

  // Transform OpenAI SSE stream into our own SSE format
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const stream = new ReadableStream({
    async start(controller) {
      const reader = openaiRes.body?.getReader();
      if (!reader) {
        controller.close();
        return;
      }

      let buffer = "";
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();
            if (data === "[DONE]") continue;

            try {
              const parsed = JSON.parse(data);
              const token = parsed.choices?.[0]?.delta?.content;
              if (token) {
                const payload = JSON.stringify({ token });
                controller.enqueue(encoder.encode(`data: ${payload}\n\n`));
              }
            } catch {
              // skip malformed chunks
            }
          }
        }
      } catch (e) {
        const errPayload = JSON.stringify({ error: String(e) });
        controller.enqueue(encoder.encode(`data: ${errPayload}\n\n`));
      }

      // Signal done
      controller.enqueue(encoder.encode(`data: ${JSON.stringify({ done: true })}\n\n`));
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
