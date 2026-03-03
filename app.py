import os
import base64
import subprocess
import shutil
import gradio as gr
from PIL import Image
from openai import OpenAI
from io import BytesIO

# ✅ เชื่อมต่อ Ollama (ใช้โมเดลที่รันในเครื่องเดียวกัน)
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

# 📁 ตั้งค่า Folder บน RunPod
output_folder = "/workspace/output_images"
zip_filepath = "/workspace/processed_images.zip"

def encode_image_to_base64(image_path):
    with Image.open(image_path) as img:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=80)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

def generate_metadata_from_vision(image_path, keyword_count):
    base64_image = encode_image_to_base64(image_path)
    
    # คำสั่งให้ AI ทำงาน
    prompt = f"""Analyze this image and provide:
    1. A short, descriptive Title (max 10 words).
    2. A detailed Description (1 sentence).
    3. Exactly {keyword_count} unique, short keywords separated by commas.
    
    Format your response EXACTLY like this:
    Title: [Your Title]
    Description: [Your Description]
    Keywords: [word1, word2, word3...]"""

    try:
        # เปลี่ยนมาใช้ llama3.2-vision ซึ่งเก่งเรื่องดูรูปภาพ
        response = client.chat.completions.create(
            model="llama3.2-vision", 
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
        
        # แยกข้อมูลที่ AI ตอบกลับมา
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

        # ใช้ ExifTool ฝังข้อมูลลงไฟล์ภาพ
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

def process_images(image_files, keyword_count):
    if not image_files:
        return [], None, "⚠️ ไม่พบไฟล์รูปภาพ", []
    
    # ล้างไฟล์เก่าออกก่อนเริ่มงานใหม่
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    if os.path.exists(zip_filepath):
        os.remove(zip_filepath)

    processed_paths = []
    log_messages = []
    metadata_info_list = [] 

    for file_obj in image_files:
        img_path = file_obj.name
        filename = os.path.basename(img_path)
        log_messages.append(f"🔄 กำลังประมวลผล: {filename}")
        
        # เรียก AI วิเคราะห์
        title, desc, kws = generate_metadata_from_vision(img_path, keyword_count)
        
        # เก็บข้อมูลไว้แสดงตอนผู้ใช้คลิกดูรูป
        info_text = f"📌 ไฟล์: {filename}\n🏷️ หัวข้อ: {title}\n📝 คำอธิบาย: {desc}\n🔑 คีย์เวิร์ด ({len(kws)} คำ):\n{', '.join(kws)}"
        metadata_info_list.append(info_text)

        # ฝัง Metadata ลงภาพ
        out_path = embed_metadata(img_path, title, desc, kws, output_folder)
        if out_path:
            processed_paths.append(out_path)
            log_messages.append(f"✅ สำเร็จ: {filename} (ได้คีย์เวิร์ด {len(kws)} คำ)\n---")
        else:
            log_messages.append(f"❌ ล้มเหลว: {filename}\n---")

    # บีบอัดไฟล์เป็น ZIP
    shutil.make_archive(zip_filepath.replace('.zip', ''), 'zip', output_folder)

    return processed_paths, zip_filepath, "\n".join(log_messages), metadata_info_list

def show_metadata(evt: gr.SelectData, metadata_list):
    if metadata_list and evt.index < len(metadata_list):
        return metadata_list[evt.index]
    return "ไม่มีข้อมูล"

# --- สร้างหน้าตาเว็บ (Web UI) ด้วย Gradio ---
with gr.Blocks(title="Auto Metadata AI", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ AI Auto Metadata Tagger 🚀")
    
    metadata_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="📂 1. อัปโหลดรูปภาพ (เลือกได้หลายรูป)", file_count="multiple", type="filepath")
            keyword_slider = gr.Slider(minimum=10, maximum=50, value=49, step=1, label="🎛️ 2. กำหนดจำนวนคีย์เวิร์ดที่ต้องการ")
            submit_btn = gr.Button("🚀 3. เริ่มประมวลผล", variant="primary")
            
            gr.Markdown("---")
            download_zip = gr.File(label="📦 โหลดไฟล์ทั้งหมดเป็น ZIP (เมื่อเสร็จสิ้น)", interactive=False)
            log_output = gr.Textbox(label="📝 สถานะการทำงาน", lines=6, interactive=False)
        
        with gr.Column(scale=2):
            gr.Markdown("### 🖼️ ผลลัพธ์ (คลิกที่รูปเพื่อดูข้อมูล Metadata)")
            gallery_output = gr.Gallery(label="รูปภาพที่ฝัง Metadata แล้ว", columns=3, height="auto")
            selected_info = gr.Textbox(label="🔍 ข้อมูล Metadata ของรูปที่เลือก", lines=6, interactive=False)

    # เชื่อมโยงปุ่มกับการทำงาน
    submit_btn.click(
        fn=process_images,
        inputs=[file_input, keyword_slider],
        outputs=[gallery_output, download_zip, log_output, metadata_state]
    )

    gallery_output.select(
        fn=show_metadata,
        inputs=[metadata_state],
        outputs=[selected_info]
    )

if __name__ == "__main__":
    # เปิด Port 7860 และอนุญาตให้เข้าถึงโฟลเดอร์ /workspace เพื่อแก้ปัญหา InvalidPathError
    demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
