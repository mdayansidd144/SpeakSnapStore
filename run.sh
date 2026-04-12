#!/bin/bash
echo "🎯 Starting Show & Tell AI..."

# Start backend
cd backend
python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "✅ Backend: http://localhost:8000"
echo "✅ Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both"

wait $BACKEND_PID $FRONTEND_PID