import os
import base64
import subprocess
import shutil
import gradio as gr
from PIL import Image
from openai import OpenAI
from io import BytesIO

# ✅ เชื่อมต่อ Ollama (รันใน RunPod เครื่องเดียวกัน)
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

# 📁 ตั้งค่า Folder บน RunPod
output_folder = "/workspace/output_images"
os.makedirs(output_folder, exist_ok=True)

def encode_image_to_base64(image_path):
    with Image.open(image_path) as img:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=80)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

def generate_metadata_from_vision(image_path):
    base64_image = encode_image_to_base64(image_path)
    prompt = """Analyze this image and provide:
    1. A short, descriptive Title (max 10 words).
    2. A detailed Description (1 sentence).
    3. Exactly 49 unique, short keywords separated by commas.
    
    Format your response EXACTLY like this:
    Title: [Your Title]
    Description: [Your Description]
    Keywords: [word1, word2, word3...]"""

    try:
        response = client.chat.completions.create(
            model="gemma3:4b", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ]
        )
        content = response.choices[0].message.content
        title, description, keywords = "Untitled", "No description", []
        
        for line in content.split('\n'):
            if line.startswith("Title:"): title = line.replace("Title:", "").strip()
            if line.startswith("Description:"): description = line.replace("Description:", "").strip()
            if line.startswith("Keywords:"): 
                kw_str = line.replace("Keywords:", "").strip()
                keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
        return title, description, keywords
    except Exception as e:
        return "Error", f"AI Error: {e}", ["error"]

def embed_metadata(image_path, title, description, keywords, temp_out_dir):
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_path = os.path.join(temp_out_dir, f"{base_name}.jpg")

    try:
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output_path, "JPEG", quality=100, subsampling=0)

        keyword_str = ", ".join(keywords)

        subprocess.run([
            "exiftool", "-overwrite_original", "-charset", "filename=utf8",
            f"-Title={title}", f"-Description={description}", f"-Subject={keyword_str}",
            f"-Keywords={keyword_str}", f"-XPTitle={title}", f"-XPKeywords={keyword_str}",
            f"-ImageDescription={description}", output_path
        ], check=True, capture_output=True)
        return output_path
    except Exception as e:
        print(f"ExifTool Error: {e}")
        return None

def process_images(image_files):
    if not image_files:
        return [], "⚠️ ไม่พบไฟล์รูปภาพ กรุณาอัปโหลดใหม่"
    
    # ล้างโฟลเดอร์ output เก่าก่อน
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)

    processed_paths = []
    log_messages = []

    for file_obj in image_files:
        img_path = file_obj.name # Gradio เก็บไฟล์ชั่วคราวไว้
        filename = os.path.basename(img_path)
        log_messages.append(f"🔄 กำลังประมวลผล: {filename}")
        
        # 1. AI วิเคราะห์
        title, desc, kws = generate_metadata_from_vision(img_path)
        log_messages.append(f"✨ หัวข้อ: {title} | คีย์เวิร์ด: {len(kws)} คำ")

        # 2. ฝัง Metadata
        out_path = embed_metadata(img_path, title, desc, kws, output_folder)
        if out_path:
            processed_paths.append(out_path)
            log_messages.append(f"✅ สำเร็จ: {filename}\n---")
        else:
            log_messages.append(f"❌ ล้มเหลว: {filename}\n---")

    return processed_paths, "\n".join(log_messages)

# --- สร้าง Web UI ด้วย Gradio ---
with gr.Blocks(title="Auto Metadata AI", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ AI Auto Metadata Tagger (Gemma 3)")
    gr.Markdown("อัปโหลดรูปภาพเพื่อให้ AI วิเคราะห์และฝัง Metadata อัตโนมัติ พร้อมส่งขาย Stock")
    
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="📂 1. อัปโหลดรูปภาพ (เลือกได้หลายรูป)", file_count="multiple", type="filepath")
            submit_btn = gr.Button("🚀 2. เริ่มประมวลผล", variant="primary")
        
        with gr.Column(scale=1):
            log_output = gr.Textbox(label="📝 สถานะการทำงาน", lines=10, interactive=False)
            
    with gr.Row():
        gallery_output = gr.Gallery(label="✅ รูปที่ประมวลผลเสร็จแล้ว (ดาวน์โหลดได้เลย)", columns=4, height="auto")

    submit_btn.click(
        fn=process_images,
        inputs=file_input,
        outputs=[gallery_output, log_output]
    )

if __name__ == "__main__":
    # เปิด UI บน Port 7860 สำหรับ RunPod
    demo.launch(server_name="0.0.0.0", server_port=7860)
