#!/bin/bash
echo "🚀 เริ่มต้นระบบ Auto-Setup..."

# บังคับใช้ GPU (ถ้ามี) และเก็บโมเดลไว้ที่พื้นที่ถาวร
export OLLAMA_MODELS="/workspace/ollama_models"
mkdir -p $OLLAMA_MODELS
cd /workspace/Auto-Metadata

# 1. ติดตั้ง Tools ที่จำเป็น
apt-get update && apt-get install -y exiftool curl pciutils lsof

# 2. ติดตั้ง Ollama (วิธีมาตรฐาน)
echo "🦙 กำลังติดตั้ง Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# 3. เคลียร์ Process เก่าที่ค้างอยู่ (ถ้ามี)
echo "🧹 เคลียร์ Port 11434..."
fuser -k 11434/tcp || true
pkill -9 ollama || true
sleep 2

# 4. สั่งรัน Ollama แบบ Hardcore (บังคับ Host และเก็บ Log)
echo "▶️ สั่ง Ollama รันเบื้องหลัง..."
export OLLAMA_HOST="0.0.0.0"
nohup ollama serve > /workspace/ollama.log 2>&1 &

# 5. รอให้ Ollama ตื่น (จำกัดเวลา 60 วินาที ถ้าไม่ตื่นให้ด่าระบบ)
echo "⏳ รอ Ollama เตรียมความพร้อม..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
        echo "✅ Ollama พร้อมใช้งานแล้ว!"
        break
    fi
    echo "พยายามติดต่อ Ollama ครั้งที่ $i..."
    sleep 2
    if [ $i -eq 30 ]; then
        echo "❌ ERROR: Ollama แม่งไม่ยอมทำงาน! ดู Log ด้านล่างนี้:"
        cat /workspace/ollama.log
        exit 1
    fi
done

# 6. โหลดโมเดล
echo "🧠 กำลังโหลดโมเดล Llama 3.2 Vision (ห้ามปิดเครื่อง)..."
ollama pull llama3.2-vision

# 7. ลง Python Packages
echo "📦 ติดตั้ง Python libraries..."
pip install -r requirements.txt

# 8. รันหน้าเว็บ UI
echo "✅ ทุกอย่างพร้อม! กำลังเปิดหน้าเว็บ..."
python app.py
