import os, subprocess, shutil, re, gradio as gr, ollama
from PIL import Image

output_folder = "/workspace/output_images"
zip_filepath = "/workspace/processed_images.zip"

def generate_metadata(image_path, kw_count):
    try:
        prompt = f"Describe this image for stock photography. Output as:\nTitle: [title]\nDescription: [description]\nKeywords: [keyword1, keyword2, ... {kw_count} words]"
        
        res = ollama.chat(model='llama3.2-vision', messages=[{
            'role': 'user', 'content': prompt, 'images': [image_path]
        }])
        
        txt = res['message']['content'].replace("*", "")
        
        title = "Untitled"
        desc = "No Description"
        keywords = []

        # ใช้ Regex ดึงข้อมูล
        t_match = re.search(r"(?i)Title:\s*(.*)", txt)
        if t_match: title = t_match.group(1).strip()

        d_match = re.search(r"(?i)Description:\s*(.*)", txt)
        if d_match: desc = d_match.group(1).strip()

        k_match = re.search(r"(?i)Keywords:\s*(.*)", txt)
        if k_match:
            keywords = [k.strip() for k in k_match.group(1).split(",") if len(k.strip()) > 1]
        
        if not keywords:
            keywords = [k.strip() for k in txt.split() if len(k.strip()) > 3][:kw_count]

        return title, desc, keywords[:kw_count], txt
    except Exception as e:
        return "Error", "Error", ["error"], f"AI Error: {str(e)}"

def embed_metadata(image_path, title, desc, keywords):
    try:
        kw_str = ", ".join(keywords)
        # ฝังมันทุก Tag ที่โลกนี้ใช้ (Windows, Adobe, Stock sites)
        cmd = [
            "exiftool", "-overwrite_original", "-charset", "UTF8",
            f"-Title={title}",
            f"-XPTitle={title}",
            f"-XMP-dc:Title={title}",
            f"-Description={desc}",
            f"-ImageDescription={desc}",
            f"-XMP-dc:Description={desc}",
            f"-Keywords={kw_str}",
            f"-Subject={kw_str}",
            f"-XMP-dc:Subject={kw_str}",
            f"-IPTC:Keywords={kw_str}",
            f"-XPKeywords={kw_str}",
            image_path
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def process(files, kw_count):
    if not files: yield [], None, "❌ No files!", [], "Please upload images."; return
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    
    results, logs, meta_list = [], [], []
    yield results, None, "🚀 Starting...", meta_list, ""

    for i, f in enumerate(files):
        filename = os.path.basename(f.name)
        logs.append(f"🔄 Processing {i+1}/{len(files)}")
        yield results, None, "\n".join(logs[-5:]), meta_list, ""
        
        t, d, k, raw_ai = generate_metadata(f.name, kw_count)
        
        if t == "Error":
            logs[-1] = f"❌ AI Fail: {filename}"
            meta_list.append(f"File: {filename}\nError: AI did not respond")
        else:
            out = os.path.join(output_folder, filename)
            with Image.open(f.name) as img:
                img.convert('RGB').save(out, "JPEG", quality=100)
            
            success, ex_log = embed_metadata(out, t, d, k)
            if success:
                logs[-1] = f"✅ Success: {filename}"
                meta_list.append(f"File: {filename}\nTitle: {t}\nKeywords: {', '.join(k)}")
            else:
                logs[-1] = f"⚠️ Tag Fail: {filename}"
                meta_list.append(f"File: {filename}\nExifTool Error: {ex_log}")
        
        results.append(out if t != "Error" else f.name)
        yield results, None, "\n".join(logs[-5:]), meta_list, raw_ai

    shutil.make_archive(zip_filepath.replace('.zip',''), 'zip', output_folder)
    yield results, zip_filepath, "🎉 Batch Done!", meta_list, "All processes finished."

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ AI Stock Metadata Pro (Final Version)")
    state = gr.State([])
    with gr.Row():
        with gr.Column(scale=1):
            inp = gr.File(label="Upload", file_count="multiple")
            sld = gr.Slider(10, 50, 49, step=1, label="Target Keywords")
            btn = gr.Button("🚀 Start", variant="primary")
            dl = gr.File(label="Download ZIP")
            log = gr.Textbox(label="Status", lines=3)
        with gr.Column(scale=2):
            gal = gr.Gallery(label="Results", columns=3)
            info = gr.Textbox(label="Current Metadata Info", lines=8)
            raw = gr.Textbox(label="AI Debug", lines=5)

    btn.click(process, [inp, sld], [gal, dl, log, state, raw])
    gal.select(lambda e, s: s[e.index] if e.index < len(s) else "", [state], info)

demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
