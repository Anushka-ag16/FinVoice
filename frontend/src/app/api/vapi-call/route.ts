import { NextRequest, NextResponse } from "next/server";

const VAPI_API_KEY = "759aff45-190c-417f-9d34-711cb05cd004";
const VAPI_ASSISTANT_ID = "011437c6-31a4-467c-aa10-ec9336df7131";
const VAPI_PHONE_NUMBER_ID = "2a6fdb19-037d-4146-85de-981b4b44d04a";

export async function POST(req: NextRequest) {
  const { phoneNumber } = await req.json();

  if (!phoneNumber) {
    return NextResponse.json({ error: "Phone number is required" }, { status: 400 });
  }

  // Normalize phone number to E.164 format
  let normalized = phoneNumber.replace(/[\s\-\(\)]/g, "");
  if (normalized.startsWith("0")) {
    normalized = "+91" + normalized.slice(1);
  } else if (!normalized.startsWith("+")) {
    normalized = "+91" + normalized;
  }

  try {
    const callRes = await fetch("https://api.vapi.ai/call", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${VAPI_API_KEY}`,
      },
      body: JSON.stringify({
        assistantId: VAPI_ASSISTANT_ID,
        phoneNumberId: VAPI_PHONE_NUMBER_ID,
        customer: {
          number: normalized,
        },
      }),
    });

    if (!callRes.ok) {
      const errText = await callRes.text();
      console.error("Failed to create Vapi call:", errText);
      return NextResponse.json(
        { error: `Failed to initiate call: ${errText}` },
        { status: 502 }
      );
    }

    const callData = await callRes.json();

    return NextResponse.json({
      success: true,
      callId: callData.id,
      status: callData.status,
      message: `Call initiated to ${normalized}. You should receive a call shortly.`,
    });
  } catch (err) {
    console.error("Vapi call error:", err);
    return NextResponse.json(
      { error: "Failed to initiate call. Please try again." },
      { status: 500 }
    );
  }
}
