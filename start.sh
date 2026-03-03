#!/bin/bash
echo "🚀 Starting Auto-Setup..."
export OLLAMA_MODELS="/workspace/ollama_models"
cd /workspace/Auto-Metadata

# 1. Update system and install dependencies
apt-get update && apt-get install -y exiftool curl pciutils

# 2. Install Ollama using the official script
echo "🦙 Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# 3. Start the Ollama service in the background
echo "▶️ Starting Ollama service..."
ollama serve &

# 4. Wait for Ollama to become fully responsive
echo "⏳ Waiting for Ollama to initialize..."
until curl -s http://localhost:11434/api/tags > /dev/null; do
    echo "Waiting for Ollama..."
    sleep 2
done
echo "✅ Ollama is running!"

# 5. Pull the Vision Model
echo "🧠 Pulling Llama 3.2 Vision model (this may take a moment)..."
ollama pull llama3.2-vision

# 6. Install Python packages
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# 7. Launch the UI
echo "✅ All set! Launching Web UI..."
python app.py
