#!/bin/bash

echo "🚀 Starting Auto-Setup..."

# 1. บังคับให้ Ollama เก็บโมเดลในพื้นที่ถาวร (/workspace) จะได้ไม่โหลดใหม่ทุกครั้ง
export OLLAMA_MODELS="/workspace/ollama_models"

# 2. ติดตั้งเครื่องมือพื้นฐาน
apt-get update && apt-get install -y exiftool curl

# 3. ติดตั้งโปรแกรม Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 4. เปิดระบบ Ollama ทิ้งไว้เบื้องหลัง
ollama serve &
sleep 5 # รอระบบเซ็ตตัว 5 วินาที

# 5. โหลดโมเดล Gemma 3 (ถ้ามีใน /workspace แล้วมันจะข้ามสเต็ปนี้ให้เลย เร็วมาก)
ollama pull gemma3:4b

# 6. ติดตั้ง Library Python (Gradio, etc.)
pip install -r requirements.txt

# 7. เปิดหน้า Web UI
echo "✅ All set! Launching Web UI..."
python app.py
