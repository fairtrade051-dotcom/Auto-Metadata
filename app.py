import os
import subprocess
import shutil
import re
import gradio as gr
import ollama
from PIL import Image

output_folder = "/workspace/output_images"
zip_filepath = "/workspace/processed_images.zip"

def generate_metadata_from_vision(image_path, keyword_count):
    prompt = f"""Analyze this image and provide:
    1. A short, descriptive Title (max 10 words).
    2. A detailed Description (1 sentence).
    3. Exactly {keyword_count} unique, short keywords separated by commas.
    
    Format your response EXACTLY like this:
    Title: [Your Title]
    Description: [Your Description]
    Keywords: [word1, word2, word3...]"""

    try:
        # ใช้ Ollama Library โดยตรง (เสถียรกว่ามาก ไม่ต้องทำ Base64 เอง)
        response = ollama.chat(
            model='llama3.2-vision',
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_path] # โยนไฟล์รูปให้ Ollama อ่านตรงๆ เลย
            }]
        )
        content = response['message']['content']
        
        # ใช้ Regex เพื่อดึงข้อมูลอย่างชาญฉลาด (เผื่อ AI ตอบมีดอกจันติดมา)
        title, description = "Untitled", "No description"
        keywords = []
        
        t_match = re.search(r'(?i)\*?\*?Title\s*:\*?\*?\s*(.*)', content)
        if t_match: title = t_match.group(1).strip()
            
        d_match = re.search(r'(?i)\*?\*?Description\s*:\*?\*?\s*(.*)', content)
        if d_match: description = d_match.group(1).strip()
            
        k_match = re.search(r'(?i)\*?\*?Keywords\s*:\*?\*?\s*(.*)', content)
        if k_match:
            kw_str = k_match.group(1).strip()
            keywords = [k.strip() for k in kw_str.split(",") if k.strip()]

        # ถ้าเผื่อมันหาไม่เจอเลยจริงๆ ให้เตือนว่า AI เอ๋อ
        if not keywords:
            return "Error Parsing", f"AI Content: {content}", ["error"]

        return title, description, keywords
    except Exception as e:
        return "System Error", f"Error Detail: {str(e)}", ["error"]

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
    
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    if os.path.exists(zip_filepath):
        os.remove(zip_filepath)

    processed_paths = []
    log_messages = ["กำลังเตรียมเริ่มงาน..."]
    metadata_info_list = [] 

    # Yield ครั้งแรกเพื่อล้างหน้าจอให้พร้อม
    yield processed_paths, None, "\n".join(log_messages), metadata_info_list

    for index, file_obj in enumerate(image_files):
        img_path = file_obj.name
        filename = os.path.basename(img_path)
        log_messages.append(f"🔄 [{index+1}/{len(image_files)}] กำลังประมวลผล: {filename}")
        
        # อัปเดต UI ว่ากำลังเริ่มทำรูปนี้
        yield processed_paths, None, "\n".join(log_messages[-10:]), metadata_info_list
        
        title, desc, kws = generate_metadata_from_vision(img_path, keyword_count)
        
        info_text = f"📌 ไฟล์: {filename}\n🏷️ หัวข้อ: {title}\n📝 คำอธิบาย: {desc}\n🔑 คีย์เวิร์ด ({len(kws)} คำ):\n{', '.join(kws)}"
        metadata_info_list.append(info_text)

        out_path = embed_metadata(img_path, title, desc, kws, output_folder)
        if out_path:
            processed_paths.append(out_path)
            log_messages[-1] = f"✅ [{index+1}/{len(image_files)}] สำเร็จ: {filename} ({len(kws)} คีย์เวิร์ด)"
        else:
            log_messages[-1] = f"❌ [{index+1}/{len(image_files)}] ล้มเหลว: {filename}"

        # อัปเดต UI ให้โชว์รูปที่เพิ่งทำเสร็จทันที (ป้องกันเว็บค้างหรือ Timeout)
        yield processed_paths, None, "\n".join(log_messages[-10:]), metadata_info_list

    # เมื่อทำครบทุกรูปแล้ว ค่อยสร้าง ZIP
    log_messages.append("📦 กำลังสร้างไฟล์ ZIP...")
    yield processed_paths, None, "\n".join(log_messages[-10:]), metadata_info_list
    
    shutil.make_archive(zip_filepath.replace('.zip', ''), 'zip', output_folder)
    log_messages.append("🎉 เสร็จสมบูรณ์! ดาวน์โหลดไฟล์ ZIP ได้เลย")
    
    # ส่งไฟล์ ZIP ไปที่หน้า UI ขั้นตอนสุดท้าย
    yield processed_paths, zip_filepath, "\n".join(log_messages[-10:]), metadata_info_list

def show_metadata(evt: gr.SelectData, metadata_list):
    if metadata_list and evt.index < len(metadata_list):
        return metadata_list[evt.index]
    return "⏳ ไม่มีข้อมูล หรือรูปยังประมวลผลไม่เสร็จ"

with gr.Blocks(title="Auto Metadata AI", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ AI Auto Metadata Tagger 🚀 (Real-time Batch)")
    
    metadata_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="📂 1. อัปโหลดรูปภาพ (เลือกได้ 100+ รูป)", file_count="multiple", type="filepath")
            keyword_slider = gr.Slider(minimum=10, maximum=50, value=49, step=1, label="🎛️ 2. กำหนดจำนวนคีย์เวิร์ดที่ต้องการ")
            submit_btn = gr.Button("🚀 3. เริ่มประมวลผล", variant="primary")
            
            gr.Markdown("---")
            download_zip = gr.File(label="📦 โหลดไฟล์ทั้งหมดเป็น ZIP (เมื่อเสร็จสิ้น)", interactive=False)
            log_output = gr.Textbox(label="📝 สถานะการทำงาน", lines=6, interactive=False)
        
        with gr.Column(scale=2):
            gr.Markdown("### 🖼️ ผลลัพธ์ (คลิกที่รูปเพื่อดูข้อมูล Metadata)")
            gallery_output = gr.Gallery(label="รูปภาพที่ฝัง Metadata แล้ว", columns=3, height="auto")
            selected_info = gr.Textbox(label="🔍 ข้อมูล Metadata ของรูปที่เลือก", lines=8, interactive=False)

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
