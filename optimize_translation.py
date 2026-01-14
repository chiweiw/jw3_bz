import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import black
import time
import os

# 注册中文字体
try:
    pdfmetrics.registerFont(TTFont('SimSun', 'C:\\Windows\\Fonts\\simsun.ttc'))
except:
    print("SimSun font not found. Please check font path.")

def translate_text(text):
    if not text.strip():
        return ""
    
    # 移除多余换行，保留段落完整性
    text = text.replace('\n', ' ')
    
    translator = GoogleTranslator(source='auto', target='zh-CN')
    chunk_size = 4500
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    translated_chunks = []
    for chunk in chunks:
        try:
            res = translator.translate(chunk)
            if res:
                translated_chunks.append(res)
            else:
                translated_chunks.append(chunk) # 翻译返回None时保留原文
            time.sleep(0.5) 
        except Exception as e:
            print(f"Translation error: {e}")
            translated_chunks.append(chunk)
    
    return "".join(translated_chunks)

def generate_pdf(output_filename, content_list):
    doc = SimpleDocTemplate(output_filename, pagesize=A4)
    styles = getSampleStyleSheet()
    
    normal_style = ParagraphStyle(
        'ChineseNormal',
        parent=styles['Normal'],
        fontName='SimSun',
        fontSize=10,
        leading=14,
        spaceAfter=6
    )
    
    # 图像居中样式
    # ReportLab Image flowable is centered by default in SimpleDocTemplate if not specified otherwise? 
    # Actually need to wrap in flowable or just append.
    
    story = []
    
    for item in content_list:
        if item['type'] == 'text':
            text = item['content'].replace('<', '&lt;').replace('>', '&gt;')
            p = Paragraph(text, normal_style)
            story.append(p)
        elif item['type'] == 'page_break':
            story.append(PageBreak())
        elif item['type'] == 'header':
             text = item['content'].replace('<', '&lt;').replace('>', '&gt;')
             p = Paragraph(f"<b>{text}</b>", normal_style)
             story.append(p)
             story.append(Spacer(1, 10))
        elif item['type'] == 'image':
            img_path = item['content']
            try:
                # 限制图片宽度，保持比例
                img = ReportLabImage(img_path)
                # A4 width is approx 595 points. Margins are usually 72. So usable is ~450.
                max_width = 450
                img_width = img.drawWidth
                img_height = img.drawHeight
                
                if img_width > max_width:
                    ratio = max_width / img_width
                    img.drawWidth = max_width
                    img.drawHeight = img_height * ratio
                
                story.append(Spacer(1, 10))
                story.append(img)
                story.append(Spacer(1, 10))
            except Exception as e:
                print(f"Error adding image {img_path}: {e}")

    try:
        doc.build(story)
        print(f"PDF generated: {output_filename}")
    except Exception as e:
        print(f"PDF generation failed: {e}")

def process_pdf(input_pdf, output_pdf, start_page=0, end_page=None):
    print(f"Processing {input_pdf}...")
    doc = fitz.open(input_pdf)
    
    if end_page is None or end_page > len(doc):
        end_page = len(doc)
    
    content_list = []
    temp_img_dir = "temp_images"
    if not os.path.exists(temp_img_dir):
        os.makedirs(temp_img_dir)
        
    for i in range(start_page, end_page):
        print(f"Processing page {i+1}...")
        page = doc[i]
        
        # 提取 Block，包含文本和图像
        # blocks: (x0, y0, x1, y1, "lines", block_no, block_type)
        # block_type: 0=text, 1=image
        blocks = page.get_text("blocks")
        
        # 排序：PyMuPDF 默认排序通常是阅读顺序，但对于双栏，有时需要检查
        # 简单的双栏排序策略：先按 y 排序，再按 x？不对。
        # 标准双栏：左栏 (x < width/2) 先读完，右栏 (x > width/2) 后读。
        # 我们可以根据 x0 坐标判断栏目。
        # 但 PyMuPDF 的 "blocks" 模式通常已经尝试按阅读顺序排序了。
        # 让我们先信任默认顺序，如果乱了再调整。
        
        # 实际上，PyMuPDF blocks 默认顺序就是 reading order (text extraction order)
        
        content_list.append({'type': 'header', 'content': f"--- 第 {i+1} 页 ---"})
        
        for block in blocks:
            bbox = block[:4]
            text = block[4]
            block_type = block[6]
            
            if block_type == 0: # 文本
                if text.strip():
                    translated = translate_text(text)
                    content_list.append({'type': 'text', 'content': translated})
            elif block_type == 1: # 图像
                # PyMuPDF block 图片只是占位符，我们需要提取实际图片
                # 或者我们可以直接截图 bbox 区域 (clip)
                # 使用 page.get_pixmap(clip=bbox) 可以获取该区域的截图，这样即使是表格或复杂矢量图也能保留
                # 这比提取 raw image 更稳健（raw image 可能是 mask 或 fragmented）
                
                try:
                    # 截图该区域
                    pix = page.get_pixmap(clip=bbox, dpi=150) # dpi 提高一点清晰度
                    img_filename = f"{temp_img_dir}/page_{i+1}_block_{block[5]}.png"
                    pix.save(img_filename)
                    content_list.append({'type': 'image', 'content': img_filename})
                except Exception as e:
                    print(f"Error extracting image block: {e}")
        
        content_list.append({'type': 'page_break'})
    
    generate_pdf(output_pdf, content_list)
    
    # 清理临时图片
    # import shutil
    # shutil.rmtree(temp_img_dir)

if __name__ == "__main__":
    # 处理全部页面
    process_pdf("2303.18223v16.pdf", "2303.18223v16_full_translated.pdf", start_page=0, end_page=None)
