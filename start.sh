#!/bin/bash

echo "🚀 Starting Auto-Setup..."

# บังคับให้เก็บโมเดล AI ไว้ในพื้นที่ถาวร จะได้ไม่ต้องโหลดใหม่เวลาย้ายเครื่อง
export OLLAMA_MODELS="/workspace/ollama_models"

# เข้าไปที่โฟลเดอร์โปรเจกต์
cd /workspace/Auto-Metadata

# 1. ติดตั้งโปรแกรมพื้นฐาน
apt-get update && apt-get install -y exiftool curl

# 2. ติดตั้งตัวจัดการ AI (Ollama)
curl -fsSL https://ollama.com/install.sh | sh

# 3. เปิดระบบ Ollama ทิ้งไว้เบื้องหลัง (ใช้ Full Path กันเหนียว)
/usr/local/bin/ollama serve &
sleep 10 # รอให้ระบบบูทเสร็จสมบูรณ์

# 4. โหลดโมเดลสำหรับวิเคราะห์รูปภาพ
echo "🧠 Pulling Llama 3.2 Vision model..."
/usr/local/bin/ollama pull llama3.2-vision

# 5. ติดตั้งไลบรารีของ Python
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# 6. รันโปรแกรมหลัก
echo "✅ All set! Launching Web UI..."
python app.py
