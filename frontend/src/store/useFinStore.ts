import { create } from 'zustand';

// Assuming schemas based on standard FastAPI response
interface RiskProfile {
  risk_level: string; // 'Conservative', 'Moderate', 'Aggressive'
  score?: number;
}

interface PortfolioItem {
  symbol: string;
  name?: string;
  units: number;
  avg_price: number;
  current_price?: number;
  sector?: string;
  asset_class?: string;
  currency?: string;
}

interface PortfolioAnalysis {
  total_value: number;
  total_pnl: number;
  total_pnl_percent: number;
  currency: string;
  asset_allocation: Record<string, number>; // { 'Equity': 70, 'Debt': 30 }
  sector_allocation?: Record<string, number>;
  risk_metrics?: any;
}

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

interface FinStoreState {
  user: User | null;
  token: string | null;
  riskProfile: RiskProfile | null;
  portfolioHoldings: PortfolioItem[];
  portfolioAnalysis: PortfolioAnalysis | null;
  isLoggedIn: boolean;

  // Actions
  login: (token: string, user: User) => void;
  logout: () => void;
  setRiskProfile: (profile: RiskProfile) => void;
  setPortfolioData: (items: PortfolioItem[], analysis: PortfolioAnalysis) => void;
}

export const useFinStore = create<FinStoreState>((set) => ({
  user: null,
  token: null,
  riskProfile: null,
  portfolioHoldings: [],
  portfolioAnalysis: null,
  isLoggedIn: false,

  login: (token, user) => set({ token, user, isLoggedIn: true }),
  logout: () => set({ token: null, user: null, riskProfile: null, portfolioHoldings: [], portfolioAnalysis: null, isLoggedIn: false }),
  setRiskProfile: (profile) => set({ riskProfile: profile }),
  setPortfolioData: (items, analysis) => set({ portfolioHoldings: items, portfolioAnalysis: analysis }),
}));
