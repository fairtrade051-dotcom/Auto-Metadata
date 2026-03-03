#!/bin/bash
echo "🚀 กำลังติดตั้งระบบ..."
apt-get update && apt-get install -y exiftool curl pciutils

# ใช้การติดตั้งแบบเดิมที่พี่เคยทำได้ (Official Script)
curl -fsSL https://ollama.com/install.sh | sh

# สั่งรัน Ollama
ollama serve > /workspace/ollama.log 2>&1 &
sleep 10

# โหลดโมเดล
ollama pull llama3.2-vision

# ลง Library และรัน
pip install ollama Pillow gradio
python app.py
