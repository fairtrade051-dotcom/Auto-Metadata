import os, subprocess, shutil, gradio as gr
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image

# ตรวจสอบ GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
model_id = "microsoft/Florence-2-base"

print(f"⏳ กำลังโหลดโมเดล Florence-2 ไว้บน {device}... (รอนิดนึงครับ)")
# โหลดโมเดล
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
    if not files: yield [], None, "❌ ไม่มีไฟล์!", []; return
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)

    results, logs, meta_list = [], [], []
    
    for i, f in enumerate(files):
        fname = os.path.basename(f.name)
        logs.append(f"🔄 กำลังทำรูปที่ {i+1}/{len(files)}: {fname}")
        yield results, None, "\n".join(logs[-5:]), meta_list
        
        try:
            img = Image.open(f.name).convert("RGB")
            
            # 1. สร้าง Title (ใช้ Detailed Caption)
            caption = run_ai(img, "<DETAILED_CAPTION>")
            title = caption[:60].strip()
            
            # 2. สร้าง Keywords (ใช้ More Detailed Caption มาแยกคำ)
            tags_raw = run_ai(img, "<MORE_DETAILED_CAPTION>")
            # สกัดคำที่ยาวกว่า 3 ตัวอักษรมาเป็นคีย์เวิร์ด
            keywords = list(set([k.strip(",.") for k in tags_raw.split() if len(k) > 3]))[:kw_count]
            
            # 3. เซฟและฝัง Metadata
            out = os.path.join(output_folder, fname)
            img.save(out, "JPEG", quality=100)
            
            kw_str = ", ".join(keywords)
            subprocess.run(["exiftool", "-overwrite_original", f"-Title={title}", f"-Description={caption}", f"-Keywords={kw_str}", f"-Subject={kw_str}", out])
            
            results.append(out)
            meta_list.append(f"📌 {fname}\nTitle: {title}\nKeywords: {kw_str}")
            logs[-1] = f"✅ เสร็จแล้ว: {fname}"
        except Exception as e:
            logs[-1] = f"❌ พังที่รูปนี้: {str(e)}"
            
        yield results, None, "\n".join(logs[-5:]), meta_list

    shutil.make_archive(zip_filepath.replace('.zip',''), 'zip', output_folder)
    yield results, zip_filepath, "🎉 เสร็จสิ้นทุกรูปแล้ว!", meta_list

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🖼️ Auto Metadata (Florence-2 Version)")
    with gr.Row():
        with gr.Column():
            inp = gr.File(label="อัปโหลดรูปภาพ", file_count="multiple")
            sld = gr.Slider(10, 50, 30, step=1, label="จำนวน Keywords")
            btn = gr.Button("🚀 เริ่มทำงาน", variant="primary")
            dl = gr.File(label="ดาวน์โหลดไฟล์ ZIP")
            log = gr.Textbox(label="สถานะการทำงาน")
        with gr.Column():
            gal = gr.Gallery(label="แกลเลอรี่", columns=3)
            info = gr.Textbox(label="ข้อมูล Metadata", lines=10)

    btn.click(process, [inp, sld], [gal, dl, log, info])

demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=["/workspace"])
