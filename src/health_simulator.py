
import pandas as pd
import random

class HealthSimulator:
    def generate_data(self, n_samples=1000):
        """
        Generates a dataset with causal links.
        - Diet and Exercise causally affect Health.
        - IceCreamConsumption is correlated with Health, but not causal.
        """
        data = []
        for _ in range(n_samples):
            diet = random.choice(["Good", "Poor"])
            exercise = random.choice(["Regular", "Irregular"])
            
            # Ice cream consumption is correlated with diet
            if diet == "Poor":
                ice_cream_consumption = random.choice(["High", "Low", "Medium"])
            else:
                ice_cream_consumption = "Low"
                
            # Health is causally affected by diet and exercise
            health_score = 0
            if diet == "Good":
                health_score += 50
            if exercise == "Regular":
                health_score += 50
            
            health = "Good" if health_score >= 50 else "Poor"
            
            data.append([diet, exercise, ice_cream_consumption, health])
            
        df = pd.DataFrame(data, columns=["Diet", "Exercise", "IceCreamConsumption", "Health"])
        df.to_csv("health_data.csv", index=False)
        return df
