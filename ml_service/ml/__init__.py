"""
FinVoice ML Package — Quantitative ML Pipeline for NSE/Nifty 50.

Modules:
    feature_engineering: OHLCV download, technical indicators, macro data, feature assembly
    regime_detector: GMM/HMM market regime classification
    xgboost_model: XGBoost & CatBoost gradient-boosted tree models
    lstm_model: TFT and vanilla LSTM deep-learning models
    ensemble: Stacking meta-learner combining all base models
    rl_agent: SAC reinforcement-learning agent for portfolio optimisation
    model_registry: MLflow model versioning and promotion utilities
"""

__version__ = "1.0.0"
