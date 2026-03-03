import os, subprocess, shutil, re, gradio as gr, ollama
from PIL import Image

# กำหนด Path ให้ชัดเจน
output_folder = "/workspace/output_images"
zip_base_name = "/workspace/processed_images"
zip_filepath = "/workspace/processed_images.zip"

def generate_metadata(image_path, kw_count):
    try:
        prompt = f"Act as a professional stock photographer. Describe this image. Output exactly in this format:\nTitle: [title]\nDescription: [description]\nKeywords: [keyword1, keyword2, ... {kw_count} words]"
        
        # ส่งไปหา AI
        res = ollama.chat(model='llama3.2-vision', messages=[{
            'role': 'user', 'content': prompt, 'images': [image_path]
        }])
        
        txt = res['message']['content'].replace("*", "")
        
        title, desc, keywords = "Untitled", "No Description", []

        # สกัดข้อมูลด้วย Regex
        t_match = re.search(r"(?i)Title:\s*(.*)", txt)
        if t_match: title = t_match.group(1).strip()

        d_match = re.search(r"(?i)Description:\s*(.*)", txt)
        if d_match: desc = d_match.group(1).strip()

        k_match = re.search(r"(?i)Keywords:\s*(.*)", txt)
        if k_match:
            keywords = [k.strip() for k in k_match.group(1).split(",") if len(k.strip()) > 1]
        
        # ป้องกันถ้าหา Keywords ไม่เจอ
        if not keywords:
            keywords = [k.strip() for k in txt.split() if len(k.strip()) > 3][:kw_count]

        return title, desc, keywords[:kw_count], txt
    except Exception as e:
        return "Error", "Error", ["error"], f"AI Crash: {str(e)}"

def embed_metadata(image_path, title, desc, keywords):
    try:
        kw_str = ", ".join(keywords)
        # ฝังทุก Tags (IPTC, XMP, EXIF)
        cmd = [
            "exiftool", "-overwrite_original", "-charset", "UTF8",
            f"-Title={title}", f"-XPTitle={title}", f"-XMP-dc:Title={title}",
            f"-Description={desc}", f"-ImageDescription={desc}", f"-XMP-dc:Description={desc}",
            f"-Keywords={kw_str}", f"-Subject={kw_str}", f"-XMP-dc:Subject={kw_str}",
            f"-IPTC:Keywords={kw_str}", f"-XPKeywords={kw_str}",
            image_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True, "OK"
    except Exception as e:
        return False, str(e)

def process(files, kw_count):
    if not files: yield [], None, "❌ ไม่มีไฟล์ที่อัปโหลด!", [], ""; return
    
    # ล้างโฟลเดอร์เก่าทิ้งและสร้างใหม่
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    if os.path.exists(zip_filepath): os.remove(zip_filepath)
    
    results, logs, meta_list = [], [], []
    processed_count = 0
    
    yield results, None, "🚀 เริ่มกระบวนการ...", meta_list, ""

    for i, f in enumerate(files):
        filename = os.path.basename(f.name)
        logs.append(f"🔄 [{i+1}/{len(files)}] กำลังทำ: {filename}")
        yield results, None, "\n".join(logs[-5:]), meta_list, ""
        
        # 1. ให้ AI วิเคราะห์
        t, d, k, raw_ai = generate_metadata(f.name, kw_count)
        
        if t == "Error":
            logs[-1] = f"❌ AI Error: {filename}"
            meta_list.append(f"ไฟล์ {filename}: AI ไม่ตอบกลับ หรือ Model ยังไม่พร้อม")
        else:
            # 2. บันทึกรูปใหม่ลงโฟลเดอร์ Output
            out_path = os.path.join(output_folder, filename)
            try:
                with Image.open(f.name) as img:
                    img.convert('RGB').save(out_path, "JPEG", quality=100)
                
                # 3. ฝัง Metadata
                success, ex_err = embed_metadata(out_path, t, d, k)
                if success:
                    processed_count += 1
                    logs[-1] = f"✅ สำเร็จ: {filename}"
                    results.append(out_path)
                    meta_list.append(f"📌 {filename}\nTitle: {t}\nKeywords: {', '.join(k)}")
                else:
                    logs[-1] = f"⚠️ ฝัง Metadata ไม่เข้า: {filename}"
                    meta_list.append(f"ไฟล์ {filename}: Metadata Error -> {ex_err}")
            except Exception as img_err:
                logs[-1] = f"❌ บันทึกรูปไม่ได้: {filename}"
                meta_list.append(f"ไฟล์ {filename}: Image Error -> {str(img_err)}")

        yield results, None, "\n".join(logs[-5:]), meta_list, raw_ai

    # 4. ตรวจสอบก่อนทำ ZIP
    if processed_count > 0:
        logs.append(f"📦 กำลังรวมไฟล์ {processed_count} รูปเข้าไฟล์ ZIP...")
        yield results, None, "\n".join(logs[-5:]), meta_list, "Zipping..."
        shutil.make_archive(zip_base_name, 'zip', output_folder)
        yield results, zip_filepath, "🎉 เสร็จเรียบร้อย! โหลดไฟล์ ZIP ได้เลย", meta_list, "Success"
    else:
        yield results, None, "❌ ไม่มีรูปที่ประมวลผลสำเร็จเลย ไฟล์ ZIP จึงไม่ได้สร้าง", meta_list, "Failed"

# --- UI Interface ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ AI Auto Metadata PRO (Batch Edition)")
    state = gr.State([])
    with gr.Row():
        with gr.Column(scale=1):
            inp = gr.File(label="📂 เลือกรูปภาพ (หลายรูปได้)", file_count="multiple")
            sld = gr.Slider(10, 50, 49, step=1, label="จำนวน Keywords")
            btn = gr.Button("🚀 เริ่มประมวลผลทั้งหมด", variant="primary")
            dl = gr.File(label="📦 ดาวน์โหลด ZIP ที่นี่")
            log = gr.Textbox(label="สถานะ", lines=4)
        with gr.Column(scale=2):
            gal = gr.Gallery(label="รูปที่ทำเสร็จแล้ว", columns=3, height="auto")
            info = gr.Textbox(label="ข้อมูล Metadata (คลิกที่รูปใน Gallery)", lines=8)
            raw = gr.Textbox(label="AI Debug (ดูข้อความจาก AI)", lines=5)

    btn.click(process, [inp, sld], [gal, dl, log, state, raw])
    gal.select(lambda e, s: s[e.index] if e.index < len(s) else "ไม่มีข้อมูล", [state], info)

demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
