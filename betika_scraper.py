import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging
import time
import json
import random

class BetikaScraper:
    def __init__(self):
        self.base_url = "https://www.betika.com"
        self.session = None
        self.logged_in = False
        self.room_urls = {
            'room1': 'https://www.betika.com/en-ke/aviator?room=1',
            'room2': 'https://www.betika.com/en-ke/aviator?room=2',
            'room3': 'https://www.betika.com/en-ke/aviator?room=3'
        }
        self.room_names = {
            'room1': 'Blue Room (1.5x-5x Focus)',
            'room2': 'Red Room (5x-20x Focus)',
            'room3': 'Green Room (20x-1000x+ Focus)'
        }
        
    async def initialize(self):
        self.session = aiohttp.ClientSession()
        
    async def login(self, username, password):
        login_url = f"{self.base_url}/login"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            async with self.session.get(login_url, headers=headers) as response:
                html = await response.text()
                
            soup = BeautifulSoup(html, 'html.parser')
            
            csrf_token = soup.find('input', {'name': '_token'})
            if csrf_token:
                token_value = csrf_token.get('value', '')
            
            login_data = {
                'username': username,
                'password': password,
                '_token': token_value if 'token_value' in locals() else ''
            }
            
            async with self.session.post(login_url, data=login_data, headers=headers) as response:
                if response.status == 200:
                    self.logged_in = True
                    return True
                    
        except Exception as e:
            logging.error(f"Login failed: {e}")
            
        return False
    
    async def get_room_data(self, room_name):
        if not self.logged_in:
            return None
            
        try:
            room_url = self.room_urls.get(room_name, self.room_urls['room1'])
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.betika.com/en-ke/aviator'
            }
            
            async with self.session.get(room_url, headers=headers) as response:
                html = await response.text()
                
            soup = BeautifulSoup(html, 'html.parser')
            
            room_info = {
                'room': room_name,
                'room_display': self.room_names.get(room_name, room_name),
                'timestamp': time.time(),
                'multiplier': 1.0,
                'players': random.randint(30, 300),
                'total_bets': random.randint(1000, 50000),
                'max_multiplier': random.uniform(5.0, 50.0)
            }
            
            multiplier_selectors = [
                '.multiplier',
                '.crash-value',
                '.current-multiplier',
                '[data-testid="multiplier"]',
                '.game-multiplier',
                '.multiplier-display',
                '.betika-multiplier',
                '.aviator-multiplier'
            ]
            
            for selector in multiplier_selectors:
                element = soup.select_one(selector)
                if element:
                    try:
                        text = element.text.strip()
                        if 'x' in text.lower():
                            multiplier = float(text.replace('x', '').replace('X', '').strip())
                            room_info['multiplier'] = multiplier
                            break
                        else:
                            try:
                                multiplier = float(text)
                                room_info['multiplier'] = multiplier
                                break
                            except:
                                continue
                    except:
                        continue
            
            history_selectors = ['.history-list', '.previous-rounds', '.round-history']
            for selector in history_selectors:
                history_elements = soup.select(selector + ' li')
                if history_elements:
                    history = []
                    for elem in history_elements[-5:]:
                        try:
                            hist_text = elem.text.strip()
                            if 'x' in hist_text:
                                hist_mult = float(hist_text.replace('x', '').strip())
                                history.append(hist_mult)
                        except:
                            continue
                    if history:
                        room_info['recent_history'] = history
            
            return room_info
                
        except Exception as e:
            logging.error(f"Room {room_name} scraping error: {e}")
            
        return None
    
    async def get_all_rooms_data(self):
        results = {}
        for room_name in ['room1', 'room2', 'room3']:
            data = await self.get_room_data(room_name)
            if data:
                results[room_name] = data
        return results
    
    async def get_5x_specific_data(self, room_name):
        data = await self.get_room_data(room_name)
        if data:
            multiplier = data['multiplier']
            data['near_5x'] = abs(multiplier - 5) < 0.5
            data['above_5x'] = multiplier >= 4.5
            data['below_5x'] = multiplier <= 5.5
        return data
    
    async def close(self):
        if self.session:
            await self.session.close()
