#!/bin/bash
# Quick start script for LDS MVP

set -e

echo "🚀 Starting Arvis LDS MVP (Local Development)"
echo "=============================================="

# Check Docker
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Install from https://docs.docker.com/compose/install/"
    exit 1
fi

# Check environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.development..."
    cp .env.development .env
    echo "✅ .env created (edit for customization)"
fi

# Start services
echo ""
echo "🐳 Starting Docker containers (PostgreSQL, Redis, API)..."
docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 10

# Initialize database
echo "📊 Initializing database schema..."
docker-compose exec -T api python -m alembic upgrade head 2>/dev/null || echo "⚠️ Schema may already exist"

# Run health check
echo ""
echo "🔍 Running health check..."
HEALTH=$(curl -s http://localhost:8000/health || echo '{"status":"unhealthy"}')
STATUS=$(echo $HEALTH | grep -o '"status":"[^"]*' | cut -d'"' -f4)

if [ "$STATUS" = "healthy" ]; then
    echo "✅ API is HEALTHY"
else
    echo "⚠️ API status: $STATUS (may be initializing)"
fi

# Display endpoints
echo ""
echo "📡 API is running at http://localhost:8000"
echo ""
echo "📚 Quick Start Commands:"
echo ""
echo "1️⃣  Register as Consumer:"
echo '   curl -X POST http://localhost:8000/auth/register \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '"'"'{"email":"user@example.com","password":"pass","role":"consumer"}'"'"
echo ""
echo "2️⃣  View Logs:"
echo "   docker-compose logs -f api"
echo ""
echo "3️⃣  Stop Services:"
echo "   docker-compose down"
echo ""
echo "4️⃣  Access Database:"
echo "   docker-compose exec postgres psql -U arvis_lds -d arvis_lds"
echo ""
echo "📖 Full docs: ./lds/README.md"
echo ""
echo "✅ LDS MVP is ready! 🎉"
