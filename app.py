import os, subprocess, shutil, gradio as gr, ollama
from PIL import Image

output_folder = "/workspace/output_images"
zip_filepath = "/workspace/processed_images.zip"

def extract_val(text, label):
    """ฟังก์ชันขุดหาข้อมูลแบบไม่สนฟอร์แมต"""
    for line in text.split('\n'):
        if label.lower() in line.lower():
            return line.split(':', 1)[-1].replace('*', '').strip()
    return ""

def generate_metadata(image_path, kw_count):
    try:
        prompt = f"Act as a stock photo expert. Provide Title, Description, and {kw_count} Keywords for this image. Format: Title: [..] Description: [..] Keywords: [k1, k2...]"
        
        res = ollama.chat(model='llama3.2-vision', messages=[{
            'role': 'user', 'content': prompt, 'images': [image_path]
        }])
        
        raw_txt = res['message']['content']
        
        # แกะข้อมูล
        title = extract_val(raw_txt, "Title") or "Untitled Stock Photo"
        desc = extract_val(raw_txt, "Description") or "No description provided."
        kw_raw = extract_val(raw_txt, "Keywords")
        
        if kw_raw:
            keywords = [k.strip() for k in kw_raw.split(',') if len(k.strip()) > 1]
        else:
            # ถ้าหา Keywords ไม่เจอจริงๆ ให้กวาดคำจากทั้งประโยค
            keywords = [k.strip() for k in raw_txt.replace('\n', ' ').split() if len(k) > 3]

        return title, desc, keywords[:kw_count], raw_txt
    except Exception as e:
        return "ERROR", str(e), [], f"❌ AI Error: {str(e)}"

def process(files, kw_count):
    if not files: yield [], None, "❌ ไม่มีไฟล์", [], ""; return
    
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    
    res_images, logs, meta_list = [], [], []
    success_count = 0

    for i, f in enumerate(files):
        fname = os.path.basename(f.name)
        logs.append(f"🔄 ทำรูป {i+1}/{len(files)}: {fname}")
        yield res_images, None, "\n".join(logs[-5:]), meta_list, "Analyzing..."
        
        t, d, k, raw_ai = generate_metadata(f.name, kw_count)
        
        if t == "ERROR":
            logs[-1] = f"❌ AI พัง: {fname}"
        elif not k:
            logs[-1] = f"⚠️ ไม่มี Keyword: {fname}"
        else:
            # เซฟและฝัง Tag
            out = os.path.join(output_folder, fname)
            try:
                with Image.open(f.name) as img:
                    img.convert('RGB').save(out, "JPEG", quality=100)
                
                kw_str = ", ".join(k)
                # ฝังแบบปูพรม ทุก Tag ที่มีในโลก
                subprocess.run(["exiftool", "-overwrite_original", f"-Title={t}", f"-Description={d}", f"-Keywords={kw_str}", f"-Subject={kw_str}", out], capture_output=True)
                
                success_count += 1
                res_images.append(out)
                logs[-1] = f"✅ สำเร็จ: {fname}"
                meta_list.append(f"📌 {fname}\nTitle: {t}\nKeywords: {kw_str}")
            except Exception as e:
                logs[-1] = f"❌ พัง: {str(e)}"

        yield res_images, None, "\n".join(logs[-5:]), meta_list, raw_ai

    if success_count > 0:
        shutil.make_archive(zip_filepath.replace('.zip',''), 'zip', output_folder)
        yield res_images, zip_filepath, f"🎉 เสร็จ! สำเร็จ {success_count} รูป", meta_list, "Done"
    else:
        yield res_images, None, "❌ ล้มเหลวทุกรูป เช็คช่อง AI Debug!", meta_list, "Failed"

with gr.Blocks(theme=gr.themes.Default()) as demo:
    gr.Markdown("# 🖼️ AI Metadata Master Final")
    with gr.Row():
        with gr.Column():
            inp = gr.File(file_count="multiple")
            sld = gr.Slider(10, 50, 49, step=1, label="Keywords")
            btn = gr.Button("🚀 START", variant="primary")
            dl = gr.File(label="Download ZIP")
            log = gr.Textbox(label="Status", lines=5)
        with gr.Column():
            gal = gr.Gallery(columns=3)
            info = gr.Textbox(label="Metadata Info", lines=5)
            debug = gr.Textbox(label="AI Debug (สำคัญมาก ถ้าพังดูตรงนี้)", lines=5)

    btn.click(process, [inp, sld], [gal, dl, log, gr.State([]), debug])
    gal.select(lambda e, s: s[e.index] if s and e.index < len(s) else "", [gr.State([])], info)

demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
