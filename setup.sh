#!/bin/bash
echo "🚀 Setting up Show & Tell AI..."

# Backend setup
echo "📦 Installing Python dependencies..."
cd backend
pip install -r requirements.txt

# Frontend setup
echo "📦 Installing Node dependencies..."
cd ../frontend
npm install

echo "✅ Setup complete! Run './run.sh' to start"