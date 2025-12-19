import asyncio
import logging
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from analyzer import AviatorAnalyzer
import aiohttp
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

TELEGRAM_TOKEN = config['telegram_token']
LEARNING_DURATION = config.get('learning_duration', 180)  # 3 minutes default

class AviatorMonitorSystem:
    def __init__(self):
        self.analyzer = AviatorAnalyzer()
        self.user_preferences = {}
        self.scraping = False
        self.learning_start_times = {}  # Track learning periods
        self.learning_duration = LEARNING_DURATION
        
        # Initialize room data
        self.room_data = {}
        for room_name in ['room1', 'room2', 'room3']:
            self.room_data[room_name] = {
                'active': False,
                'users': set(),
                'learning_users': set(),  # Users in learning phase
                'history': []
            }
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        keyboard = [
            [InlineKeyboardButton("🎮 Room 1 (1.5x-5x)", callback_data='room_1')],
            [InlineKeyboardButton("🎮 Room 2 (5x-20x)", callback_data='room_2')],
            [InlineKeyboardButton("🎮 Room 3 (20x-1000x+)", callback_data='room_3')],
            [InlineKeyboardButton("📊 All Rooms", callback_data='room_all')],
            [InlineKeyboardButton("📈 Status", callback_data='status')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 *Aviator Analysis Bot*\n\n"
            "Select which room to monitor:\n"
            "• Room 1: Low Risk (1.5x-5x focus)\n"
            "• Room 2: Medium Risk (5x-20x focus)\n"
            "• Room 3: High Risk (20x-1000x+ focus)\n\n"
            "Each room has a 3-5 minute learning phase for better predictions!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == 'room_1':
            await self.select_room(user_id, 'room1', query)
        elif query.data == 'room_2':
            await self.select_room(user_id, 'room2', query)
        elif query.data == 'room_3':
            await self.select_room(user_id, 'room3', query)
        elif query.data == 'room_all':
            await self.select_all_rooms(user_id, query)
        elif query.data == 'status':
            await self.send_status_update(user_id, query)
    
    async def select_room(self, user_id, room_name, query):
        # Remove user from any other rooms
        for room in ['room1', 'room2', 'room3']:
            if user_id in self.room_data[room]['users']:
                self.room_data[room]['users'].remove(user_id)
            if user_id in self.room_data[room]['learning_users']:
                self.room_data[room]['learning_users'].remove(user_id)
        
        # Add to new room with learning phase
        self.user_preferences[user_id] = {'room': room_name}
        self.room_data[room_name]['users'].add(user_id)
        self.room_data[room_name]['learning_users'].add(user_id)
        self.room_data[room_name]['active'] = True
        
        # Set learning start time
        learning_key = (user_id, room_name)
        self.learning_start_times[learning_key] = time.time()
        
        # Start learning countdown
        asyncio.create_task(self.handle_learning_countdown(user_id, room_name))
        
        room_display = {
            'room1': 'BLUE ROOM (1.5x-5x Focus)',
            'room2': 'RED ROOM (5x-20x Focus)',
            'room3': 'GREEN ROOM (20x-1000x+ Focus)'
        }.get(room_name, room_name)
        
        await query.edit_message_text(
            f"✅ *Room Selected*\n\n"
            f"You are now monitoring:\n"
            f"**{room_display}**\n\n"
            f"📚 *Learning Phase Started*\n"
            f"Analyzing room patterns for {self.learning_duration//60} minutes...\n"
            f"• Collecting data for accurate predictions\n"
            f"• Adjusting to current volatility\n"
            f"• First alerts coming soon!\n\n"
            f"⏳ Please wait for the learning to complete.",
            parse_mode='Markdown'
        )
        
        # Start monitoring if not already running
        if not self.scraping:
            self.scraping = True
            asyncio.create_task(self.run_continuous_monitoring())
    
    async def select_all_rooms(self, user_id, query):
        # Remove from all rooms first
        for room in ['room1', 'room2', 'room3']:
            if user_id in self.room_data[room]['users']:
                self.room_data[room]['users'].remove(user_id)
            if user_id in self.room_data[room]['learning_users']:
                self.room_data[room]['learning_users'].remove(user_id)
        
        # Add to all rooms with learning phase
        self.user_preferences[user_id] = {'room': 'all'}
        
        for room_name in ['room1', 'room2', 'room3']:
            self.room_data[room_name]['users'].add(user_id)
            self.room_data[room_name]['learning_users'].add(user_id)
            self.room_data[room_name]['active'] = True
            
            # Set learning start time for each room
            learning_key = (user_id, room_name)
            self.learning_start_times[learning_key] = time.time()
            
            # Start learning countdown for each room
            asyncio.create_task(self.handle_learning_countdown(user_id, room_name))
        
        await query.edit_message_text(
            "✅ *All Rooms Selected*\n\n"
            "You are now monitoring:\n"
            "**ALL 3 ROOMS**\n\n"
            f"📚 *Learning Phase Started*\n"
            f"Analyzing all rooms for {self.learning_duration//60} minutes...\n"
            f"• Room 1: Low risk patterns\n"
            f"• Room 2: Medium risk patterns\n"
            f"• Room 3: High risk patterns\n\n"
            f"⏳ Please wait for learning to complete in each room.",
            parse_mode='Markdown'
        )
        
        if not self.scraping:
            self.scraping = True
            asyncio.create_task(self.run_continuous_monitoring())
    
    async def handle_learning_countdown(self, user_id, room_name):
        """Handle the learning period countdown for a user-room combination"""
        learning_key = (user_id, room_name)
        
        # Send learning updates every minute
        for minute in range(1, (self.learning_duration // 60) + 1):
            await asyncio.sleep(60)  # Wait 1 minute
            
            if learning_key not in self.learning_start_times:
                break  # User left the room
            
            elapsed = time.time() - self.learning_start_times[learning_key]
            remaining = max(0, self.learning_duration - elapsed)
            
            if remaining > 0:
                # Send progress update
                try:
                    room_display = {
                        'room1': 'Room 1', 'room2': 'Room 2', 'room3': 'Room 3'
                    }.get(room_name, room_name)
                    
                    await self.send_telegram_alert(
                        user_id,
                        f"📚 *Learning Progress - {room_display}*\n"
                        f"Analyzing patterns... {minute} minute(s) completed.\n"
                        f"Remaining: {int(remaining//60)}:{int(remaining%60):02d}"
                    )
                except:
                    pass
        
        # Learning complete - remove from learning_users
        if user_id in self.room_data[room_name]['learning_users']:
            self.room_data[room_name]['learning_users'].remove(user_id)
        
        # Send completion message
        try:
            await self.send_telegram_alert(
                user_id,
                f"✅ *Learning Complete - {room_name.upper()}*\n\n"
                f"Analysis phase finished! Now sending real predictions for:\n"
                f"1.5x, 2x, 3x, 4x, 5x, 10x, 20x, 30x, 40x, 50x, 60x, 70x, 80x, 90x, 100x, 1000x+"
            )
        except:
            pass
    
    async def run_continuous_monitoring(self):
        """Main monitoring loop"""
        while self.scraping:
            try:
                # Process each room
                for room_name in ['room1', 'room2', 'room3']:
                    if self.room_data[room_name]['active'] and self.room_data[room_name]['users']:
                        # Get prediction for this room
                        prediction = self.analyzer.get_prediction(room_name)
                        
                        if prediction:
                            # Process each user in this room
                            for user_id in list(self.room_data[room_name]['users']):
                                # Skip if user is still in learning phase
                                if user_id in self.room_data[room_name]['learning_users']:
                                    continue
                                
                                # Generate alerts for this user
                                alerts = self.get_alerts(prediction, room_name, user_id)
                                
                                # Send alerts
                                for alert in alerts:
                                    try:
                                        await self.send_telegram_alert(user_id, alert)
                                    except Exception as e:
                                        logger.error(f"Send error to {user_id}: {e}")
                
                # Wait before next cycle
                await asyncio.sleep(20)  # Check every 20 seconds
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(10)
    
    def get_alerts(self, prediction, room_name, user_id):
        """Generate alerts based on predictions"""
        alerts = []
        
        room_display = {
            'room1': '🎮 BLUE ROOM',
            'room2': '🎮 RED ROOM', 
            'room3': '🎮 GREEN ROOM'
        }.get(room_name, room_name)
        
        # Check all multiplier targets
        urgent_alerts = []
        high_alerts = []
        medium_alerts = []
        
        targets = [1.5, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 1000]
        
        for target in targets:
            prob_key = f'prob_{target}x'
            if prob_key in prediction:
                prob = prediction[prob_key]
                
                # 5x gets special attention
                if target == 5 and prob > 0.7:
                    urgent_alerts.append(f"5x ⚠️ ({prob*100:.0f}%)")
                
                # High value targets
                elif target >= 20 and prob > 0.4:
                    high_alerts.append(f"{target}x ({prob*100:.0f}%)")
                
                # Medium targets
                elif target >= 10 and prob > 0.5:
                    medium_alerts.append(f"{target}x ({prob*100:.0f}%)")
                
                # Low targets (safe plays)
                elif target < 10 and prob > 0.6:
                    medium_alerts.append(f"{target}x ({prob*100:.0f}%)")
        
        # Create alert messages
        if urgent_alerts:
            alerts.append(
                f"🚨 *URGENT 5x ALERT*\n"
                f"{room_display}\n\n"
                f"🎯 High Probability for 5x Multiplier!\n"
                f"Confidence: {prediction['confidence']*100:.0f}%\n"
                f"Trend: {prediction['trend']}\n\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}"
            )
        
        if high_alerts:
            alerts.append(
                f"🎯 *HIGH VALUE ALERT*\n"
                f"{room_display}\n\n"
                f"📈 Detected Potential for:\n"
                f"   • {' | '.join(high_alerts[:5])}\n\n"
                f"⚡ Confidence: {prediction['confidence']*100:.0f}%\n"
                f"📊 Trend: {prediction['trend']}\n\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}"
            )
        
        if medium_alerts and len(alerts) < 2:
            alerts.append(
                f"📈 *SAFE PLAY ALERT*\n"
                f"{room_display}\n\n"
                f"🎯 Good chance for:\n"
                f"   • {' | '.join(medium_alerts[:5])}\n\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}"
            )
        
        return alerts
    
    async def send_telegram_alert(self, chat_id, message):
        """Send message via Telegram API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                async with session.post(url, json=data) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return None
    
    async def send_status_update(self, user_id, query):
        """Send current status to user"""
        status_lines = []
        
        for room_name in ['room1', 'room2', 'room3']:
            if user_id in self.room_data[room_name]['users']:
                status = "✅ ACTIVE"
                if user_id in self.room_data[room_name]['learning_users']:
                    status = "📚 LEARNING"
                
                users_count = len(self.room_data[room_name]['users'])
                status_lines.append(f"• {room_name.upper()}: {status} ({users_count} users)")
        
        if not status_lines:
            status_text = "Not monitoring any rooms. Use /start to begin."
        else:
            status_text = "\n".join(status_lines)
        
        await query.edit_message_text(
            f"📊 *Your Status*\n\n{status_text}\n\n"
            f"🕐 Last Update: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='Markdown'
        )
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop monitoring for a user"""
        user_id = update.effective_user.id
        
        # Remove from all rooms
        for room in ['room1', 'room2', 'room3']:
            if user_id in self.room_data[room]['users']:
                self.room_data[room]['users'].remove(user_id)
            if user_id in self.room_data[room]['learning_users']:
                self.room_data[room]['learning_users'].remove(user_id)
            
            # Remove learning times
            for key in list(self.learning_start_times.keys()):
                if key[0] == user_id:
                    del self.learning_start_times[key]
        
        # Remove preferences
        if user_id in self.user_preferences:
            del self.user_preferences[user_id]
        
        await update.message.reply_text(
            "🛑 Monitoring stopped.\n\n"
            "You will no longer receive alerts.\n"
            "Use /start to begin monitoring again.",
            parse_mode='Markdown'
        )

def main():
    """Main entry point"""
    system = AviatorMonitorSystem()
    
    # Create application
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", system.start_command))
    app.add_handler(CommandHandler("stop", system.stop_command))
    app.add_handler(CallbackQueryHandler(system.button_handler))
    
    print("🤖 Aviator Bot starting...")
    print(f"📚 Learning duration: {LEARNING_DURATION//60} minutes")
    app.run_polling()

if __name__ == "__main__":
    main()
