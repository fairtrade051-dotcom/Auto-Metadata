#!/bin/bash
echo "🚀 [1/5] อัปเดตระบบ..."
apt-get update && apt-get install -y psmisc curl exiftool pciutils

echo "🧹 [2/5] เคลียร์พอร์ตค้าง..."
fuser -k 11434/tcp || true
pkill -9 ollama || true

echo "🦙 [3/5] โหลด Ollama จาก GitHub (ชัวร์กว่าเดิม)..."
# ใช้ Link ตรงจาก GitHub Release เพื่อป้องกันการได้ไฟล์ 9 byte
curl -L https://github.com/ollama/ollama/releases/download/v0.5.7/ollama-linux-amd64 -o /usr/local/bin/ollama
chmod +x /usr/local/bin/ollama

echo "▶️ [4/5] สั่ง Ollama Start..."
export OLLAMA_HOST="0.0.0.0"
export OLLAMA_MODELS="/workspace/ollama_models"
mkdir -p $OLLAMA_MODELS
nohup /usr/local/bin/ollama serve > /workspace/ollama.log 2>&1 &

echo "⏳ [5/5] รอเช็คสถานะ..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
        echo "✅ Ollama ตื่นแล้ว!"
        break
    fi
    echo "รอ Ollama บูทเครื่อง... ($i)"
    sleep 2
    if [ $i -eq 30 ]; then
        echo "❌ ไม่ยอมตื่น! ดู Log:"
        cat /workspace/ollama.log
        exit 1
    fi
done

echo "🧠 โหลด Model และเริ่มโปรแกรม..."
/usr/local/bin/ollama pull llama3.2-vision
pip install -r requirements.txt
python app.py
