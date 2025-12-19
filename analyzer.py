import random
from datetime import datetime
import json
import os

class AviatorAnalyzer:
    def __init__(self):
        self.room_histories = {
            'room1': [],
            'room2': [],
            'room3': []
        }
        self.targets = [1.5, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 1000]
        self.load_histories()
        
    def load_histories(self):
        for room in ['room1', 'room2', 'room3']:
            filename = f"{room}_data.json"
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    self.room_histories[room] = json.load(f)
    
    def get_prediction(self, room_name):
        try:
            latest_data = self.simulate_room_scraping(room_name)
            self.room_histories[room_name].append(latest_data)
            
            if len(self.room_histories[room_name]) > 1000:
                self.room_histories[room_name] = self.room_histories[room_name][-1000:]
            
            self.save_room_history(room_name)
            
            return self.analyze_room_patterns(room_name)
            
        except Exception as e:
            print(f"Error in get_prediction for {room_name}: {e}")
            return self.get_fallback_prediction(room_name)
    
    def simulate_room_scraping(self, room_name):
        room_ranges = {
            'room1': (1.0, 10.0),
            'room2': (1.0, 25.0),
            'room3': (1.0, 100.0)
        }
        
        min_val, max_val = room_ranges.get(room_name, (1.0, 5.0))
        
        return {
            'timestamp': datetime.now().isoformat(),
            'multiplier': random.uniform(min_val, max_val),
            'round_id': len(self.room_histories[room_name]) + 1,
            'room': room_name
        }
    
    def analyze_room_patterns(self, room_name):
        history = self.room_histories[room_name]
        
        if len(history) < 30:
            return self.get_fallback_prediction(room_name)
        
        recent = history[-30:]
        multipliers = [d['multiplier'] for d in recent]
        
        avg = sum(multipliers) / len(multipliers)
        max_val = max(multipliers)
        
        room_trends = {
            'room1': ['STEADY', 'VOLATILE', 'RISING', 'SAFE'],
            'room2': ['AGGRESSIVE', 'UNPREDICTABLE', 'SURGING', 'BALANCED'],
            'room3': ['EXTREME', 'EXPLOSIVE', 'RAPID', 'HIGH RISK']
        }
        
        trend = self.determine_trend(multipliers, room_name)
        
        prediction = {
            'timestamp': datetime.now().isoformat(),
            'room': room_name,
            'trend': trend,
            'confidence': self.calculate_confidence(multipliers, room_name),
            'recent_high': max_val,
            'volatility': self.calculate_volatility(multipliers)
        }
        
        for target in self.targets:
            prob = self.calculate_room_probability(target, multipliers, avg, room_name)
            prediction[f'prob_{target}x'] = prob
        
        return prediction
    
    def determine_trend(self, multipliers, room_name):
        if len(multipliers) < 5:
            return "ANALYZING"
        
        last_5 = multipliers[-5:]
        
        if all(last_5[i] <= last_5[i+1] for i in range(len(last_5)-1)):
            return "STRONG UP"
        elif all(last_5[i] >= last_5[i+1] for i in range(len(last_5)-1)):
            return "STRONG DOWN"
        
        up_count = sum(1 for i in range(len(last_5)-1) if last_5[i] < last_5[i+1])
        
        if up_count >= 3:
            return "UPWARD"
        elif up_count <= 1:
            return "DOWNWARD"
        return "VOLATILE"
    
    def calculate_confidence(self, multipliers, room_name):
        if len(multipliers) < 10:
            return 0.3
        
        base_confidence = 0.5
        
        volatility = self.calculate_volatility(multipliers)
        
        if volatility < 1.0:
            base_confidence += 0.2
        elif volatility > 3.0:
            base_confidence -= 0.1
        
        recent_5x = sum(1 for m in multipliers[-10:] if m >= 5)
        if recent_5x >= 3:
            base_confidence += 0.15
        
        return min(max(base_confidence, 0.1), 0.95)
    
    def calculate_room_probability(self, target, multipliers, avg, room_name):
        if len(multipliers) < 5:
            return 0.1
        
        recent_count = min(20, len(multipliers))
        recent = multipliers[-recent_count:]
        
        near_target = sum(1 for m in recent if m >= target * 0.7)
        ratio = near_target / recent_count
        
        room_boost = {
            'room1': {1.5: 1.8, 2: 1.6, 3: 1.4, 4: 1.2, 5: 1.5, 10: 0.8, 20: 0.6, 30: 0.4, 40: 0.3, 50: 0.2, 60: 0.2, 70: 0.2, 80: 0.2, 90: 0.1, 100: 0.1, 1000: 0.05},
            'room2': {1.5: 1.3, 2: 1.4, 3: 1.5, 4: 1.6, 5: 1.8, 10: 1.5, 20: 1.2, 30: 1.0, 40: 0.8, 50: 0.7, 60: 0.6, 70: 0.5, 80: 0.4, 90: 0.3, 100: 0.3, 1000: 0.2},
            'room3': {1.5: 0.8, 2: 0.9, 3: 1.0, 4: 1.1, 5: 1.2, 10: 1.5, 20: 1.8, 30: 2.0, 40: 2.2, 50: 2.3, 60: 2.4, 70: 2.5, 80: 2.6, 90: 2.7, 100: 2.8, 1000: 3.0}
        }
        
        boost = room_boost.get(room_name, {}).get(target, 1.0)
        
        volatility = self.calculate_volatility(recent)
        volatility_factor = 1.0 + (volatility * 0.1)
        
        if target == 5:
            recent_5x_hits = sum(1 for m in recent if m >= 4.5 and m <= 5.5)
            if recent_5x_hits > 0:
                boost *= 1.3
        
        base_prob = min(ratio * 2.5 * boost * volatility_factor, 0.95)
        
        return base_prob
    
    def calculate_volatility(self, multipliers):
        if len(multipliers) < 2:
            return 0.0
        
        mean = sum(multipliers) / len(multipliers)
        variance = sum((x - mean) ** 2 for x in multipliers) / len(multipliers)
        return variance ** 0.5
    
    def get_fallback_prediction(self, room_name):
        prediction = {
            'timestamp': datetime.now().isoformat(),
            'room': room_name,
            'trend': 'ANALYZING',
            'confidence': 0.2,
            'recent_high': 0,
            'volatility': 0
        }
        
        for target in self.targets:
            prediction[f'prob_{target}x'] = 0.1
        
        return prediction
    
    def save_room_history(self, room_name):
        filename = f"{room_name}_data.json"
        with open(filename, 'w') as f:
            json.dump(self.room_histories[room_name][-1000:], f)
