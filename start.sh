#!/bin/bash
echo "🚀 [1/2] ติดตั้ง ExifTool..."
apt-get update && apt-get install -y exiftool

echo "🚀 [2/2] ติดตั้ง Python Libraries..."
pip install -r requirements.txt

echo "✅ พร้อมรันโปรแกรม!"
python app.py
