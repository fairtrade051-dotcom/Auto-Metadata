#!/bin/bash
echo "🚀 Starting Auto-Setup..."
export OLLAMA_MODELS="/workspace/ollama_models"
cd /workspace/Auto-Metadata

# 1. ติดตั้งเครื่องมือพื้นฐาน
apt-get update && apt-get install -y exiftool curl

# 2. ดาวน์โหลดโปรแกรม Ollama ตรงๆ มาไว้ที่ /usr/bin (บังคับตำแหน่งแน่นอน)
echo "🦙 Downloading Ollama binary..."
curl -L https://ollama.com/download/ollama-linux-amd64 -o /usr/bin/ollama
chmod +x /usr/bin/ollama

# 3. เปิดระบบ Ollama ทิ้งไว้
/usr/bin/ollama serve &

# 4. รอจนกว่าเซิร์ฟเวอร์ Ollama จะรันเสร็จสมบูรณ์ 100%
echo "⏳ Waiting for Ollama to initialize..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 2
done
echo "✅ Ollama is running!"

# 5. โหลดโมเดลสำหรับวิเคราะห์ภาพ
echo "🧠 Pulling Llama 3.2 Vision model..."
/usr/bin/ollama pull llama3.2-vision

# 6. ติดตั้งไลบรารี Python
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# 7. เปิดหน้า Web UI
echo "✅ All set! Launching Web UI..."
python app.py
