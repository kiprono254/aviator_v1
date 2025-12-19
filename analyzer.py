import random
from datetime import datetime
import json
import os
import time

class AviatorAnalyzer:
    def __init__(self):
        self.room_histories = {
            'room1': [],
            'room2': [],
            'room3': []
        }
        self.targets = [1.5, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 1000]
        self.load_histories()
        self.prediction_cache = {}
    
    def load_histories(self):
        """Load historical data for each room"""
        for room in ['room1', 'room2', 'room3']:
            filename = f"{room}_data.json"
            if os.path.exists(filename):
                try:
                    with open(filename, 'r') as f:
                        self.room_histories[room] = json.load(f)
                    print(f"Loaded {len(self.room_histories[room])} records for {room}")
                except:
                    self.room_histories[room] = []
            else:
                self.room_histories[room] = []
    
    def get_prediction(self, room_name):
        """Generate prediction for a specific room"""
        try:
            # Simulate getting live data (replace with actual scraping)
            live_data = self.simulate_live_data(room_name)
            
            # Add to history
            self.room_histories[room_name].append(live_data)
            
            # Keep only last 1000 records
            if len(self.room_histories[room_name]) > 1000:
                self.room_histories[room_name] = self.room_histories[room_name][-1000:]
            
            # Save to file
            self.save_room_history(room_name)
            
            # Analyze patterns
            return self.analyze_patterns(room_name)
            
        except Exception as e:
            print(f"Prediction error for {room_name}: {e}")
            return self.get_fallback_prediction(room_name)
    
    def simulate_live_data(self, room_name):
        """Simulate live data from Betika (REPLACE WITH ACTUAL SCRAPING)"""
        # Room-specific behavior
        room_profiles = {
            'room1': {'min': 1.0, 'max': 10.0, 'volatility': 0.5},
            'room2': {'min': 1.0, 'max': 25.0, 'volatility': 1.0},
            'room3': {'min': 1.0, 'max': 100.0, 'volatility': 2.0}
        }
        
        profile = room_profiles.get(room_name, {'min': 1.0, 'max': 5.0, 'volatility': 0.5})
        
        # Generate multiplier with some randomness
        base = random.uniform(profile['min'], profile['max'] / 2)
        volatility = random.uniform(0, profile['volatility'])
        multiplier = base * (1 + volatility)
        
        # Occasionally generate very high multipliers
        if random.random() < 0.05:  # 5% chance
            multiplier = random.uniform(profile['max'] * 0.7, profile['max'] * 1.3)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'multiplier': round(multiplier, 2),
            'room': room_name,
            'round_id': len(self.room_histories[room_name]) + 1
        }
    
    def analyze_patterns(self, room_name):
        """Analyze historical patterns for predictions"""
        history = self.room_histories[room_name]
        
        if len(history) < 10:
            return self.get_fallback_prediction(room_name)
        
        # Get recent multipliers
        recent_count = min(30, len(history))
        recent = history[-recent_count:]
        multipliers = [d['multiplier'] for d in recent]
        
        # Calculate statistics
        avg_multiplier = sum(multipliers) / len(multipliers)
        max_recent = max(multipliers)
        min_recent = min(multipliers)
        
        # Determine trend
        trend = self.determine_trend(multipliers)
        
        # Calculate confidence
        confidence = self.calculate_confidence(multipliers, len(history))
        
        # Generate prediction
        prediction = {
            'timestamp': datetime.now().isoformat(),
            'room': room_name,
            'trend': trend,
            'confidence': confidence,
            'recent_high': max_recent,
            'recent_low': min_recent,
            'average': round(avg_multiplier, 2),
            'data_points': len(multipliers)
        }
        
        # Calculate probabilities for each target
        for target in self.targets:
            probability = self.calculate_probability(target, multipliers, avg_multiplier, room_name)
            prediction[f'prob_{target}x'] = round(probability, 3)
        
        return prediction
    
    def determine_trend(self, multipliers):
        """Determine the current trend"""
        if len(multipliers) < 5:
            return "ANALYZING"
        
        # Check last 5 values
        last_5 = multipliers[-5:]
        
        # Check if consistently rising
        rising = all(last_5[i] <= last_5[i+1] for i in range(len(last_5)-1))
        if rising:
            return "STRONG UP"
        
        # Check if consistently falling
        falling = all(last_5[i] >= last_5[i+1] for i in range(len(last_5)-1))
        if falling:
            return "STRONG DOWN"
        
        # Count ups and downs
        up_count = sum(1 for i in range(len(last_5)-1) if last_5[i] < last_5[i+1])
        
        if up_count >= 3:
            return "UPWARD"
        elif up_count <= 1:
            return "DOWNWARD"
        
        return "VOLATILE"
    
    def calculate_confidence(self, multipliers, total_history):
        """Calculate confidence level"""
        base_confidence = 0.5
        
        # More data = more confidence
        if total_history >= 100:
            base_confidence += 0.2
        elif total_history >= 50:
            base_confidence += 0.1
        
        # Check volatility
        volatility = self.calculate_volatility(multipliers)
        if volatility < 1.0:
            base_confidence += 0.1
        elif volatility > 3.0:
            base_confidence -= 0.1
        
        # Check for clear patterns
        if self.has_clear_pattern(multipliers):
            base_confidence += 0.15
        
        return min(max(base_confidence, 0.1), 0.95)
    
    def calculate_volatility(self, multipliers):
        """Calculate volatility of multipliers"""
        if len(multipliers) < 2:
            return 0.0
        
        mean = sum(multipliers) / len(multipliers)
        variance = sum((x - mean) ** 2 for x in multipliers) / len(multipliers)
        return variance ** 0.5
    
    def has_clear_pattern(self, multipliers):
        """Check for clear patterns in data"""
        if len(multipliers) < 10:
            return False
        
        # Simple pattern detection
        # Check for clustering of similar values
        clusters = 0
        threshold = 1.0
        
        for i in range(len(multipliers) - 1):
            if abs(multipliers[i] - multipliers[i+1]) < threshold:
                clusters += 1
        
        return clusters / len(multipliers) > 0.6
    
    def calculate_probability(self, target, multipliers, average, room_name):
        """Calculate probability of reaching target multiplier"""
        if len(multipliers) < 5:
            return 0.1
        
        # Room-specific base probabilities
        room_bases = {
            'room1': {t: 0.3 if t <= 5 else 0.1 for t in self.targets},
            'room2': {t: 0.4 if t <= 20 else 0.2 for t in self.targets},
            'room3': {t: 0.5 if t >= 20 else 0.3 for t in self.targets}
        }
        
        base_prob = room_bases.get(room_name, {}).get(target, 0.2)
        
        # Adjust based on recent performance
        recent_hits = sum(1 for m in multipliers if m >= target * 0.7)
        hit_ratio = recent_hits / len(multipliers)
        
        # Adjust based on average
        avg_factor = 1.0
        if average > target * 0.5:
            avg_factor = 1.2
        elif average > target * 0.3:
            avg_factor = 1.1
        
        # Calculate final probability
        probability = base_prob * (1 + hit_ratio) * avg_factor
        
        # Special boost for 5x
        if target == 5:
            near_5x = sum(1 for m in multipliers if 4 <= m <= 6)
            if near_5x > 0:
                probability *= 1.3
        
        return min(probability, 0.95)
    
    def get_fallback_prediction(self, room_name):
        """Fallback prediction when insufficient data"""
        prediction = {
            'timestamp': datetime.now().isoformat(),
            'room': room_name,
            'trend': 'INSUFFICIENT_DATA',
            'confidence': 0.2,
            'recent_high': 0,
            'recent_low': 0,
            'average': 0,
            'data_points': 0
        }
        
        for target in self.targets:
            prediction[f'prob_{target}x'] = 0.1
        
        return prediction
    
    def save_room_history(self, room_name):
        """Save room history to file"""
        filename = f"{room_name}_data.json"
        try:
            with open(filename, 'w') as f:
                json.dump(self.room_histories[room_name][-500:], f, indent=2)
        except Exception as e:
            print(f"Save error for {room_name}: {e}")
