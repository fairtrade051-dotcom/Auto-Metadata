import os, subprocess, shutil, re, gradio as gr, ollama
from PIL import Image

output_folder = "/workspace/output_images"
zip_filepath = "/workspace/processed_images.zip"

def generate_metadata(image_path, kw_count):
    try:
        # สั่ง AI ให้ชัดเจนขึ้น
        prompt = f"Analyze this image. Output exactly in this format:\nTitle: (short title)\nDescription: (one sentence)\nKeywords: (list {kw_count} words separated by commas)"
        
        res = ollama.chat(model='llama3.2-vision', messages=[{
            'role': 'user',
            'content': prompt,
            'images': [image_path]
        }])
        
        txt = res['message']['content']
        print(f"AI Response: {txt}") # ดูใน Terminal ของ RunPod จะเห็นข้อความดิบ

        # ใช้ Regex ที่ยืดหยุ่นขึ้น (รองรับ ** หรือช่องว่างแปลกๆ)
        title = re.search(r"(?i)Title:\s*(.*)", txt)
        desc = re.search(r"(?i)Description:\s*(.*)", txt)
        kws = re.search(r"(?i)Keywords:\s*(.*)", txt)

        t_val = title.group(1).replace("*", "").strip() if title else "Untitled"
        d_val = desc.group(1).replace("*", "").strip() if desc else "No Description"
        
        if kws:
            kw_list = [k.strip().replace("*", "") for k in kws.group(1).split(",") if k.strip()]
        else:
            # ถ้าหาคำว่า Keywords ไม่เจอเลย ให้เอาบรรทัดสุดท้ายมาลองแยกดู
            kw_list = [k.strip() for k in txt.split("\n")[-1].split(",") if len(k) > 1]

        return t_val, d_val, kw_list[:kw_count]
    except Exception as e:
        return "Error", f"System Error: {str(e)}", ["error"]

def process(files, kw_count):
    if not files: yield [], None, "❌ No files uploaded", []; return
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    
    results, logs, meta_list = [], [], []
    yield results, None, "🚀 Starting...", meta_list

    for i, f in enumerate(files):
        filename = os.path.basename(f.name)
        logs.append(f"🔄 Processing {i+1}/{len(files)}: {filename}")
        yield results, None, "\n".join(logs[-5:]), meta_list
        
        t, d, k = generate_metadata(f.name, kw_count)
        
        # เก็บข้อมูลไว้โชว์
        info = f"File: {filename}\nTitle: {t}\nKeywords ({len(k)}): {', '.join(k)}"
        meta_list.append(info)
        
        # บันทึกรูปและฝัง Metadata
        out = os.path.join(output_folder, filename)
        with Image.open(f.name) as img:
            img.convert('RGB').save(out, "JPEG", quality=100)
        
        # ฝัง Metadata ด้วย Exiftool
        kw_str = ", ".join(k)
        subprocess.run(["exiftool", "-overwrite_original", f"-Title={t}", f"-Description={d}", f"-Keywords={kw_str}", f"-Subject={kw_str}", out])
        
        results.append(out)
        logs[-1] = f"✅ Finished {i+1}/{len(files)}: {filename}"
        yield results, None, "\n".join(logs[-5:]), meta_list

    # สร้าง ZIP
    shutil.make_archive(zip_filepath.replace('.zip',''), 'zip', output_folder)
    yield results, zip_filepath, "🎉 All Done! Download ZIP below.", meta_list

# --- UI Layout ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ AI Auto Metadata (Stock Photo Edition)")
    state = gr.State([])
    
    with gr.Row():
        with gr.Column(scale=1):
            inp = gr.File(label="Upload Images", file_count="multiple")
            sld = gr.Slider(10, 50, 49, step=1, label="Target Keyword Count")
            btn = gr.Button("🚀 Start Processing", variant="primary")
            dl = gr.File(label="Download Processed ZIP")
            log = gr.Textbox(label="Status Log", lines=4)
        with gr.Column(scale=2):
            gal = gr.Gallery(label="Processed Results", columns=3, height="auto")
            info = gr.Textbox(label="Image Details (Click image in gallery)", lines=8)

    btn.click(process, [inp, sld], [gal, dl, log, state])
    gal.select(lambda e, s: s[e.index] if e.index < len(s) else "No info", [state], info)

demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
