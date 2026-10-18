#!/bin/bash
# ==========================================================
# BloodConnect - Quick Launch Script for Viva / Local Demo
# ==========================================================

echo "======================================================="
echo "   BloodConnect: Online Blood Donor Finder System     "
echo "======================================================="

# Navigate to project directory
cd "$(dirname "$0")"

# Ensure virtual environment exists and is activated
if [ ! -d "venv" ]; then
    echo "First time setup: Initializing Python virtual environment..."
    python3 -m venv venv
    venv/bin/pip install --quiet -r requirements.txt
fi
source venv/bin/activate

# Ensure database is initialized if missing
if [ ! -f "bloodconnect.db" ]; then
    echo "First time setup: Initializing clean database for real-time registrations..."
    python seed_data.py
fi

echo ""
echo "🚀 Starting BloodConnect web server on http://127.0.0.1:5050 ..."
echo "👉 Open http://127.0.0.1:5050 in your browser to view the app."
echo ""
echo "Default Administrator Credentials:"
echo "-------------------------------------------------------"
echo "Role        | Email                      | Password    "
echo "-------------------------------------------------------"
echo "Admin       | admin@bloodconnect.org     | admin123    "
echo "-------------------------------------------------------"
echo "Live Registered Data:"
echo "• Donors and Requesters register live in real-time."
echo "• Use the 'Register' page to create new accounts."
echo "• Admin dashboard allows verifying newly registered donors."
echo ""

python app.py
