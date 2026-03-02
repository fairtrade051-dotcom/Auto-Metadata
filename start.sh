#!/bin/bash

echo "🚀 Starting Auto-Setup..."

# บังคับให้เข้ามาในโฟลเดอร์โปรเจกต์ชัวร์ๆ จะได้หาไฟล์ requirements.txt เจอ
cd /workspace/Auto-Metadata

# 1. ติดตั้งเครื่องมือ
apt-get update && apt-get install -y exiftool curl

# 2. ติดตั้งโปรแกรม Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 3. เปิดระบบ Ollama (ใช้ Full Path เพื่อแก้ปัญหา command not found)
/usr/local/bin/ollama serve &
sleep 10 # รอระบบเซ็ตตัว 10 วินาทีให้ชัวร์

# 4. โหลดโมเดล Gemma 3
/usr/local/bin/ollama pull gemma3:4b

# 5. ติดตั้ง Library Python (ตอนนี้ระบบจะหา requirements.txt เจอแล้ว)
pip install -r requirements.txt

# 6. เปิดหน้า Web UI
echo "✅ All set! Launching Web UI..."
python app.py
