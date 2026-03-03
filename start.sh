#!/bin/bash
echo "🚀 Starting Auto-Setup..."
export OLLAMA_MODELS="/workspace/ollama_models"
cd /workspace/Auto-Metadata

apt-get update && apt-get install -y exiftool curl
curl -fsSL https://ollama.com/install.sh | sh

# เปิดระบบ Ollama ทิ้งไว้
/usr/local/bin/ollama serve &

# รอจนกว่าเซิร์ฟเวอร์ Ollama จะรันเสร็จสมบูรณ์ 100% (กัน Error)
echo "⏳ Waiting for Ollama to initialize..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 2
done
echo "✅ Ollama is running!"

echo "🧠 Pulling Llama 3.2 Vision model..."
/usr/local/bin/ollama pull llama3.2-vision

echo "📦 Installing Python packages..."
pip install -r requirements.txt

echo "✅ All set! Launching Web UI..."
python app.py
