#!/bin/bash
echo "🚀 [1/4] Install Tools..."
apt-get update && apt-get install -y exiftool curl pciutils

echo "🚀 [2/4] Install Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

echo "🚀 [3/4] Pulling Model (2.5GB - Please Wait...)"
# รัน Ollama ใน background
ollama serve > /workspace/ollama.log 2>&1 &
sleep 10
# ดึงโมเดลให้เสร็จก่อนไปขั้นตอนถัดไป
ollama pull llama3.2-vision

echo "🚀 [4/4] Finalizing..."
pip install ollama Pillow gradio
echo "✅ Everything is ready! Launching UI..."
python app.py
