import os
import base64
import subprocess
import shutil
import re
import gradio as gr
from PIL import Image
from openai import OpenAI
from io import BytesIO

# ✅ เชื่อมต่อ Ollama
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
    
    prompt = f"""Analyze this image and provide:
    1. A short, descriptive Title (max 10 words).
    2. A detailed Description (1 sentence).
    3. Exactly {keyword_count} unique, short keywords separated by commas.
    
    Format your response EXACTLY like this:
    Title: [Your Title]
    Description: [Your Description]
    Keywords: [word1, word2, word3...]"""

    try:
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
        
        # 💡 ใช้ Regex เพื่อดึงข้อความให้แม่นยำขึ้น (ป้องกัน AI พิมพ์ติด ** มา)
        title = "Untitled"
        description = "No description"
        keywords = []

        match_title = re.search(r'Title:\s*([^\n]*)', content, re.IGNORECASE)
        if match_title: title = match_title.group(1).replace('*', '').strip()

        match_desc = re.search(r'Description:\s*([^\n]*)', content, re.IGNORECASE)
        if match_desc: description = match_desc.group(1).replace('*', '').strip()

        match_kw = re.search(r'Keywords:\s*(.*)', content, re.IGNORECASE | re.DOTALL)
        if match_kw:
            kw_str = match_kw.group(1).replace('*', '').replace('\n', '').strip()
            # ตัดแบ่งคีย์เวิร์ด และบังคับจำนวนคำตามที่ผู้ใช้เลือก
            keywords = [k.strip() for k in kw_str.split(",") if k.strip()][:keyword_count]

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

def process_images(image_files, keyword_count):
    if not image_files:
        yield [], None, "⚠️ ไม่พบไฟล์รูปภาพ", []
        return
    
    # ล้างไฟล์เก่าออก
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    if os.path.exists(zip_filepath):
        os.remove(zip_filepath)

    processed_paths = []
    log_messages = []
    metadata_info_list = [] 
    total_files = len(image_files)

    # 💡 เปลี่ยนมาใช้ Yield เพื่อส่งรูปและสถานะกลับไปโชว์ที่หน้าเว็บ "ทีละรูป" (แก้ปัญหาเว็บค้างตอนทำ 100 รูป)
    for i, file_obj in enumerate(image_files, 1):
        img_path = file_obj.name
        filename = os.path.basename(img_path)
        
        current_log = f"🔄 กำลังประมวลผล ({i}/{total_files}): {filename}..."
        log_messages.append(current_log)
        # อัปเดต UI ทันทีว่ากำลังทำรูปไหนอยู่ (โชว์ Log แค่ 5 บรรทัดล่าสุดกันรก)
        yield processed_paths, None, "\n".join(log_messages[-5:]), metadata_info_list
        
        # 1. ให้ AI วิเคราะห์
        title, desc, kws = generate_metadata_from_vision(img_path, keyword_count)
        
        # 2. ฝัง Metadata
        out_path = embed_metadata(img_path, title, desc, kws, output_folder)
        
        if out_path:
            # เก็บข้อมูลเฉพาะเมื่อฝังไฟล์สำเร็จ เพื่อให้ Index ของรูปกับข้อมูลตรงกันเป๊ะเวลาคลิก
            processed_paths.append(out_path)
            info_text = f"📌 ไฟล์: {filename}\n🏷️ หัวข้อ: {title}\n📝 คำอธิบาย: {desc}\n🔑 คีย์เวิร์ด ({len(kws)} คำ):\n{', '.join(kws)}"
            metadata_info_list.append(info_text)
            log_messages[-1] = f"✅ สำเร็จ ({i}/{total_files}): {filename} (ได้ {len(kws)} คำ)"
        else:
            log_messages[-1] = f"❌ ล้มเหลว ({i}/{total_files}): {filename}"

        # ส่งรูปที่เสร็จแล้วไปโชว์ใน Gallery ทันที
        yield processed_paths, None, "\n".join(log_messages[-5:]), metadata_info_list

    # เมื่อทำครบทุกรูป ค่อยบีบอัดเป็น ZIP
    log_messages.append("📦 กำลังสร้างไฟล์ ZIP...")
    yield processed_paths, None, "\n".join(log_messages[-5:]), metadata_info_list
    
    shutil.make_archive(zip_filepath.replace('.zip', ''), 'zip', output_folder)
    
    log_messages[-1] = "🎉 ประมวลผลเสร็จสิ้นทั้งหมด! ดาวน์โหลดไฟล์ ZIP ได้เลย"
    yield processed_paths, zip_filepath, "\n".join(log_messages[-5:]), metadata_info_list

def show_metadata(evt: gr.SelectData, metadata_list):
    # ดึงข้อมูลมาแสดงเมื่อผู้ใช้คลิกรูปใน Gallery
    if metadata_list and evt.index < len(metadata_list):
        return metadata_list[evt.index]
    return "⚠️ ไม่พบข้อมูล Metadata สำหรับรูปนี้"

# --- UI (Gradio) ---
with gr.Blocks(title="Auto Metadata AI", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ AI Auto Metadata Tagger (Batch 100+) 🚀")
    
    metadata_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="📂 1. อัปโหลดรูปภาพ (โยนมา 100 รูปได้เลย)", file_count="multiple", type="filepath")
            keyword_slider = gr.Slider(minimum=10, maximum=50, value=49, step=1, label="🎛️ 2. กำหนดจำนวนคีย์เวิร์ดที่ต้องการ")
            submit_btn = gr.Button("🚀 3. เริ่มประมวลผล (กดปุ๊บ รอดูทีละรูปได้เลย)", variant="primary")
            
            gr.Markdown("---")
            download_zip = gr.File(label="📦 โหลดไฟล์ทั้งหมดเป็น ZIP", interactive=False)
            log_output = gr.Textbox(label="📝 สถานะการทำงาน", lines=6, interactive=False)
        
        with gr.Column(scale=2):
            gr.Markdown("### 🖼️ ผลลัพธ์ (คลิกที่รูปเพื่อดูข้อมูล Metadata)")
            gallery_output = gr.Gallery(label="กำลังทยอยอัปเดต...", columns=4, height="auto")
            selected_info = gr.Textbox(label="🔍 ข้อมูล Metadata ของรูปที่เลือก", lines=6, interactive=False)

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
    demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
