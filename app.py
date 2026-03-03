import os, subprocess, shutil, re, gradio as gr, ollama
from PIL import Image

# ตั้งค่าตำแหน่งไฟล์
output_folder = "/workspace/output_images"
zip_base_name = "/workspace/processed_images"
zip_filepath = "/workspace/processed_images.zip"

def generate_metadata(image_path, kw_count):
    try:
        # สั่ง AI ให้ทำงานตามฟอร์แมตที่เป๊ะที่สุด
        prompt = f"Stock Photo Metadata. Provide:\nTitle: [short title]\nDescription: [1 sentence]\nKeywords: [list {kw_count} words separated by commas]"
        
        res = ollama.chat(model='llama3.2-vision', messages=[{
            'role': 'user', 'content': prompt, 'images': [image_path]
        }])
        
        txt = res['message']['content'].replace("*", "").replace("#", "")
        
        # ระบบแกะข้อมูลแบบยืดหยุ่น (Regex)
        title = "Untitled"
        desc = "No Description"
        keywords = []

        t_match = re.search(r"(?i)Title\s*:\s*(.*)", txt)
        if t_match: title = t_match.group(1).split('\n')[0].strip()

        d_match = re.search(r"(?i)Description\s*:\s*(.*)", txt)
        if d_match: desc = d_match.group(1).split('\n')[0].strip()

        k_match = re.search(r"(?i)Keywords\s*:\s*(.*)", txt)
        if k_match:
            raw_kws = k_match.group(1).replace("\n", ",").split(",")
            keywords = [k.strip() for k in raw_kws if len(k.strip()) > 1]
        
        # แผนสำรอง: ถ้าหา Keywords ไม่เจอเลย ให้กวาดเอาคำที่มีความยาว > 3 มาทำเป็นคีย์เวิร์ด
        if not keywords:
            keywords = [k.strip() for k in txt.split() if len(k.strip()) > 3][:kw_count]

        return title, desc, keywords[:kw_count], txt
    except Exception as e:
        return "ERROR", str(e), [], f"AI Crash: {str(e)}"

def embed_metadata(image_path, title, desc, keywords):
    try:
        kw_str = ", ".join(keywords)
        # ฝัง Tags ทุกชนิดที่เว็บ Stock และ Windows รองรับ
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
    if not files:
        yield [], None, "❌ ไม่พบไฟล์!", [], ""; return
    
    # ล้างข้อมูลเก่า
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    if os.path.exists(zip_filepath): os.remove(zip_filepath)
    
    results, logs, meta_list = [], [], []
    success_count = 0
    yield results, None, "🚀 เริ่มต้นการประมวลผล...", meta_list, ""

    for i, f in enumerate(files):
        filename = os.path.basename(f.name)
        logs.append(f"🔄 [{i+1}/{len(files)}] {filename}")
        yield results, None, "\n".join(logs[-5:]), meta_list, ""
        
        # 1. AI วิเคราะห์ภาพ
        t, d, k, raw_ai = generate_metadata(f.name, kw_count)
        
        if t == "ERROR":
            logs[-1] = f"❌ AI พัง: {filename}"
            meta_list.append(f"ไฟล์ {filename}: AI ตอบกลับผิดพลาด")
        else:
            # 2. เซฟรูปและฝัง Metadata
            out_path = os.path.join(output_folder, filename)
            try:
                with Image.open(f.name) as img:
                    img.convert('RGB').save(out_path, "JPEG", quality=100)
                
                ok, err = embed_metadata(out_path, t, d, k)
                if ok:
                    success_count += 1
                    results.append(out_path)
                    logs[-1] = f"✅ สำเร็จ: {filename}"
                    meta_list.append(f"📌 {filename}\nTitle: {t}\nKeywords: {', '.join(k)}")
                else:
                    logs[-1] = f"❌ ฝัง Tag พัง: {filename}"
                    meta_list.append(f"ไฟล์ {filename}: ExifTool Error -> {err}")
            except Exception as e:
                logs[-1] = f"❌ เซฟรูปพัง: {filename}"
                meta_list.append(f"ไฟล์ {filename}: Image Error -> {str(e)}")

        yield results, None, "\n".join(logs[-5:]), meta_list, raw_ai

    # 3. สร้าง ZIP
    if success_count > 0:
        logs.append(f"📦 กำลังบีบอัดไฟล์ {success_count} รูป...")
        yield results, None, "\n".join(logs[-5:]), meta_list, "Zipping..."
        shutil.make_archive(zip_base_name, 'zip', output_folder)
        yield results, zip_filepath, f"🎉 เสร็จเรียบร้อย! ทำสำเร็จ {success_count} รูป", meta_list, "Success"
    else:
        yield results, None, "❌ ล้มเหลวทุกรูป! ตรวจสอบช่อง AI Debug", meta_list, "Failed"

# --- UI Setup ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ AI Auto Metadata PRO (Stock batch)")
    state = gr.State([])
    with gr.Row():
        with gr.Column(scale=1):
            inp = gr.File(label="📂 อัปโหลดรูปภาพ", file_count="multiple")
            sld = gr.Slider(10, 50, 49, step=1, label="จำนวนคีย์เวิร์ด")
            btn = gr.Button("🚀 เริ่มงาน Batch", variant="primary")
            dl = gr.File(label="📦 ดาวน์โหลด ZIP ที่นี่")
            log = gr.Textbox(label="สถานะ", lines=5)
        with gr.Column(scale=2):
            gal = gr.Gallery(label="แกลเลอรี่ผลลัพธ์", columns=3, height="auto")
            info = gr.Textbox(label="ข้อมูล Metadata รายรูป (คลิกที่รูปด้านบน)", lines=8)
            raw = gr.Textbox(label="AI Debug (ดูข้อความดิบจาก AI ตรงนี้)", lines=5)

    btn.click(process, [inp, sld], [gal, dl, log, state, raw])
    gal.select(lambda e, s: s[e.index] if e.index < len(s) else "", [state], info)

demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
