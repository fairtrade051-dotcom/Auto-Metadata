import os, subprocess, shutil, re, gradio as gr, ollama
from PIL import Image

output_folder = "/workspace/output_images"
zip_base_name = "/workspace/processed_images"
zip_filepath = "/workspace/processed_images.zip"

def generate_metadata(image_path, kw_count):
    try:
        # สั่ง AI แบบทิ้งไพ่ตาย (ถ้าไม่ตอบตามฟอร์แมต ให้ตอบลิสต์มาเลย)
        prompt = f"Analyze this image. Return the result in this structure:\nTitle: [title]\nDescription: [description]\nKeywords: [keyword1, keyword2, ... {kw_count} keywords]"
        
        res = ollama.chat(model='llama3.2-vision', messages=[{
            'role': 'user', 'content': prompt, 'images': [image_path]
        }])
        
        txt = res['message']['content']
        # ลบเครื่องหมายพิเศษออกเพื่อให้อ่านง่าย
        clean_txt = txt.replace("*", "").replace("#", "")
        
        title, desc, keywords = "Untitled", "No Description", []

        # ใช้ Regex แบบ Case-Insensitive และยืดหยุ่นสูง
        t_match = re.search(r"(?i)Title\s*:\s*(.*)", clean_txt)
        if t_match: title = t_match.group(1).split('\n')[0].strip()

        d_match = re.search(r"(?i)Description\s*:\s*(.*)", clean_txt)
        if d_match: desc = d_match.group(1).split('\n')[0].strip()

        k_match = re.search(r"(?i)Keywords\s*:\s*(.*)", clean_txt)
        if k_match:
            raw_kws = k_match.group(1).split(",")
            keywords = [k.strip() for k in raw_kws if len(k.strip()) > 1]
        
        # --- แผนสำรอง: ถ้า AI ไม่ตอบตามฟอร์แมต ---
        if not keywords or len(keywords) < 5:
            # กวาดเอาทุกคำที่คั่นด้วยลูกน้ำมาเป็นคีย์เวิร์ด
            keywords = [k.strip() for k in clean_txt.replace("\n", ",").split(",") if len(k.strip()) > 2]

        return title, desc, keywords[:kw_count], txt
    except Exception as e:
        return "ERROR_SYSTEM", str(e), [], f"❌ AI CRASH: {str(e)}"

def embed_metadata(image_path, title, desc, keywords):
    try:
        kw_str = ", ".join(keywords)
        # ฝัง Tags แบบถล่มทลาย (ครอบคลุมทุกที่)
        cmd = [
            "exiftool", "-overwrite_original", "-charset", "UTF8",
            f"-Title={title}", f"-XPTitle={title}", f"-XMP-dc:Title={title}",
            f"-Description={desc}", f"-ImageDescription={desc}", f"-XMP-dc:Description={desc}",
            f"-Keywords={kw_str}", f"-Subject={kw_str}", f"-XMP-dc:Subject={kw_str}",
            f"-IPTC:Keywords={kw_str}", f"-XPKeywords={kw_str}",
            image_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True, "Success"
    except Exception as e:
        return False, str(e)

def process(files, kw_count):
    if not files:
        yield [], None, "❌ ไม่พบไฟล์!", [], "กรุณาเลือกรูปภาพก่อนกด Start"
        return
    
    # ล้างบ้านก่อนเริ่มงาน
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    if os.path.exists(zip_filepath): os.remove(zip_filepath)
    
    results, logs, meta_list = [], [], []
    success_count = 0
    
    yield results, None, "🚀 เริ่มต้นระบบ...", meta_list, "กำลังติดต่อ AI..."

    for i, f in enumerate(files):
        filename = os.path.basename(f.name)
        logs.append(f"🔄 [{i+1}/{len(files)}] {filename}")
        yield results, None, "\n".join(logs[-5:]), meta_
