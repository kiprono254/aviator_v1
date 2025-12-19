#!/bin/bash

echo "🚀 Setting up Aviator Bot with Learning Feature..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install requirements
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create data files
echo "📁 Creating data files..."
for room in room1 room2 room3; do
    if [ ! -f "${room}_data.json" ]; then
        echo "[]" > "${room}_data.json"
        echo "Created ${room}_data.json"
    fi
done

# Set permissions
chmod +x main.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the bot:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run the bot: python main.py"
echo ""
echo "Features:"
echo "• 3-minute learning period for all rooms"
echo "• Room-specific analysis"
echo "• Real-time alerts for 1.5x to 1000x+"
echo "• User-specific learning tracking"
