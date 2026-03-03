#!/bin/bash
echo "🚀 [1/4] ติดตั้งเครื่องมือ..."
apt-get update && apt-get install -y exiftool curl psmisc

echo "🚀 [2/4] ติดตั้ง Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

echo "🚀 [3/4] เปิดระบบและโหลดโมเดล..."
fuser -k 11434/tcp || true
pkill -9 ollama || true
sleep 2

export OLLAMA_HOST="0.0.0.0"
export OLLAMA_MODELS="/workspace/ollama_models"
mkdir -p $OLLAMA_MODELS
nohup ollama serve > /workspace/ollama.log 2>&1 &

# รอจนกว่า Ollama จะตอบสนอง
while ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; do
    echo "⏳ รอ Ollama บูทเครื่อง (ถ้าค้างตรงนี้นานเกิน 5 นาที ให้เช็คเน็ต RunPod)..."
    sleep 5
done

echo "🧠 กำลังโหลดโมเดล Llama 3.2 Vision (2.5GB)..."
ollama pull llama3.2-vision

echo "🚀 [4/4] เริ่มโปรแกรม..."
pip install -r requirements.txt
python app.py
