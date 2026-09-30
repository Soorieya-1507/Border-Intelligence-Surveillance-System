from app.config import settings
from app.models.schemas import RiskFactor
from datetime import datetime

class RiskEngine:
    @staticmethod
    def calculate_risk(factors_present: list[str]) -> tuple[int, list[RiskFactor]]:
        """
        Calculates the explainable risk score based on triggered rules and conditions.
        """
        score = 0
        risk_factors = []
        
        for factor in factors_present:
            if factor in settings.RISK_WEIGHTS:
                weight = settings.RISK_WEIGHTS[factor]
                score += weight
                risk_factors.append(RiskFactor(description=factor, score=weight))
                
        # Time-based risk (Night hours: 6 PM to 6 AM)
        hour = datetime.now().hour
        if hour >= 18 or hour < 6:
            night_weight = settings.RISK_WEIGHTS.get("Night Hours", 25)
            score += night_weight
            risk_factors.append(RiskFactor(description="Night Hours", score=night_weight))
            
        final_score = min(100, score)
        return final_score, risk_factors
