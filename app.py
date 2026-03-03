import os, subprocess, shutil, gradio as gr
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image

# โหลด Model ครั้งแรกครั้งเดียว (ขนาด ~500MB)
device = "cuda" if torch.cuda.is_available() else "cpu"
model_id = "microsoft/Florence-2-base"
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True).to(device).eval()
processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

output_folder = "/workspace/output_images"
zip_filepath = "/workspace/processed_images.zip"

def run_ai(image, task_prompt):
    inputs = processor(text=task_prompt, images=image, return_tensors="pt").to(device)
    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=1024,
        num_beams=3
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return generated_text

def process(files, kw_count):
    if not files: yield [], None, "❌ No files!"; return
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)

    results, logs, meta_list = [], [], []
    
    for i, f in enumerate(files):
        fname = os.path.basename(f.name)
        logs.append(f"🔄 Processing {i+1}/{len(files)}: {fname}")
        yield results, None, "\n".join(logs[-5:]), meta_list
        
        img = Image.open(f.name).convert("RGB")
        
        # 1. สร้าง Title & Description
        caption = run_ai(img, "<DETAILED_CAPTION>")
        title = caption[:50] + "..." if len(caption) > 50 else caption
        
        # 2. สร้าง Keywords (ใช้วิธีสกัดจาก Caption)
        tags_raw = run_ai(img, "<MORE_DETAILED_CAPTION>")
        keywords = list(set([k.strip() for k in tags_raw.replace(".", "").split() if len(k) > 3]))[:kw_count]
        
        # 3. เซฟรูปและฝัง Metadata
        out = os.path.join(output_folder, fname)
        img.save(out, "JPEG", quality=100)
        
        kw_str = ", ".join(keywords)
        subprocess.run(["exiftool", "-overwrite_original", f"-Title={title}", f"-Description={caption}", f"-Keywords={kw_str}", f"-Subject={kw_str}", out])
        
        results.append(out)
        meta_list.append(f"📌 {fname}\nTitle: {title}\nKeywords: {kw_str}")
        logs[-1] = f"✅ Done: {fname}"
        yield results, None, "\n".join(logs[-5:]), meta_list

    shutil.make_archive(zip_filepath.replace('.zip',''), 'zip', output_folder)
    yield results, zip_filepath, "🎉 Finished!", meta_list

with gr.Blocks() as demo:
    gr.Markdown("# 🖼️ Auto Metadata (No Ollama Version)")
    with gr.Row():
        with gr.Column():
            inp = gr.File(file_count="multiple")
            sld = gr.Slider(10, 50, 30, step=1, label="Keywords Count")
            btn = gr.Button("🚀 Start", variant="primary")
            dl = gr.File(label="Download ZIP")
            log = gr.Textbox(label="Status")
        with gr.Column():
            gal = gr.Gallery(columns=3)
            info = gr.Textbox(label="Info", lines=10)

    state = gr.State([])
    btn.click(process, [inp, sld], [gal, dl, log, info])

demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
