import { create } from 'zustand';

interface RiskProfile {
  risk_level: string;
  score?: number;
  behavioral_bias?: string;
  recommended_allocation?: Record<string, number>;
}

interface PortfolioItem {
  symbol: string;
  name?: string;
  units: number;
  avg_price: number;
  current_price?: number;
  sector?: string;
  asset_class?: string;
}

interface PortfolioAnalysis {
  total_value: number;
  total_pnl: number;
  total_pnl_percent: number;
  currency: string;
  asset_allocation: Record<string, number>;
  sector_allocation?: Record<string, number>;
  risk_metrics?: unknown;
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
