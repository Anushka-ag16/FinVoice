import { NextRequest, NextResponse } from "next/server";

const SYSTEM_PROMPT = `You are FinVoice AI — an expert Indian financial planner. Given an investor's parameters and risk profile, generate three investment allocation plans: Conservative, Balanced, and Aggressive.

CRITICAL: Respond ONLY with raw JSON — no markdown, no code fences, no backticks, no explanation text. Just the JSON object.

Use these Indian asset classes: Equity (Nifty 50 / large cap MFs), Mid & Small Cap, Debt (bonds, FDs, govt securities), Gold (SGBs, Gold ETFs), Real Estate (REITs), Liquid / Cash, International Equity (Nasdaq/S&P 500 funds).

For each plan, provide:
- name: "Conservative" | "Balanced" | "Aggressive"
- tagline: 2-3 word subtitle (e.g. "Safe Harbor", "Golden Mean", "Moonshot")
- description: 1-sentence summary
- allocations: array of {asset, pct, amount} (pct sums to 100, amount = pct * total amount / 100, formatted for Indian locale with K/L/Cr suffixes)
- projected_return: projected value after horizon (formatted in Indian locale like ₹1.18L)
- max_drawdown: worst-case percentage loss (e.g. "-11%")
- recommended: boolean (true for the one best matching their risk profile)
- explanation: 2-3 sentences explaining why this allocation fits (use Indian context)

Also include:
- explanation_summary: 2-3 sentence overall explanation of why the recommended plan was chosen, referencing their risk profile, horizon, and loss tolerance
- driving_factors: array of {factor, impact, direction} where impact is 0.0-1.0 and direction is "positive" or "negative"

Use Indian formatting (₹, lakhs, crores). Never guarantee returns. Use language like "projected", "historically".

JSON schema:
{
  "plans": [...],
  "explanation_summary": "...",
  "driving_factors": [...]
}`;

export async function POST(req: NextRequest) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: "OPENAI_API_KEY not configured" }, { status: 500 });
  }

  const body = await req.json();
  const { amount, horizon, priority, loss, riskProfile } = body;

  // Build the user prompt with all context
  let userPrompt = `Generate investment plans for the following investor:

Investment amount: ₹${amount}
Investment horizon: ${horizon}
Priority: ${priority}
Maximum acceptable loss: ${loss}%`;

  if (riskProfile) {
    userPrompt += `

Risk Questionnaire Results:
- Risk Level: ${riskProfile.risk_level || "Not assessed"}
- Risk Score: ${riskProfile.score ?? "N/A"}/100
- Behavioral Bias: ${riskProfile.behavioral_bias || "balanced"}
- Recommended Asset Allocation from risk assessment: ${riskProfile.recommended_allocation ? JSON.stringify(riskProfile.recommended_allocation) : "N/A"}`;
  }

  userPrompt += `

Generate exactly 3 plans (Conservative, Balanced, Aggressive), marking the one most appropriate for this investor's risk profile as recommended. Use the risk questionnaire results to inform which plan to recommend and how to explain the allocation.`;

  try {
    const openaiRes = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "gpt-4o",
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: userPrompt },
        ],
        temperature: 0.7,
        max_tokens: 2048,
      }),
    });

    if (!openaiRes.ok) {
      const errText = await openaiRes.text();
      console.error("OpenAI error:", errText);
      return NextResponse.json({ error: `OpenAI error: ${openaiRes.status}` }, { status: 502 });
    }

    const data = await openaiRes.json();
    const content = data.choices?.[0]?.message?.content;

    if (!content) {
      return NextResponse.json({ error: "Empty response from AI" }, { status: 502 });
    }

    // Parse the JSON response (strip markdown fences if present)
    let parsed;
    try {
      const cleaned = content.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
      parsed = JSON.parse(cleaned);
    } catch (parseErr) {
      console.error("Failed to parse AI response:", content);
      return NextResponse.json({ error: "Failed to parse AI response" }, { status: 502 });
    }

    return NextResponse.json(parsed);
  } catch (err) {
    console.error("Investment plan generation failed:", err);
    return NextResponse.json({ error: "Failed to generate investment plan" }, { status: 500 });
  }
}
