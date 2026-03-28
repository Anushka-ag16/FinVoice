/**
 * FinVoice — AI Trading Agent (DOM Manipulation Engine)
 * Drives the agent's "thinking" flow, animates trade decisions,
 * and renders XAI explanations in real-time.
 */

const API_BASE = "http://127.0.0.1:8000";

// ─── State ───
let isRunning = false;
let currentMode = "paper";
let selectedTradeIndex = -1;
let tradeDecisions = [];
let agentInterval = null;

// ─── Mock Data (replace with real API calls when backend is live) ───

const MOCK_PORTFOLIO = [
    { symbol: "RELIANCE", name: "Reliance Industries", sector: "Energy", qty: 25, buyPrice: 2450, currentPrice: 2580, weight: 18.2 },
    { symbol: "TCS", name: "Tata Consultancy", sector: "IT", qty: 15, buyPrice: 3800, currentPrice: 3720, weight: 15.8 },
    { symbol: "HDFCBANK", name: "HDFC Bank", sector: "Banking", qty: 40, buyPrice: 1550, currentPrice: 1620, weight: 18.3 },
    { symbol: "INFY", name: "Infosys", sector: "IT", qty: 30, buyPrice: 1480, currentPrice: 1510, weight: 12.8 },
    { symbol: "ICICIBANK", name: "ICICI Bank", sector: "Banking", qty: 50, buyPrice: 920, currentPrice: 985, weight: 13.9 },
    { symbol: "ITC", name: "ITC Limited", sector: "FMCG", qty: 100, buyPrice: 440, currentPrice: 465, weight: 13.1 },
    { symbol: "BHARTIARTL", name: "Bharti Airtel", sector: "Telecom", qty: 20, buyPrice: 1350, currentPrice: 1420, weight: 8.0 },
];

const MOCK_SENTIMENT = {
    RELIANCE: { signal: "bullish", score: 0.42, headlines: ["Reliance Jio subscriber base crosses 500M", "RIL Q4 profits beat estimates by 12%"] },
    TCS: { signal: "bearish", score: -0.31, headlines: ["TCS sees increased attrition in key digital units", "IT sector faces headwinds from AI disruption"] },
    HDFCBANK: { signal: "bullish", score: 0.55, headlines: ["HDFC Bank asset quality improves, NPA at all-time low", "Merger synergies ahead of schedule: analysts"] },
    INFY: { signal: "neutral", score: 0.05, headlines: ["Infosys maintains guidance, muted outlook for FY27"] },
    ICICIBANK: { signal: "bullish", score: 0.38, headlines: ["ICICI Bank retail loan book grows 22% YoY"] },
    ITC: { signal: "bullish", score: 0.28, headlines: ["ITC demerger unlocks value for hotel business"] },
    BHARTIARTL: { signal: "bullish", score: 0.51, headlines: ["Bharti Airtel ARPU rises to ₹233, strongest in industry"] },
};

const MOCK_SHAP_FACTORS = {
    RELIANCE: [
        { name: "News is positive", value: 0.22, direction: "positive" },
        { name: "Not overpriced", value: 0.15, direction: "positive" },
        { name: "Price rising lately", value: 0.12, direction: "positive" },
        { name: "Energy sector doing well", value: 0.10, direction: "positive" },
        { name: "Buying interest is high", value: 0.09, direction: "positive" },
        { name: "Investors purchasing more", value: 0.07, direction: "positive" },
        { name: "Price swings a bit", value: -0.08, direction: "negative" },
        { name: "Near its yearly high", value: -0.05, direction: "negative" },
    ],
    TCS: [
        { name: "News is negative", value: -0.25, direction: "negative" },
        { name: "Price falling lately", value: -0.18, direction: "negative" },
        { name: "Looks overpriced", value: -0.12, direction: "negative" },
        { name: "Selling signal active", value: -0.11, direction: "negative" },
        { name: "IT sector struggling", value: -0.09, direction: "negative" },
        { name: "Near its yearly low", value: -0.04, direction: "negative" },
        { name: "Price is stable", value: 0.06, direction: "positive" },
        { name: "Clear trend exists", value: 0.03, direction: "positive" },
    ],
    HDFCBANK: [
        { name: "News is very positive", value: 0.28, direction: "positive" },
        { name: "Banking sector is strong", value: 0.15, direction: "positive" },
        { name: "Growing steadily for weeks", value: 0.11, direction: "positive" },
        { name: "Investors purchasing more", value: 0.09, direction: "positive" },
        { name: "Not overpriced", value: 0.08, direction: "positive" },
        { name: "Buying signal active", value: 0.06, direction: "positive" },
        { name: "Clear upward trend", value: 0.04, direction: "positive" },
        { name: "Slight price swings", value: -0.03, direction: "negative" },
    ],
};

// ─── Agent Flow ───

async function startAnalysis() {
    if (isRunning) return;
    isRunning = true;

    const startBtn = document.getElementById("startAnalysisBtn");
    const stopBtn = document.getElementById("stopBtn");
    startBtn.innerHTML = '<span class="btn-icon">⚡</span><span>Running...</span>';
    startBtn.classList.add("running");
    stopBtn.style.display = "flex";

    updateAgentStatus("Initializing analysis pipeline...");
    clearThoughts();
    tradeDecisions = [];
    renderDecisions();

    // Phase 1: Market Scan
    await addThought("🔍", "Checking the <strong>latest stock prices</strong> for your 7 holdings...", "analyzing");
    await sleep(1200);

    // Phase 2: Feature Engineering
    await addThought("📈", "Studying <strong>price trends, buying patterns, and market momentum</strong> across your stocks...");
    updateAgentStatus("Studying price patterns...");
    await sleep(1500);

    // Phase 3: Sentiment Analysis
    await addThought("📰", "Reading <strong>today's financial news</strong> to understand what experts and media are saying...", "analyzing");
    updateAgentStatus("Reading financial news...");
    await sleep(1800);

    await addThought("🟢", `<strong>Good news</strong> for RELIANCE, HDFC Bank, and Bharti Airtel — experts are optimistic!`, "buy-signal");
    await sleep(800);
    await addThought("🔴", `<strong>Concerning news</strong> for TCS — employee exits increasing, sector facing challenges`, "sell-signal");
    await sleep(800);

    // Phase 4: AutoML Prediction
    await addThought("🤖", "Running <strong>6 different AI models</strong> to predict where prices may head next week...");
    updateAgentStatus("AI predicting price movement...");
    await sleep(2000);

    await addThought("📊", "AI predictions ready. <strong>5 out of 6 models agree</strong> on the direction — high confidence!");
    await sleep(600);

    // Phase 5: Risk Controls
    await addThought("🛡️", "Running <strong>safety checks</strong> — making sure trades are within your risk limits and not too concentrated in one stock...");
    updateAgentStatus("Safety checks...");
    await sleep(1000);
    await addThought("✅", "All safety checks passed. <strong>Your money stays protected.</strong>");
    await sleep(800);

    // Phase 6: Generate Decisions
    updateAgentStatus("Preparing recommendations...");
    await generateTradeDecisions();

    // Phase 7: Done
    updateAgentStatus("Analysis complete ✓");
    await addThought("🎯", `I've prepared <strong>${tradeDecisions.length} recommendations</strong> for you. Tap any one to see exactly <strong>why</strong> I'm suggesting it.`);

    startBtn.innerHTML = '<span class="btn-icon">🔄</span><span>Re-analyze</span>';
    startBtn.classList.remove("running");
    isRunning = false;
}

function stopAgent() {
    isRunning = false;
    const startBtn = document.getElementById("startAnalysisBtn");
    const stopBtn = document.getElementById("stopBtn");
    startBtn.innerHTML = '<span class="btn-icon">▶</span><span>Start Analysis</span>';
    startBtn.classList.remove("running");
    stopBtn.style.display = "none";
    updateAgentStatus("Stopped");
}

async function generateTradeDecisions() {
    tradeDecisions = [];

    // BUY: HDFCBANK
    tradeDecisions.push({
        symbol: "HDFCBANK", name: "HDFC Bank", action: "buy",
        qty: 10, price: 1620, amount: 16200,
        confidence: 0.85, regime: "Bull",
        reason: "HDFC Bank is getting <strong>very positive news</strong> — their bad loans are at an all-time low, which means the bank is healthier than ever. The stock <strong>isn't overpriced</strong> right now, and the banking sector as a whole is doing well. Our AI expects the price to <strong>go up about 2.3% this week</strong>.",
        shap: MOCK_SHAP_FACTORS.HDFCBANK,
        sentiment: MOCK_SENTIMENT.HDFCBANK,
        riskChecks: [
            { label: "Market is open right now", pass: true },
            { label: "This trade is only 2.9% of your portfolio — safe size", pass: true },
            { label: "After buying, HDFC Bank will be 21% of your portfolio — well diversified", pass: true },
            { label: "You've only made 1 trade today — within daily limit", pass: true },
            { label: "No losses today — you're in the green", pass: true },
            { label: "You haven't traded this stock recently — no rush", pass: true },
        ],
    });

    // SELL: TCS
    tradeDecisions.push({
        symbol: "TCS", name: "Tata Consultancy", action: "sell",
        qty: 5, price: 3720, amount: 18600,
        confidence: 0.72, regime: "Uncertainty",
        reason: "TCS is facing <strong>concerning news</strong> — key employees are leaving and the IT sector is worried about AI replacing traditional services. The stock price has been <strong>falling over the past week</strong>, and our AI thinks it may <strong>drop another 1.8%</strong>. Selling a small portion to reduce your risk.",
        shap: MOCK_SHAP_FACTORS.TCS,
        sentiment: MOCK_SENTIMENT.TCS,
        riskChecks: [
            { label: "Market is open right now", pass: true },
            { label: "Selling only 3.3% of your portfolio — small move", pass: true },
            { label: "After selling, TCS drops from 15.8% → 12.5% of portfolio — still diversified", pass: true },
            { label: "You've only made 2 trades today — within daily limit", pass: true },
            { label: "No losses today — you're in the green", pass: true },
            { label: "You haven't traded this stock recently — no rush", pass: true },
        ],
    });

    // BUY: RELIANCE
    tradeDecisions.push({
        symbol: "RELIANCE", name: "Reliance Industries", action: "buy",
        qty: 5, price: 2580, amount: 12900,
        confidence: 0.78, regime: "Bull",
        reason: "Reliance is in the news for <strong>Jio crossing 500 million subscribers</strong> — a huge business milestone. The stock has been <strong>going up steadily</strong> over the past week (+1.8%). The biggest reason our AI likes this trade: <strong>the news is overwhelmingly positive</strong>. 5 out of 6 AI models agree this is a good buy.",
        shap: MOCK_SHAP_FACTORS.RELIANCE,
        sentiment: MOCK_SENTIMENT.RELIANCE,
        riskChecks: [
            { label: "Market is open right now", pass: true },
            { label: "This trade is only 2.3% of your portfolio — safe size", pass: true },
            { label: "After buying, Reliance will be 20.5% of portfolio — well diversified", pass: true },
            { label: "You've only made 3 trades today — within daily limit", pass: true },
            { label: "No losses today — you're in the green", pass: true },
            { label: "You haven't traded this stock recently — no rush", pass: true },
        ],
    });

    // HOLD: INFY
    tradeDecisions.push({
        symbol: "INFY", name: "Infosys", action: "hold",
        qty: 0, price: 1510, amount: 0,
        confidence: 0.45, regime: "Neutral",
        reason: "Infosys gave a <strong>cautious outlook</strong> for next year — not bad news, but nothing exciting either. Our AI models are <strong>split on this one</strong> — some say it'll go up, others say it'll go down. When there's no clear direction, the smartest move is to <strong>sit tight and wait</strong> for a clearer picture.",
        shap: [],
        sentiment: MOCK_SENTIMENT.INFY,
        riskChecks: [],
    });

    // Render each card with delay
    for (let i = 0; i < tradeDecisions.length; i++) {
        await sleep(600);
        renderDecisions();
    }
}

// ─── DOM Manipulation ───

function clearThoughts() {
    document.getElementById("agentThoughts").innerHTML = "";
}

async function addThought(icon, text, cssClass = "") {
    if (!isRunning) return;

    const container = document.getElementById("agentThoughts");
    const card = document.createElement("div");
    card.className = `thought-card ${cssClass}`;

    card.innerHTML = `
        <div class="thought-icon">${icon}</div>
        <div class="thought-text">
            <p>${text}<span class="typing-cursor"></span></p>
        </div>
    `;

    container.appendChild(card);
    container.scrollTop = container.scrollHeight;

    // Remove cursor after typing effect
    await sleep(600);
    const cursor = card.querySelector(".typing-cursor");
    if (cursor) cursor.remove();
}

function updateAgentStatus(text) {
    document.getElementById("agentStatus").textContent = text;
}

function renderDecisions() {
    const container = document.getElementById("decisionsList");
    const emptyState = document.getElementById("emptyState");

    if (tradeDecisions.length === 0) {
        container.innerHTML = "";
        container.appendChild(emptyState);
        emptyState.style.display = "flex";
        return;
    }

    if (emptyState) emptyState.style.display = "none";

    container.innerHTML = tradeDecisions.map((trade, i) => `
        <div class="trade-card ${trade.action} ${i === selectedTradeIndex ? 'selected' : ''}"
             onclick="selectTrade(${i})" id="trade-card-${i}">
            <div class="trade-card-top">
                <div class="trade-symbol">
                    <span class="symbol-badge">${trade.symbol}</span>
                    <span class="symbol-name">${trade.name}</span>
                </div>
                <span class="trade-action ${trade.action}">${trade.action}</span>
            </div>
            ${trade.action !== "hold" ? `
            <div class="trade-card-details">
                <div class="detail-item">
                    <span class="detail-label">Qty</span>
                    <span class="detail-value">${trade.qty}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Price</span>
                    <span class="detail-value">₹${trade.price.toLocaleString("en-IN")}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Value</span>
                    <span class="detail-value">₹${trade.amount.toLocaleString("en-IN")}</span>
                </div>
            </div>` : ''}
            <div class="trade-card-reason">${trade.reason}</div>
            <div class="trade-card-time">
                Confidence: ${(trade.confidence * 100).toFixed(0)}% • Regime: ${trade.regime} • ${new Date().toLocaleTimeString("en-IN")}
            </div>
            ${trade.action !== "hold" ? `
            <div class="trade-progress">
                <div class="trade-progress-bar ${trade.action}" style="width: ${trade.confidence * 100}%"></div>
            </div>` : ''}
        </div>
    `).join("");
}

function selectTrade(index) {
    selectedTradeIndex = index;
    renderDecisions();
    renderXAI(tradeDecisions[index]);

    // Highlight animation
    const card = document.getElementById(`trade-card-${index}`);
    if (card) {
        card.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function filterTrades(filter, btn) {
    document.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");

    const cards = document.querySelectorAll(".trade-card");
    cards.forEach(card => {
        if (filter === "all" || card.classList.contains(filter)) {
            card.style.display = "block";
        } else {
            card.style.display = "none";
        }
    });
}

// ─── XAI Rendering ───

function renderXAI(trade) {
    const container = document.getElementById("xaiContent");

    container.innerHTML = `
        <div class="xai-detail">
            <!-- Summary -->
            <div class="xai-summary">
                <strong>${trade.action === "buy" ? "📈 BUY" : trade.action === "sell" ? "📉 SELL" : "⏸ HOLD"} ${trade.symbol}</strong>
                ${trade.action !== "hold" ? `— ${trade.qty} shares @ ₹${trade.price.toLocaleString("en-IN")}` : "— No action recommended"}
                <br><br>
                ${trade.reason}
            </div>

            ${trade.shap && trade.shap.length > 0 ? `
            <!-- What influenced this decision -->
            <div class="xai-section">
                <div class="xai-section-title">🧠 What influenced this decision?</div>
                <p style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 10px;">Each bar shows how much a factor pushed the AI towards buying (green, right) or selling (red, left).</p>
                <div class="factor-bar-container">
                    ${trade.shap.sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).map(f => `
                        <div class="factor-bar">
                            <span class="factor-name">${f.name}</span>
                            <div class="factor-track">
                                <div class="factor-center-line"></div>
                                <div class="factor-fill ${f.direction}"
                                     style="width: ${Math.abs(f.value) * 200}%;">
                                    ${f.direction === 'positive' ? '👍' : '👎'} ${Math.abs(f.value * 100).toFixed(0)}%
                                </div>
                            </div>
                        </div>
                    `).join("")}
                </div>
            </div>` : ''}

            <!-- What the news says -->
            <div class="xai-section">
                <div class="xai-section-title">📰 What the news says</div>
                ${renderSentimentGauge(trade.sentiment)}
                <div style="margin-top: 8px;">
                    ${(trade.sentiment.headlines || []).map(h => `
                        <div style="padding: 6px 8px; margin-bottom: 4px; background: var(--bg-card); border-radius: var(--radius-sm); font-size: 0.75rem; color: var(--text-secondary);">
                            📄 ${h}
                        </div>
                    `).join("")}
                </div>
            </div>

            ${trade.riskChecks && trade.riskChecks.length > 0 ? `
            <!-- Safety checks -->
            <div class="xai-section">
                <div class="xai-section-title">🛡️ Is this trade safe for me?</div>
                <div class="risk-checks">
                    ${trade.riskChecks.map(rc => `
                        <div class="risk-check ${rc.pass ? 'pass' : 'fail'}">
                            <span class="risk-check-icon">${rc.pass ? '✅' : '❌'}</span>
                            <span>${rc.label}</span>
                        </div>
                    `).join("")}
                </div>
            </div>` : ''}

            <!-- Execute Button -->
            ${trade.action !== "hold" ? `
            <div style="margin-top: 16px;">
                <button class="btn-primary" onclick="executeTrade(${tradeDecisions.indexOf(trade)})" style="width: 100%;">
                    <span>⚡ Execute ${trade.action === "buy" ? "Buy" : "Sell"} (${currentMode === "paper" ? "Paper" : "Live"})</span>
                </button>
            </div>` : ''}
        </div>
    `;

    // Animate SHAP bars
    setTimeout(() => {
        container.querySelectorAll(".factor-fill").forEach(bar => {
            bar.style.transition = "width 0.8s ease-out";
        });
    }, 100);
}

function renderSentimentGauge(sentiment) {
    if (!sentiment) return "";

    const score = sentiment.score || 0;
    const normalizedScore = (score + 1) / 2; // Map [-1, 1] to [0, 1]
    const circumference = 2 * Math.PI * 24;
    const offset = circumference * (1 - normalizedScore);

    let color = "var(--hold-amber)";
    if (score > 0.2) color = "var(--buy-green)";
    else if (score < -0.2) color = "var(--sell-red)";

    return `
        <div class="sentiment-meter">
            <div class="sentiment-gauge">
                <svg viewBox="0 0 56 56">
                    <circle class="gauge-bg" cx="28" cy="28" r="24"/>
                    <circle class="gauge-fill" cx="28" cy="28" r="24"
                        stroke="${color}"
                        stroke-dasharray="${circumference}"
                        stroke-dashoffset="${offset}"/>
                </svg>
                <span class="sentiment-value" style="color: ${color}">
                    ${score > 0 ? '+' : ''}${(score * 100).toFixed(0)}
                </span>
            </div>
            <div class="sentiment-info">
                <div class="sentiment-label" style="color: ${color}">${sentiment.signal === "bullish" ? "Positive News" : sentiment.signal === "bearish" ? "Negative News" : "Mixed News"}</div>
                <div class="sentiment-desc">
                    We read ${sentiment.headlines ? sentiment.headlines.length : 0} recent news articles about this company.
                    ${Math.abs(score * 100).toFixed(0)}% of coverage points ${score > 0 ? 'in a positive direction' : score < 0 ? 'in a negative direction' : 'in no clear direction'}.
                </div>
            </div>
        </div>
    `;
}

// ─── Trade Execution ───

async function executeTrade(index) {
    const trade = tradeDecisions[index];
    showToast(`⚡ Executing ${trade.action.toUpperCase()} ${trade.qty} ${trade.symbol}...`, "info");

    // Simulate execution
    await sleep(1500);

    showToast(
        `✅ ${trade.action === "buy" ? "Bought" : "Sold"} ${trade.qty} ${trade.symbol} @ ₹${trade.price.toLocaleString("en-IN")} (${currentMode} mode)`,
        "success"
    );

    // Update paper balance
    const balanceEl = document.getElementById("paperBalance");
    const currentBalance = parseFloat(balanceEl.textContent.replace(/[₹,]/g, ""));
    const newBalance = trade.action === "buy"
        ? currentBalance - trade.amount
        : currentBalance + trade.amount;
    balanceEl.textContent = `₹${newBalance.toLocaleString("en-IN")}`;

    // Update trade count
    const tradesEl = document.getElementById("tradesToday");
    const current = parseInt(tradesEl.textContent);
    tradesEl.textContent = `${current + 1} / 20`;
}

// ─── Mode Toggle ───

document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentMode = btn.dataset.mode;

        if (currentMode === "live") {
            showToast("🔴 Switched to LIVE trading mode. Trades will execute via Angel One.", "error");
        } else {
            showToast("📝 Switched to PAPER trading mode. Using virtual ₹10L balance.", "info");
        }
    });
});

// ─── Utilities ───

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(30px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ─── Init ───

function init() {
    // Set market status based on time
    const now = new Date();
    const hours = now.getHours();
    const mins = now.getMinutes();
    const timeVal = hours * 60 + mins;
    const marketOpen = 9 * 60 + 15;
    const marketClose = 15 * 60 + 30;
    const isWeekend = now.getDay() === 0 || now.getDay() === 6;

    const statusEl = document.getElementById("marketStatus");
    if (isWeekend || timeVal < marketOpen || timeVal > marketClose) {
        statusEl.innerHTML = '<span class="status-dot"></span><span>Market Closed</span>';
    }
}

init();
