import os, subprocess, shutil, re, gradio as gr, ollama
from PIL import Image

output_folder = "/workspace/output_images"
zip_filepath = "/workspace/processed_images.zip"

def generate_metadata(image_path, kw_count):
    try:
        # สั่ง AI แบบเข้มงวด
        prompt = f"Analyze this image. You MUST include these 3 lines in your response:\nTitle: (short title)\nDescription: (one sentence)\nKeywords: (comma separated list of {kw_count} words)"
        
        res = ollama.chat(model='llama3.2-vision', messages=[{
            'role': 'user',
            'content': prompt,
            'images': [image_path]
        }])
        
        txt = res['message']['content']
        
        # --- ระบบแกะข้อมูลแบบเหนียวพิเศษ ---
        title = "Untitled"
        desc = "No Description"
        keywords = []

        # หา Title
        t_match = re.search(r"(?i)Title:\s*(.*)", txt)
        if t_match: title = t_match.group(1).replace("*", "").strip()

        # หา Description
        d_match = re.search(r"(?i)Description:\s*(.*)", txt)
        if d_match: desc = d_match.group(1).replace("*", "").strip()

        # หา Keywords
        k_match = re.search(r"(?i)Keywords:\s*(.*)", txt)
        if k_match:
            raw_kws = k_match.group(1).replace("*", "").split(",")
            keywords = [k.strip() for k in raw_kws if len(k.strip()) > 1]
        
        # ถ้าหา Keywords ไม่เจอตามฟอร์แมต ให้ขุดจากบรรทัดที่ยาวที่สุด
        if not keywords:
            lines = txt.split('\n')
            for line in lines:
                if ',' in line and len(line) > 50:
                    keywords = [k.strip() for k in line.split(",") if len(k.strip()) > 1]
                    break

        return title, desc, keywords[:kw_count], txt
    except Exception as e:
        return "System Error", str(e), ["error"], str(e)

def process(files, kw_count):
    if not files: yield [], None, "❌ No files!", [], ""; return
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    
    results, logs, meta_list = [], [], []
    yield results, None, "🚀 Starting Process...", meta_list, ""

    for i, f in enumerate(files):
        filename = os.path.basename(f.name)
        logs.append(f"🔄 Processing {i+1}/{len(files)}: {filename}")
        yield results, None, "\n".join(logs[-5:]), meta_list, ""
        
        t, d, k, raw_ai = generate_metadata(f.name, kw_count)
        
        # เก็บข้อมูล Metadata
        info = f"File: {filename}\nTitle: {t}\nKeywords: {', '.join(k)}"
        meta_list.append(info)
        
        # จัดการไฟล์รูป
        out = os.path.join(output_folder, filename)
        with Image.open(f.name) as img:
            img.convert('RGB').save(out, "JPEG", quality=100)
        
        # ฝัง Metadata
        k_str = ", ".join(k)
        subprocess.run(["exiftool", "-overwrite_original", f"-Title={t}", f"-Description={d}", f"-Keywords={k_str}", f"-Subject={k_str}", out])
        
        results.append(out)
        logs[-1] = f"✅ Success: {filename}"
        yield results, None, "\n".join(logs[-5:]), meta_list, raw_ai

    shutil.make_archive(zip_filepath.replace('.zip',''), 'zip', output_folder)
    yield results, zip_filepath, "🎉 Finished! Download ZIP below.", meta_list, "Done"

# --- UI ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ AI Stock Metadata Pro")
    state = gr.State([])
    
    with gr.Row():
        with gr.Column(scale=1):
            inp = gr.File(label="Upload Images", file_count="multiple")
            sld = gr.Slider(10, 50, 49, step=1, label="Keywords Count")
            btn = gr.Button("🚀 Start Batch Process", variant="primary")
            dl = gr.File(label="Download ZIP")
            log = gr.Textbox(label="Status", lines=3)
        with gr.Column(scale=2):
            gal = gr.Gallery(label="Results", columns=3)
            info = gr.Textbox(label="Current Image Info", lines=5)
            raw = gr.Textbox(label="AI Debug (ดูว่า AI ตอบอะไร)", lines=5)

    btn.click(process, [inp, sld], [gal, dl, log, state, raw])
    gal.select(lambda e, s: s[e.index] if e.index < len(s) else "", [state], info)

demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
