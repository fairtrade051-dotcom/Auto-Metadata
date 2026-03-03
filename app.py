import os, subprocess, shutil, re, gradio as gr, ollama
from PIL import Image

output_folder = "/workspace/output_images"
zip_filepath = "/workspace/processed_images.zip"

def generate_metadata(image_path, kw_count):
    try:
        # สั่ง AI แบบบังคับเอาคำตอบ
        prompt = f"Describe this image. Format your output exactly as:\nTitle: [title]\nDescription: [description]\nKeywords: [keyword1, keyword2, ... {kw_count} words]"
        
        res = ollama.chat(model='llama3.2-vision', messages=[{
            'role': 'user',
            'content': prompt,
            'images': [image_path]
        }])
        
        txt = res['message']['content']
        
        # ล้างพวกเครื่องหมายดอกจันออกให้หมด
        clean_txt = txt.replace("*", "")
        
        # ดึงข้อมูล (Case-insensitive)
        title = "Untitled"
        desc = "No Description"
        keywords = []

        t_match = re.search(r"(?i)Title:\s*(.*)", clean_txt)
        if t_match: title = t_match.group(1).strip()

        d_match = re.search(r"(?i)Description:\s*(.*)", clean_txt)
        if d_match: desc = d_match.group(1).strip()

        k_match = re.search(r"(?i)Keywords:\s*(.*)", clean_txt)
        if k_match:
            keywords = [k.strip() for k in k_match.group(1).split(",") if len(k.strip()) > 1]
        
        # ถ้าหา Keywords ไม่เจอจริงๆ ให้กวาดคำมาจากเนื้อความทั้งหมดเลย
        if not keywords:
            keywords = [k.strip() for k in clean_txt.split() if len(k.strip()) > 3][:kw_count]

        return title, desc, keywords[:kw_count], txt
    except Exception as e:
        return "Error", "Error", ["error"], f"System Error: {str(e)}"

def process(files, kw_count):
    if not files: yield [], None, "❌ No files!", [], "Please upload images."; return
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    
    results, logs, meta_list = [], [], []
    yield results, None, "🚀 Starting Batch...", meta_list, "Waiting for AI..."

    for i, f in enumerate(files):
        filename = os.path.basename(f.name)
        logs.append(f"🔄 Processing {i+1}/{len(files)}")
        yield results, None, "\n".join(logs[-5:]), meta_list, ""
        
        t, d, k, raw_ai = generate_metadata(f.name, kw_count)
        
        # ถ้าพัง ให้โชว์ชื่อไฟล์ที่พังด้วย
        if t == "Error":
            logs[-1] = f"❌ Failed: {filename}"
        else:
            logs[-1] = f"✅ Done: {filename}"
            
        info = f"File: {filename}\nTitle: {t}\nKeywords: {', '.join(k)}"
        meta_list.append(info)
        
        out = os.path.join(output_folder, filename)
        with Image.open(f.name) as img:
            img.convert('RGB').save(out, "JPEG", quality=100)
        
        if t != "Error":
            kw_str = ", ".join(k)
            subprocess.run(["exiftool", "-overwrite_original", f"-Title={t}", f"-Description={d}", f"-Keywords={kw_str}", f"-Subject={kw_str}", out])
        
        results.append(out)
        yield results, None, "\n".join(logs[-5:]), meta_list, raw_ai

    shutil.make_archive(zip_filepath.replace('.zip',''), 'zip', output_folder)
    yield results, zip_filepath, "🎉 Batch Finished!", meta_list, "Done"

with gr.Blocks(theme=gr.themes.Default()) as demo:
    gr.Markdown("# 🖼️ AI Metadata Batch Pro")
    state = gr.State([])
    with gr.Row():
        with gr.Column(scale=1):
            inp = gr.File(label="Upload", file_count="multiple")
            sld = gr.Slider(10, 50, 49, step=1, label="Keywords")
            btn = gr.Button("🚀 Start", variant="primary")
            dl = gr.File(label="Download ZIP")
            log = gr.Textbox(label="Status", lines=3)
        with gr.Column(scale=2):
            gal = gr.Gallery(label="Output", columns=3)
            info = gr.Textbox(label="Metadata Info", lines=5)
            raw = gr.Textbox(label="AI Debug (ดูตรงนี้ถ้ามันขึ้น Error)", lines=5)

    btn.click(process, [inp, sld], [gal, dl, log, state, raw])
    gal.select(lambda e, s: s[e.index] if e.index < len(s) else "", [state], info)

demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
