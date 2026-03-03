#!/bin/bash
echo "🚀 [1/5] อัปเดตระบบและลงเครื่องมือจำเป็น..."
# ลง psmisc เพื่อให้มีคำสั่ง fuser และลงตัวจัดการ GPU
apt-get update && apt-get install -y psmisc curl exiftool pciutils

echo "🧹 [2/5] เคลียร์พอร์ตค้าง..."
fuser -k 11434/tcp || true
pkill -9 ollama || true

echo "🦙 [3/5] ติดตั้ง Ollama แบบบังคับ..."
# โหลด binary มาวางเองเลย ไม่ต้องผ่านสคริปต์ติดตั้งที่มันเอ๋อ
curl -L https://ollama.com/download/ollama-linux-amd64 -o /usr/local/bin/ollama
chmod +x /usr/local/bin/ollama

echo "▶️ [4/5] สั่ง Ollama Start..."
export OLLAMA_HOST="0.0.0.0"
export OLLAMA_MODELS="/workspace/ollama_models"
mkdir -p $OLLAMA_MODELS
# รันเบื้องหลังและเก็บ Log ไว้ที่นี่
nohup /usr/local/bin/ollama serve > /workspace/ollama.log 2>&1 &

echo "⏳ [5/5] รอเช็คสถานะ (Max 30s)..."
for i in {1..15}; do
    if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
        echo "✅ Ollama ตื่นแล้ว!"
        break
    fi
    echo "รอ Ollama แป๊บ... ($i)"
    sleep 2
    if [ $i -eq 15 ]; then
        echo "❌ มันไม่ยอมตื่น! ดูสาเหตุข้างล่างนี้:"
        cat /workspace/ollama.log
        exit 1
    fi
done

echo "🧠 โหลด Model และเริ่มโปรแกรม..."
/usr/local/bin/ollama pull llama3.2-vision
pip install -r requirements.txt
python app.py
