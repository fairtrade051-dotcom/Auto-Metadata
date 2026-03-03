#!/bin/bash
echo "🚀 Starting Auto-Setup..."
export OLLAMA_MODELS="/workspace/ollama_models"
mkdir -p $OLLAMA_MODELS
cd /workspace/Auto-Metadata

# 1. Update and install required tools
apt-get update && apt-get install -y exiftool curl pciutils lsof

# 2. Install Ollama (Official script)
echo "🦙 Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# 3. Clean up any stuck Ollama processes that might block the port
echo "🧹 Cleaning up existing processes..."
pkill -9 ollama || true
sleep 2

# 4. Start the Ollama service explicitly on the correct IP
echo "▶️ Starting Ollama service..."
export OLLAMA_HOST="0.0.0.0"
nohup ollama serve > /workspace/ollama_startup.log 2>&1 &
sleep 5 # Give it a few seconds to boot

# 5. Wait for Ollama to become fully responsive (with a timeout mechanism)
echo "⏳ Waiting for Ollama to initialize..."
MAX_RETRIES=30
RETRY_COUNT=0
while ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; do
    echo "Waiting for Ollama (Attempt $((RETRY_COUNT+1))/$MAX_RETRIES)..."
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ ERROR: Ollama failed to start. Check /workspace/ollama_startup.log for details."
        cat /workspace/ollama_startup.log
        exit 1
    fi
done
echo "✅ Ollama is running!"

# 6. Pull the Vision Model
echo "🧠 Pulling Llama 3.2 Vision model (this may take a moment)..."
ollama pull llama3.2-vision

# 7. Install Python packages
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# 8. Launch the UI
echo "✅ All set! Launching Web UI..."
python app.py
