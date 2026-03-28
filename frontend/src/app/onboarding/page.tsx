"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { apiSubmitQuestionnaire } from "@/lib/api";
import { useFinStore } from "@/store/useFinStore";
import { ChevronRight, ChevronLeft, Check, Info } from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   TYPES
═══════════════════════════════════════════════════════════════ */
interface Option {
  label: string;
  desc?: string;
  score: number;
  bias?: string;
  tier?: string;
}
interface Question {
  id: string;
  section: string;
  tier?: string;
  tier_splitter?: boolean;
  conditional?: boolean;
  text: string;
  sub?: string;
  type: "radio" | "multi" | "slider";
  min?: number;
  max?: number;
  options: Option[];
  optional?: boolean;
}

/* ═══════════════════════════════════════════════════════════════
   QUESTION BANK  (28 questions; each user sees 12–13)
═══════════════════════════════════════════════════════════════ */
const ALL_QUESTIONS: Question[] = [
  // ── UNIVERSAL Q1–Q5 ──────────────────────────────────────────────────────
  { id:"age_bracket", section:"foundation",
    text:"Which age group do you belong to?",
    sub:"This shapes how much time your money has to grow and how much risk makes sense.",
    type:"radio", options:[
      {label:"Under 25",  desc:"Longest runway ahead",       score:20},
      {label:"25–35",     desc:"Prime wealth-building years", score:17},
      {label:"36–45",     desc:"Peak earning phase",          score:13},
      {label:"46–55",     desc:"Pre-retirement planning",     score:8},
      {label:"56+",       desc:"Preservation priority",       score:3},
    ]},

  { id:"dependents", section:"foundation",
    text:"How many people depend on you financially?",
    sub:"More dependents means less room to take on risk.",
    type:"radio", options:[
      {label:"None — just myself", score:10},
      {label:"1–2 people",         score:7},
      {label:"3–4 people",         score:4},
      {label:"5 or more",          score:1},
    ]},

  { id:"employment", section:"foundation",
    text:"What best describes your work situation?",
    sub:"Your income stability is a key input to how much risk you can absorb.",
    type:"radio", options:[
      {label:"Government / public sector job",    desc:"Highly stable income",          score:10},
      {label:"Private company — salaried",        desc:"Stable with some market risk",  score:8},
      {label:"Self-employed / freelancer",        desc:"Variable income",               score:5},
      {label:"Business owner",                    desc:"Variable, higher upside",       score:6},
      {label:"Student / not currently earning",   desc:"No primary income",             score:3},
      {label:"Retired",                           desc:"Fixed income / savings",        score:2},
    ]},

  { id:"emergency_buffer", section:"foundation",
    text:"If you lost your income today, how long could you manage with your savings?",
    sub:"Without a buffer, you may be forced to sell investments at the worst time.",
    type:"radio", options:[
      {label:"Less than 1 month", score:0},
      {label:"1–3 months",        score:3},
      {label:"3–6 months",        score:6},
      {label:"6–12 months",       score:8},
      {label:"More than a year",  score:10},
    ]},

  { id:"investing_experience", section:"foundation", tier_splitter:true,
    text:"Which best describes your investing journey so far?",
    sub:"Be honest — there is no wrong answer. This determines which questions you see next.",
    type:"radio", options:[
      {label:"Never invested. My money sits in a savings account or FD.",             score:2,  tier:"beginner"},
      {label:"Done a few SIPs or mutual funds, but I don't really follow markets.",   score:5,  tier:"beginner"},
      {label:"I invest regularly in mutual funds / stocks and understand the basics.", score:10, tier:"intermediate"},
      {label:"I actively manage my portfolio — fundamentals / technicals.",            score:15, tier:"expert"},
      {label:"I trade options/futures, use leverage, manage complex positions.",       score:18, tier:"expert"},
    ]},

  // ── BEGINNER PATH Q6–Q12 ─────────────────────────────────────────────────
  { id:"b_goal", section:"financial", tier:"beginner",
    text:"What is the main reason you want to start investing?",
    type:"radio", options:[
      {label:"My savings are losing value to inflation",                score:5},
      {label:"I have a big goal in 2–5 years (wedding, car, home)",    score:8},
      {label:"I want to build wealth slowly over the long term",        score:14},
      {label:"Saving for retirement or my children's future",           score:12},
      {label:"No specific goal — I just want to start somewhere",       score:9},
    ]},

  { id:"b_time_horizon", section:"financial", tier:"beginner",
    text:"How long can you leave this money invested without needing it back?",
    sub:"The longer you can wait, the more growth you can target.",
    type:"radio", options:[
      {label:"Less than 1 year — I might need it anytime", score:2},
      {label:"1–3 years",                                   score:5},
      {label:"3–5 years",                                   score:9},
      {label:"5–10 years",                                  score:13},
      {label:"10+ years — I'm in no rush at all",           score:17},
    ]},

  { id:"b_max_loss", section:"behavioral", tier:"beginner", conditional:true,
    text:"Which situation would actually make you sell your investments?",
    sub:"Be honest — answering cautiously here only leads to a mismatch later.",
    type:"radio", options:[
      {label:"Any loss at all — I can't see my balance go down",               score:1,  bias:"loss_averse"},
      {label:"A 10% drop (₹10,000 on every ₹1 lakh invested)",                score:4,  bias:"loss_averse"},
      {label:"A 20% drop (₹20,000 on every ₹1 lakh invested)",                score:8},
      {label:"A 35%+ drop — even then I'd think twice before selling",         score:13, bias:"balanced"},
      {label:"I wouldn't sell regardless of how far it falls",                 score:17, bias:"overconfident"},
    ]},

  { id:"b_invest_amount", section:"financial", tier:"beginner",
    text:"How much could you invest every month, even in small amounts?",
    type:"radio", options:[
      {label:"Under ₹500 / month",        score:2},
      {label:"₹500 – ₹2,000 / month",     score:4},
      {label:"₹2,000 – ₹5,000 / month",   score:6},
      {label:"₹5,000 – ₹15,000 / month",  score:8},
      {label:"More than ₹15,000 / month", score:10},
    ]},

  { id:"b_gift_scenario", section:"behavioral", tier:"beginner",
    text:"Someone gifts you ₹1,00,000 today. How would you use it?",
    type:"radio", options:[
      {label:"Keep all of it in a bank FD — I can't risk losing even ₹1",          score:2,  bias:"loss_averse"},
      {label:"Keep ₹80,000 safe; invest ₹20,000 in something that could grow",     score:6},
      {label:"Split equally — half safe, half in growth investments",               score:10, bias:"balanced"},
      {label:"Invest ₹80,000 or more — ups and downs are fine for me",             score:14, bias:"overconfident"},
    ]},

  { id:"b_drop_test", section:"behavioral", tier:"beginner",
    text:"You invest ₹5,000/month. After 6 months (₹30,000 invested) your balance shows ₹25,000. What do you do?",
    type:"radio", options:[
      {label:"Stop and withdraw everything immediately",           score:1,  bias:"loss_averse"},
      {label:"Stop adding money but leave what's already there",   score:4,  bias:"loss_averse"},
      {label:"Continue as normal — this kind of dip is expected",  score:10, bias:"balanced"},
      {label:"Invest even more — I'm buying at a discount!",       score:15, bias:"overconfident"},
    ]},

  { id:"b_priority", section:"behavioral", tier:"beginner",
    text:"If you could only pick ONE — what matters most about your money?",
    type:"radio", options:[
      {label:"Safety — my money should never go down",                     score:3,  bias:"loss_averse"},
      {label:"Stability — small, steady growth with minimal bumps",        score:7},
      {label:"Growth — I want it to grow, even with some ups and downs",   score:13, bias:"balanced"},
      {label:"Maximum returns — I'll take big risks for big rewards",      score:17, bias:"overconfident"},
    ]},

  // ── INTERMEDIATE PATH Q6–Q13 ──────────────────────────────────────────────
  { id:"i_annual_income", section:"financial", tier:"intermediate",
    text:"What is your approximate annual household income?",
    type:"radio", options:[
      {label:"Under ₹6 LPA",   score:3},
      {label:"₹6–12 LPA",      score:6},
      {label:"₹12–25 LPA",     score:9},
      {label:"₹25–50 LPA",     score:12},
      {label:"Above ₹50 LPA",  score:15},
    ]},

  { id:"i_portfolio_size", section:"financial", tier:"intermediate",
    text:"What is your current total investment value?",
    sub:"Across all instruments — MFs, stocks, FDs, gold. Exclude your primary home and emergency fund.",
    type:"radio", options:[
      {label:"Under ₹1 Lakh",         score:3},
      {label:"₹1–5 Lakh",             score:5},
      {label:"₹5–25 Lakh",            score:8},
      {label:"₹25 Lakh – ₹1 Crore",  score:11},
      {label:"Above ₹1 Crore",        score:14},
    ]},

  { id:"i_debt", section:"financial", tier:"intermediate", conditional:true,
    text:"What is your current debt situation?",
    type:"radio", options:[
      {label:"Completely debt-free",                  score:10},
      {label:"Only home loan with comfortable EMI",   score:8},
      {label:"Home loan + one other loan",            score:5},
      {label:"Multiple loans or heavy EMI burden",    score:2},
    ]},

  { id:"i_primary_goal", section:"financial", tier:"intermediate",
    text:"What is your primary investment goal?",
    type:"radio", options:[
      {label:"Long-term wealth creation (10+ years)", score:15},
      {label:"Retirement planning",                   score:12},
      {label:"Child's education or marriage fund",    score:10},
      {label:"Buying a home in 3–7 years",           score:7},
      {label:"Regular income or cash flow",           score:4},
      {label:"Tax saving (ELSS, NPS)",               score:6},
    ]},

  { id:"i_time_horizon", section:"financial", tier:"intermediate",
    text:"What is your primary investment time horizon?",
    type:"radio", options:[
      {label:"Less than 1 year",   score:2},
      {label:"1–3 years",          score:5},
      {label:"3–5 years",          score:9},
      {label:"5–10 years",         score:14},
      {label:"More than 10 years", score:18},
    ]},

  { id:"i_crash_scenario", section:"behavioral", tier:"intermediate",
    text:"Your portfolio drops 25% in 3 months during a market correction. What do you do?",
    sub:"Answer honestly — not what sounds 'smart'. Your real reaction matters most.",
    type:"radio", options:[
      {label:"Sell everything to stop further losses",                    score:2,  bias:"loss_averse"},
      {label:"Sell a portion to reduce exposure",                         score:5,  bias:"loss_averse"},
      {label:"Do nothing — wait for recovery",                            score:10, bias:"balanced"},
      {label:"Review fundamentals and buy more if thesis holds",          score:14, bias:"balanced"},
      {label:"Aggressively buy more — crashes are the best entry points", score:17, bias:"overconfident"},
    ]},

  { id:"i_max_loss", section:"behavioral", tier:"intermediate",
    text:"What is the maximum portfolio loss you could tolerate in a single year?",
    type:"radio", options:[
      {label:"0% — I cannot tolerate any loss",          score:1,  bias:"loss_averse"},
      {label:"Up to 5%",                                 score:4},
      {label:"Up to 10%",                                score:7},
      {label:"Up to 20%",                                score:11},
      {label:"Up to 30%",                                score:15},
      {label:"More than 30% — fine for long-term gains", score:18, bias:"overconfident"},
    ]},

  { id:"i_past_panic", section:"behavioral", tier:"intermediate",
    text:"Have you ever panic-sold investments during a crash and later regretted it?",
    sub:"Past behavior under real stress is the strongest predictor of future behavior.",
    type:"radio", options:[
      {label:"Yes — and I've done it more than once",         score:2,  bias:"loss_averse"},
      {label:"Yes — once. I learned from it.",                score:5,  bias:"loss_averse"},
      {label:"No — I've stayed the course through dips",      score:12, bias:"balanced"},
      {label:"I haven't experienced a real market crash yet", score:7},
    ]},

  // ── EXPERT PATH Q6–Q13 ───────────────────────────────────────────────────
  { id:"e_portfolio_size", section:"financial", tier:"expert",
    text:"Total portfolio value (excluding primary residence)?",
    type:"radio", options:[
      {label:"Under ₹10 Lakh",         score:4},
      {label:"₹10–50 Lakh",            score:7},
      {label:"₹50 Lakh – ₹2 Crore",   score:10},
      {label:"₹2–10 Crore",            score:13},
      {label:"Above ₹10 Crore",        score:16},
    ]},

  { id:"e_savings_rate", section:"financial", tier:"expert",
    text:"What percentage of your income do you invest monthly?",
    type:"radio", options:[
      {label:"Under 15%",  score:4},
      {label:"15–30%",     score:7},
      {label:"30–50%",     score:10},
      {label:"Above 50%",  score:13},
    ]},

  { id:"e_primary_goal", section:"financial", tier:"expert",
    text:"Primary investment objective?",
    type:"radio", options:[
      {label:"Aggressive wealth creation",             score:16},
      {label:"Retirement corpus building",             score:12},
      {label:"Portfolio income / FIRE",                score:10},
      {label:"Capital preservation with real returns", score:5},
      {label:"Multi-goal (diversified objectives)",    score:9},
    ]},

  { id:"e_time_horizon", section:"financial", tier:"expert",
    text:"Investment time horizon for your primary goal?",
    type:"radio", options:[
      {label:"Under 3 years",          score:3},
      {label:"3–5 years",              score:7},
      {label:"5–10 years",             score:12},
      {label:"10–20 years",            score:16},
      {label:"20+ years or perpetual", score:18},
    ]},

  { id:"e_liquidity_need", section:"financial", tier:"expert", conditional:true,
    text:"How important is portfolio liquidity to you?",
    type:"radio", options:[
      {label:"Critical — need access within weeks",      score:2},
      {label:"Important — within 6 months max",          score:5},
      {label:"Moderate — can lock up for 1–3 years",     score:9},
      {label:"Low — comfortable with 3+ year lock-ins",  score:14},
    ]},

  { id:"e_drawdown_experience", section:"behavioral", tier:"expert",
    text:"Largest portfolio drawdown you've held through without selling?",
    sub:"Actual lived experience matters far more than theoretical tolerance.",
    type:"radio", options:[
      {label:"Less than 10%",                            score:4},
      {label:"10–20%",                                   score:7},
      {label:"20–35%",                                   score:11},
      {label:"35–50%",                                   score:15},
      {label:"50%+ (held through 2008 or March 2020)",   score:18},
    ]},

  { id:"e_max_loss", section:"behavioral", tier:"expert",
    text:"Maximum acceptable annual portfolio drawdown?",
    type:"radio", options:[
      {label:"Under 10%",                             score:4},
      {label:"10–20%",                                score:8},
      {label:"20–30%",                                score:12},
      {label:"30–40%",                                score:16},
      {label:"40%+ acceptable for outsized returns",  score:19},
    ]},

  { id:"e_crisis_behavior", section:"behavioral", tier:"expert",
    text:"How did you handle the March 2020 COVID crash (Nifty fell 38%)?",
    sub:"If you weren't invested then, pick what you think you would have done.",
    type:"radio", options:[
      {label:"Panicked and sold most positions",                    score:2,  bias:"loss_averse"},
      {label:"Switched to defensive — more debt / gold",           score:6,  bias:"loss_averse"},
      {label:"Held positions, didn't add fresh money",             score:9,  bias:"balanced"},
      {label:"Held and continued SIPs as planned",                 score:12, bias:"balanced"},
      {label:"Aggressively deployed fresh capital into equities",  score:16, bias:"overconfident"},
    ]},
];

/* ═══════════════════════════════════════════════════════════════
   PATH ENGINE
═══════════════════════════════════════════════════════════════ */
const QUESTION_MAP: Record<string, Question> = Object.fromEntries(
  ALL_QUESTIONS.map(q => [q.id, q])
);

const UNIVERSAL_SEQUENCE = [
  "age_bracket","dependents","employment","emergency_buffer","investing_experience",
];

const TIER_SEQUENCES: Record<string, string[]> = {
  beginner:     ["b_goal","b_time_horizon","b_max_loss","b_invest_amount","b_gift_scenario","b_drop_test","b_priority"],
  intermediate: ["i_annual_income","i_portfolio_size","i_debt","i_primary_goal","i_time_horizon","i_crash_scenario","i_max_loss","i_past_panic"],
  expert:       ["e_portfolio_size","e_savings_rate","e_primary_goal","e_time_horizon","e_liquidity_need","e_drawdown_experience","e_max_loss","e_crisis_behavior"],
};

// answer_index → forced next question ID (overrides default sequence)
const BRANCH_RULES: Record<string, Record<number, string>> = {
  investing_experience: {0:"b_goal", 1:"b_goal", 2:"i_annual_income", 3:"e_portfolio_size", 4:"e_portfolio_size"},
  b_time_horizon:   {0: "b_invest_amount"},     // < 1 year → skip b_max_loss
  i_portfolio_size: {0: "i_primary_goal"},      // < ₹1L   → skip i_debt
  e_time_horizon:   {4: "e_drawdown_experience"}, // perpetual → skip e_liquidity_need
};

function detectTier(answers: Record<string, number | number[]>): string {
  const exp = answers["investing_experience"];
  if (exp === undefined) return "beginner";
  const map: Record<number, string> = {0:"beginner",1:"beginner",2:"intermediate",3:"expert",4:"expert"};
  return map[exp as number] ?? "beginner";
}

function buildPath(answers: Record<string, number | number[]>): string[] {
  const tier = detectTier(answers);
  const fullSequence = [...UNIVERSAL_SEQUENCE, ...TIER_SEQUENCES[tier]];
  const path: string[] = [];

  let i = 0;
  while (i < fullSequence.length) {
    const qid = fullSequence[i];
    path.push(qid);

    const ans = answers[qid];
    if (ans !== undefined && qid in BRANCH_RULES) {
      const forcedNext = BRANCH_RULES[qid][ans as number];
      if (forcedNext !== undefined) {
        const forcedIdx = fullSequence.indexOf(forcedNext);
        if (forcedIdx > i) { i = forcedIdx; continue; }
      }
    }
    i++;
  }
  return path;
}

/* ═══════════════════════════════════════════════════════════════
   SCORING (mirrors backend)
═══════════════════════════════════════════════════════════════ */
function computeResults(answers: Record<string, number | number[]>) {
  const path = buildPath(answers);
  const active = path.map(id => QUESTION_MAP[id]).filter(Boolean);
  let raw = 0, maxScore = 0;
  const biasVotes: Record<string, number> = {loss_averse:0, overconfident:0, balanced:0};

  active.forEach(q => {
    const ans = answers[q.id];
    if (ans === undefined) return;
    if (q.type === "radio" && typeof ans === "number") {
      const opt = q.options[ans];
      if (opt) { raw += opt.score; if (opt.bias) biasVotes[opt.bias]++; }
      maxScore += Math.max(...q.options.map(o => o.score));
    } else if (q.type === "multi" && Array.isArray(ans)) {
      ans.forEach(i => { const opt = q.options[i]; if (opt) { raw += opt.score; if (opt.bias) biasVotes[opt.bias]++; }});
      maxScore += q.options.reduce((s, o) => s + o.score, 0);
    }
  });

  const score = maxScore > 0 ? Math.round((raw / maxScore) * 100) : 50;
  const investorType = score < 35 ? "beginner" : score < 65 ? "intermediate" : "experienced";
  const bMax = Math.max(...Object.values(biasVotes));
  let bias = "balanced";
  if (bMax > 0) {
    if (biasVotes.loss_averse === bMax) bias = "loss_averse";
    else if (biasVotes.overconfident === bMax) bias = "overconfident";
  }

  const ALLOC_TABLE: Array<[number, Record<string, number>]> = [
    [25,  {"Equity / Stocks":10, "Mutual Funds":15, "Fixed Deposits / Debt":45, "Gold / SGBs":15, "Real Estate / REITs":15}],
    [40,  {"Equity / Stocks":20, "Mutual Funds":25, "Fixed Deposits / Debt":30, "Gold / SGBs":15, "Real Estate / REITs":10}],
    [55,  {"Equity / Stocks":35, "Mutual Funds":25, "Fixed Deposits / Debt":20, "Gold / SGBs":12, "Real Estate / REITs":8}],
    [70,  {"Equity / Stocks":45, "Mutual Funds":25, "Fixed Deposits / Debt":12, "Gold / SGBs":10, "Real Estate / REITs":8}],
    [85,  {"Equity / Stocks":55, "Mutual Funds":25, "Fixed Deposits / Debt":7,  "Gold / SGBs":7,  "Real Estate / REITs":6}],
    [101, {"Equity / Stocks":65, "Mutual Funds":22, "Fixed Deposits / Debt":3,  "Gold / SGBs":5,  "Real Estate / REITs":5}],
  ];
  let alloc = ALLOC_TABLE[ALLOC_TABLE.length - 1][1];
  for (const [t, a] of ALLOC_TABLE) { if (score < t) { alloc = a; break; } }

  return { score, investorType, bias, alloc };
}

/* ═══════════════════════════════════════════════════════════════
   DYNAMIC SUBTITLE (personalises i_max_loss with actual ₹)
═══════════════════════════════════════════════════════════════ */
const PORTFOLIO_EXAMPLES: Record<number, string> = {
  0: "e.g. on a ₹75k portfolio: 5% = ₹3,750 · 10% = ₹7,500 · 20% = ₹15,000",
  1: "e.g. on a ₹3L portfolio:  5% = ₹15,000 · 10% = ₹30,000 · 20% = ₹60,000",
  2: "e.g. on a ₹15L portfolio: 5% = ₹75k · 10% = ₹1.5L · 20% = ₹3L",
  3: "e.g. on a ₹60L portfolio: 10% = ₹6L · 20% = ₹12L · 30% = ₹18L",
  4: "e.g. on a ₹1Cr+ portfolio:10% = ₹10L · 20% = ₹20L · 30% = ₹30L",
};

function getDynamicSub(qid: string, answers: Record<string, number | number[]>): string | undefined {
  if (qid === "i_max_loss") {
    const ps = answers["i_portfolio_size"] as number | undefined;
    return ps !== undefined ? PORTFOLIO_EXAMPLES[ps] : "Think in actual rupees, not abstract percentages.";
  }
  return undefined;
}

/* ═══════════════════════════════════════════════════════════════
   DISPLAY CONFIG
═══════════════════════════════════════════════════════════════ */
const SECTION_LABELS: Record<string, string> = {
  foundation: "Getting to Know You",
  financial:  "Your Financial Picture",
  behavioral: "Your Risk Personality",
};

const INVESTOR_LABELS: Record<string, {label:string; sub:string; color:string}> = {
  beginner:     {label:"Conservative",  sub:"Capital preservation with steady growth",         color:"text-emerald-600"},
  intermediate: {label:"Balanced",      sub:"Growth with managed downside",                    color:"text-blue-600"},
  experienced:  {label:"Aggressive",    sub:"Growth-oriented — comfortable with volatility",   color:"text-amber-600"},
};

const BIAS_INFO: Record<string, {label:string; desc:string; cls:string}> = {
  loss_averse:   {label:"Loss Averse",   cls:"text-red-700 border-red-200 bg-red-50",    desc:"You weight losses more heavily than equivalent gains. You may sell too early or avoid necessary risk. We'll flag this in your recommendations."},
  overconfident: {label:"Overconfident", cls:"text-amber-700 border-amber-200 bg-amber-50", desc:"You may underestimate downside risk. We'll add guardrails to protect you from oversized bets."},
  balanced:      {label:"Balanced",      cls:"text-emerald-700 border-emerald-200 bg-emerald-50", desc:"You show a rational approach to risk and reward — unlikely to make emotionally-driven decisions under pressure."},
};

/* ═══════════════════════════════════════════════════════════════
   MAIN COMPONENT
═══════════════════════════════════════════════════════════════ */
export default function OnboardingPage() {
  const router = useRouter();
  const setRiskProfile = useFinStore(s => s.setRiskProfile);

  const [answers, setAnswers]           = useState<Record<string, number | number[]>>({});
  const [currentPathIdx, setCurrentPathIdx] = useState(0);
  const [direction, setDirection]       = useState<"fwd"|"bwd">("fwd");
  const [submitting, setSubmitting]     = useState(false);
  const [showResult, setShowResult]     = useState(false);
  const [result, setResult]             = useState<ReturnType<typeof computeResults> | null>(null);
  const [animScore, setAnimScore]       = useState(0);

  // Derived from answers every render
  const questionPath = buildPath(answers);
  const totalSteps   = questionPath.length;
  const currentQId   = questionPath[currentPathIdx] ?? questionPath[0];
  const q            = QUESTION_MAP[currentQId];

  const pct = totalSteps > 0 ? Math.round(((currentPathIdx + 1) / totalSteps) * 100) : 0;

  const hasAnswer = q
    ? (q.optional
        || (q.type === "multi" ? Array.isArray(answers[q.id]) && (answers[q.id] as number[]).length > 0 : answers[q.id] !== undefined))
    : false;

  /* ── answer handlers ────────────────────────────────────────────────────── */
  function selectRadio(optIdx: number) {
    const newAnswers = { ...answers, [q.id]: optIdx };
    setAnswers(newAnswers);

    // Auto-advance after a short delay for better UX
    setTimeout(() => {
      const newPath = buildPath(newAnswers);
      const nextIdx = currentPathIdx + 1;
      if (nextIdx < newPath.length) {
        setDirection("fwd");
        setCurrentPathIdx(nextIdx);
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        handleSubmit(newAnswers);
      }
    }, 300);
  }

  function toggleMulti(optIdx: number) {
    setAnswers(prev => {
      const cur = (prev[q.id] as number[] | undefined) ?? [];
      const next = cur.includes(optIdx) ? cur.filter(i => i !== optIdx) : [...cur, optIdx];
      return { ...prev, [q.id]: next };
    });
  }

  /* ── navigation ─────────────────────────────────────────────────────────── */
  function goNext() {
    const nextIdx = currentPathIdx + 1;
    if (nextIdx < questionPath.length) {
      setDirection("fwd");
      setCurrentPathIdx(nextIdx);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      handleSubmit(answers);
    }
  }

  function goBack() {
    if (currentPathIdx > 0) {
      setDirection("bwd");
      setCurrentPathIdx(i => i - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  /* ── submit ─────────────────────────────────────────────────────────────── */
  async function handleSubmit(finalAnswers = answers) {
    setSubmitting(true);
    const r = computeResults(finalAnswers);
    setResult(r);

    try {
      const res: Record<string, unknown> = await apiSubmitQuestionnaire({ answers: finalAnswers });
      setRiskProfile({
        risk_level: (res.investor_type as string) || r.investorType,
        score: (res.risk_score as number) || r.score,
        behavioral_bias: (res.behavioral_bias as string) || r.bias,
        recommended_allocation: (res.recommended_allocation as Record<string, number>) || r.alloc,
      });
    } catch {
      setRiskProfile({
        risk_level: r.investorType,
        score: r.score,
        behavioral_bias: r.bias,
        recommended_allocation: r.alloc,
      });
    }

    setSubmitting(false);
    setShowResult(true);

    // Animate score counter
    let cur = 0;
    const inc = r.score / 60;
    const timer = setInterval(() => {
      cur = Math.min(cur + inc, r.score);
      setAnimScore(Math.round(cur));
      if (cur >= r.score) clearInterval(timer);
    }, 16);
  }

  /* ═══════════════════════════════════════════════════════════════
     RESULT SCREEN
  ═══════════════════════════════════════════════════════════════ */
  if (showResult && result) {
    const typeInfo = INVESTOR_LABELS[result.investorType] ?? INVESTOR_LABELS.intermediate;
    const biasInfo = BIAS_INFO[result.bias] ?? BIAS_INFO.balanced;
    const circumference = 2 * Math.PI * 38;
    const offset = circumference - (animScore / 100) * circumference;

    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-start py-16 px-4 animate-in fade-in duration-500">
        <div className="w-full max-w-2xl space-y-6">
          {/* Header */}
          <div className="text-center space-y-2">
            <span className="inline-block text-xs font-semibold uppercase tracking-widest text-blue-700 border border-blue-200 bg-blue-50 rounded-full px-4 py-1">
              Your Investor Profile
            </span>
            <h1 className={cn("text-4xl font-bold mt-3", typeInfo.color)}>{typeInfo.label}</h1>
            <p className="text-slate-500 text-sm">{typeInfo.sub}</p>
          </div>

          {/* Score + Bias */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col items-center gap-3 shadow-sm">
              <p className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Risk Score</p>
              <svg viewBox="0 0 100 100" className="w-28 h-28">
                <circle cx="50" cy="50" r="38" fill="none" stroke="#E2E8F0" strokeWidth="8"/>
                <circle cx="50" cy="50" r="38" fill="none" stroke="#2563EB" strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={offset}
                  transform="rotate(-90 50 50)"
                  style={{transition:"stroke-dashoffset 0.05s linear"}}
                />
                <text x="50" y="55" textAnchor="middle" fontSize="22" fontWeight="bold" fill="#0F172A">{animScore}</text>
              </svg>
              <p className="text-xs text-slate-500 text-center leading-relaxed px-2">
                {animScore < 35 ? "Low risk tolerance — safety first" : animScore < 65 ? "Balanced risk appetite" : "High risk tolerance — growth-oriented"}
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col gap-3 shadow-sm">
              <p className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Behavioral Bias</p>
              <span className={cn("inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-semibold border w-fit", biasInfo.cls)}>
                {biasInfo.label}
              </span>
              <p className="text-xs text-slate-600 leading-relaxed">{biasInfo.desc}</p>
            </div>
          </div>

          {/* Allocation */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <p className="text-xs text-slate-400 uppercase tracking-widest font-semibold mb-5">Recommended Allocation</p>
            <div className="space-y-4">
              {Object.entries(result.alloc).map(([name, pct]) => (
                <div key={name} className="flex items-center gap-3">
                  <span className="text-sm text-slate-600 w-40 flex-shrink-0">{name}</span>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-600 rounded-full transition-all duration-1000"
                      style={{width:`${pct}%`}}
                    />
                  </div>
                  <span className="text-sm font-semibold text-slate-900 w-9 text-right">{pct}%</span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-center text-xs text-slate-400 px-4 leading-relaxed">
            FinVoice is a decision-support tool. Invest at your own risk. Consult a SEBI-registered advisor for personalised advice.
          </p>

          <button
            id="btn-view-dashboard"
            onClick={() => router.push("/dashboard")}
            className="w-full py-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold transition-all shadow-sm flex items-center justify-center gap-2"
          >
            View My Dashboard <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    );
  }

  if (!q) return null;

  const sectionLabel = SECTION_LABELS[q.section] ?? q.section;
  const dynamicSub   = getDynamicSub(q.id, answers) ?? q.sub;

  /* ═══════════════════════════════════════════════════════════════
     QUESTION SCREEN
  ═══════════════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* ── Progress bar ─────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-white border-b border-slate-200 px-4 py-4 shadow-sm">
        <div className="max-w-2xl mx-auto">
          <div className="flex justify-between items-center mb-2.5">
            <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">{sectionLabel}</span>
            <span className="text-xs text-slate-400">{currentPathIdx + 1} / {totalSteps}</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 rounded-full transition-all duration-500"
              style={{width:`${pct}%`}}
            />
          </div>
        </div>
      </div>

      {/* ── Question card ─────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center px-4 pt-10 pb-32">
        <div
          key={q.id}
          className={cn(
            "w-full max-w-2xl",
            direction === "fwd" ? "animate-in slide-in-from-right-8 fade-in duration-300" : "animate-in slide-in-from-left-8 fade-in duration-300"
          )}
        >
          {/* Conditional badge */}
          {q.conditional && (
            <div className="flex items-center gap-2 mb-4 text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 w-fit">
              <Info className="w-3.5 h-3.5 flex-shrink-0" />
              <span>This question appeared based on your earlier answer</span>
            </div>
          )}

          <h2 className="text-2xl font-bold text-slate-900 leading-snug mb-3">{q.text}</h2>

          {dynamicSub && (
            <p className="text-sm text-slate-500 mb-6 leading-relaxed border-l-2 border-blue-300 pl-3">
              {dynamicSub}
            </p>
          )}

          {/* ── Radio options ─────────────────────────────────────────────────── */}
          {q.type === "radio" && (
            <div className="space-y-3">
              {q.options.map((opt, i) => {
                const selected = answers[q.id] === i;
                return (
                  <button
                    key={i}
                    id={`opt-${q.id}-${i}`}
                    onClick={() => selectRadio(i)}
                    className={cn(
                      "w-full text-left rounded-xl border px-5 py-4 transition-all duration-200 group",
                      selected
                        ? "border-blue-500 bg-blue-50 shadow-[0_0_0_1px_rgba(37,99,235,0.2)]"
                        : "border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50 shadow-sm"
                    )}
                  >
                    <div className="flex items-start gap-4">
                      {/* Indicator */}
                      <div className={cn(
                        "w-5 h-5 rounded-full border-2 flex-shrink-0 mt-0.5 flex items-center justify-center transition-all duration-200",
                        selected ? "border-blue-600 bg-blue-600" : "border-slate-300 group-hover:border-blue-400"
                      )}>
                        {selected && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
                      </div>
                      {/* Label */}
                      <div className="flex-1">
                        <p className={cn("text-sm font-medium leading-snug transition-colors", selected ? "text-slate-900" : "text-slate-600")}>
                          {opt.label}
                        </p>
                        {opt.desc && (
                          <p className="text-xs text-slate-400 mt-1">{opt.desc}</p>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* ── Multi-select options ─────────────────────────────────────────── */}
          {q.type === "multi" && (
            <div className="space-y-3">
              {q.options.map((opt, i) => {
                const selected = Array.isArray(answers[q.id]) && (answers[q.id] as number[]).includes(i);
                return (
                  <button
                    key={i}
                    id={`opt-${q.id}-${i}`}
                    onClick={() => toggleMulti(i)}
                    className={cn(
                      "w-full text-left rounded-xl border px-5 py-4 transition-all duration-200 group",
                      selected
                        ? "border-blue-500 bg-blue-50 shadow-[0_0_0_1px_rgba(37,99,235,0.2)]"
                        : "border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50 shadow-sm"
                    )}
                  >
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "w-5 h-5 rounded border-2 flex-shrink-0 flex items-center justify-center transition-all duration-200",
                        selected ? "border-blue-600 bg-blue-600" : "border-slate-300 group-hover:border-blue-400"
                      )}>
                        {selected && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
                      </div>
                      <p className={cn("text-sm font-medium transition-colors", selected ? "text-slate-900" : "text-slate-600")}>
                        {opt.label}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Bottom nav ───────────────────────────────────────────────────────── */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 px-4 py-4 z-20 shadow-[0_-1px_8px_rgba(0,0,0,0.06)]">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          {currentPathIdx > 0 && (
            <button
              id="btn-back"
              onClick={goBack}
              className="flex items-center gap-2 px-5 py-3.5 rounded-xl border border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300 hover:bg-slate-50 transition-all text-sm font-medium"
            >
              <ChevronLeft className="w-4 h-4" /> Back
            </button>
          )}

          {q.type !== "radio" && (
            <button
              id="btn-next"
              onClick={goNext}
              disabled={!hasAnswer || submitting}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 py-3.5 rounded-xl font-semibold text-sm transition-all",
                hasAnswer
                  ? "bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
                  : "bg-slate-100 text-slate-400 cursor-not-allowed"
              )}
            >
              {submitting ? "Analysing..." : currentPathIdx === questionPath.length - 1 ? "See My Profile" : "Continue"}
              {!submitting && <ChevronRight className="w-4 h-4" />}
            </button>
          )}

          {q.type === "radio" && answers[q.id] !== undefined && (
            <p className="text-xs text-slate-400 text-center flex-1">
              {currentPathIdx === questionPath.length - 1 ? "Submitting…" : "Moving to next question…"}
            </p>
          )}

          {q.optional && q.type !== "radio" && (
            <button id="btn-skip" onClick={goNext} className="text-xs text-slate-400 hover:text-slate-600 underline underline-offset-2 transition-colors">
              Skip
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
