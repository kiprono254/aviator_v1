import asyncio
import signal
import sys
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from analyzer import AviatorAnalyzer
import aiohttp
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8368454491:AAHt21WGsWVRhNmQ9z5MYfWPcsHWATn4qQ4"

class AviatorMonitorSystem:
    def __init__(self):
        self.analyzer = AviatorAnalyzer()
        self.user_preferences = {}
        self.scraping = False
        self.room_data = {
            'room1': {'active': False, 'users': set(), 'history': []},
            'room2': {'active': False, 'users': set(), 'history': []},
            'room3': {'active': False, 'users': set(), 'history': []}
        }
        self.targets = [1.5, 2, 3, 4, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 1000]
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        keyboard = [
            [InlineKeyboardButton("🎮 Room 1", callback_data='room_1')],
            [InlineKeyboardButton("🎮 Room 2", callback_data='room_2')],
            [InlineKeyboardButton("🎮 Room 3", callback_data='room_3')],
            [InlineKeyboardButton("📊 All Rooms", callback_data='room_all')],
            [InlineKeyboardButton("⚙️ Settings", callback_data='settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 *Aviator Analysis*\n\n"
            "Select which room to monitor:\n"
            "• Room 1: Low Risk (1.5x-5x)\n"
            "• Room 2: Medium Risk (5x-20x)\n"
            "• Room 3: High Risk (20x-1000x+)\n\n"
            "I will alert you for multipliers:\n"
            "1.5x, 2x, 3x, 4x, 5x, 10x, 20x, 30x, 40x, 50x, 60x, 70x, 80x, 90x, 100x, 1000x+",
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
        elif query.data == 'settings':
            await self.show_settings(user_id, query)
    
    async def select_room(self, user_id, room_name, query):
        self.user_preferences[user_id] = {'room': room_name}
        self.room_data[room_name]['users'].add(user_id)
        self.room_data[room_name]['active'] = True
        
        room_descriptions = {
            'room1': 'LOW RISK (1.5x-5x focus)',
            'room2': 'MEDIUM RISK (5x-20x focus)', 
            'room3': 'HIGH RISK (20x-1000x+ focus)'
        }
        
        await query.edit_message_text(
            f"✅ *Room Selected*\n\n"
            f"You are now monitoring:\n"
            f"**{room_name.upper()} - {room_descriptions[room_name]}**\n\n"
            f"I will alert you when this room shows potential for:\n"
            f"1.5x, 2x, 3x, 4x, 5x, 10x, 20x, 30x, 40x, 50x, 60x, 70x, 80x, 90x, 100x, 1000x+\n\n"
            f"Starting real-time analysis now...",
            parse_mode='Markdown'
        )
        
        if not self.scraping:
            self.scraping = True
            asyncio.create_task(self.run_continuous_monitoring())
    
    async def select_all_rooms(self, user_id, query):
        self.user_preferences[user_id] = {'room': 'all'}
        for room in ['room1', 'room2', 'room3']:
            self.room_data[room]['users'].add(user_id)
            self.room_data[room]['active'] = True
        
        await query.edit_message_text(
            "✅ *All Rooms Selected*\n\n"
            "You are now monitoring:\n"
            "**ALL ROOMS - Complete Coverage**\n\n"
            "I will alert you when any room shows potential for:\n"
            "1.5x, 2x, 3x, 4x, 5x, 10x, 20x, 30x, 40x, 50x, 60x, 70x, 80x, 90x, 100x, 1000x+\n\n"
            "Starting real-time analysis now...",
            parse_mode='Markdown'
        )
        
        if not self.scraping:
            self.scraping = True
            asyncio.create_task(self.run_continuous_monitoring())
    
    async def show_settings(self, user_id, query):
        keyboard = [
            [InlineKeyboardButton("🔔 Alert Thresholds", callback_data='thresholds')],
            [InlineKeyboardButton("🎯 Target Multipliers", callback_data='targets')],
            [InlineKeyboardButton("📊 Room Priority", callback_data='priority')],
            [InlineKeyboardButton("⬅️ Back", callback_data='back_to_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ *Settings*\n\n"
            "Configure your monitoring preferences:\n\n"
            "• Alert Thresholds: Set confidence levels\n"
            "• Target Multipliers: Choose which multipliers to track\n"
            "• Room Priority: Set which rooms get priority alerts",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def run_continuous_monitoring(self):
        while self.scraping:
            try:
                for room_name in ['room1', 'room2', 'room3']:
                    if self.room_data[room_name]['active']:
                        prediction = self.analyzer.get_prediction(room_name)
                        
                        if prediction and self.room_data[room_name]['users']:
                            alerts = self.get_alerts(prediction, room_name)
                            
                            for alert in alerts:
                                for user_id in self.room_data[room_name]['users']:
                                    try:
                                        await self.send_telegram_alert(user_id, alert)
                                    except Exception as e:
                                        logger.error(f"Failed to send to {user_id}: {e}")
                
                await asyncio.sleep(20)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(10)
    
    def get_alerts(self, prediction, room_name):
        alerts = []
        
        room_display = {
            'room1': '🎮 BLUE ROOM (Low Risk)',
            'room2': '🎮 RED ROOM (Medium Risk)',
            'room3': '🎮 GREEN ROOM (High Risk)'
        }.get(room_name, room_name)
        
        urgent_targets = []
        high_targets = []
        medium_targets = []
        
        for target in self.targets:
            prob = prediction.get(f'prob_{target}x', 0)
            
            if target == 5 and prob > 0.7:
                urgent_targets.append(f"5x ⚠️ ({prob*100:.0f}%)")
            elif target < 5 and prob > 0.8:
                medium_targets.append(f"{target}x ({prob*100:.0f}%)")
            elif target > 5 and target <= 20 and prob > 0.6:
                high_targets.append(f"{target}x ({prob*100:.0f}%)")
            elif target > 20 and prob > 0.4:
                high_targets.append(f"{target}x ({prob*100:.0f}%)")
        
        if urgent_targets:
            alert_msg = (
                f"🚨 *URGENT 5x ALERT*\n"
                f"{room_display}\n\n"
                f"🎯 High Probability for 5x Multiplier!\n"
                f"Confidence: {prediction['confidence']*100:.0f}%\n"
                f"Trend: {prediction['trend']}\n\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}"
            )
            alerts.append(alert_msg)
        
        if high_targets:
            high_alert = (
                f"🎯 *HIGH VALUE ALERT*\n"
                f"{room_display}\n\n"
                f"📈 Detected Potential for:\n"
                f"   • {' | '.join(high_targets)}\n\n"
                f"⚡ Confidence: {prediction['confidence']*100:.0f}%\n"
                f"📊 Trend: {prediction['trend']}\n"
                f"🔥 Recent High: {prediction['recent_high']:.2f}x\n\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}"
            )
            alerts.append(high_alert)
        
        if medium_targets and len(alerts) < 2:
            medium_alert = (
                f"📈 *SAFE PLAY ALERT*\n"
                f"{room_display}\n\n"
                f"🎯 Good chance for low multipliers:\n"
                f"   • {' | '.join(medium_targets)}\n\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}"
            )
            alerts.append(medium_alert)
        
        return alerts
    
    async def send_telegram_alert(self, chat_id, message):
        if not message:
            return
            
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            async with session.post(url, json=data) as response:
                return await response.json()
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_pref = self.user_preferences.get(user_id, {})
        
        status_msg = "📊 *Your Monitoring Status*\n\n"
        
        if user_pref.get('room') == 'all':
            status_msg += "Monitoring: **ALL 3 ROOMS**\n\n"
            for room in ['room1', 'room2', 'room3']:
                users_count = len(self.room_data[room]['users'])
                status_msg += f"• {room.upper()}: {users_count} users\n"
        elif user_pref.get('room'):
            room = user_pref['room']
            users_count = len(self.room_data[room]['users'])
            status_msg += f"Monitoring: **{room.upper()}**\n"
            status_msg += f"Active in room: {users_count} users\n"
        else:
            status_msg += "Not monitoring any room yet.\nUse /start to begin."
        
        status_msg += f"\n🎯 Tracking: 1.5x, 2x, 3x, 4x, 5x, 10x, 20x, 30x, 40x, 50x, 60x, 70x, 80x, 90x, 100x, 1000x+"
        status_msg += f"\n🕐 Last Update: {datetime.now().strftime('%H:%M:%S')}"
        
        await update.message.reply_text(status_msg, parse_mode='Markdown')
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id in self.user_preferences:
            room_pref = self.user_preferences[user_id].get('room')
            
            if room_pref == 'all':
                for room in ['room1', 'room2', 'room3']:
                    if user_id in self.room_data[room]['users']:
                        self.room_data[room]['users'].remove(user_id)
            elif room_pref:
                if user_id in self.room_data[room_pref]['users']:
                    self.room_data[room_pref]['users'].remove(user_id)
            
            del self.user_preferences[user_id]
            
            await update.message.reply_text(
                "🛑 Monitoring stopped.\n\n"
                "You will no longer receive alerts.\n"
                "Use /start to begin monitoring again.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "You are not currently monitoring any room.\n"
                "Use /start to begin.",
                parse_mode='Markdown'
            )
    
    async def targets_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        targets_list = "1.5x, 2x, 3x, 4x, 5x, 10x, 20x, 30x, 40x, 50x, 60x, 70x, 80x, 90x, 100x, 1000x+"
        await update.message.reply_text(
            f"🎯 *Target Multipliers*\n\n"
            f"Currently tracking:\n"
            f"{targets_list}\n\n"
            f"Special focus on **5x** for safe plays.",
            parse_mode='Markdown'
        )

def main():
    system = AviatorMonitorSystem()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", system.start_command))
    app.add_handler(CommandHandler("status", system.status_command))
    app.add_handler(CommandHandler("stop", system.stop_command))
    app.add_handler(CommandHandler("targets", system.targets_command))
    app.add_handler(CallbackQueryHandler(system.button_handler))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
