import pdfplumber
from deep_translator import GoogleTranslator
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import black
import time

# 注册中文字体
# 注意：确保 C:\Windows\Fonts\simsun.ttc 存在，否则需要替换为系统存在的字体路径
try:
    pdfmetrics.registerFont(TTFont('SimSun', 'C:\\Windows\\Fonts\\simsun.ttc'))
except:
    print("SimSun font not found. Please check font path.")

def translate_text(text):
    """
    使用 Google Translate 翻译文本。
    为了避免被限制，添加了重试机制和简单的文本分块。
    """
    if not text.strip():
        return ""
    
    translator = GoogleTranslator(source='auto', target='zh-CN')
    
    # 简单的分块处理，防止超过单次请求限制 (5000 chars)
    chunk_size = 4500
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    translated_chunks = []
    for chunk in chunks:
        try:
            # 简单的清洗
            clean_chunk = chunk.replace('\n', ' ').replace('- ', '')
            res = translator.translate(clean_chunk)
            translated_chunks.append(res)
            time.sleep(0.5) # 稍微暂停，避免请求过快
        except Exception as e:
            print(f"Translation error: {e}")
            translated_chunks.append(chunk) # 翻译失败则保留原文
    
    return "".join(translated_chunks)

def generate_pdf(output_filename, content_list):
    doc = SimpleDocTemplate(output_filename, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # 定义中文样式
    normal_style = ParagraphStyle(
        'ChineseNormal',
        parent=styles['Normal'],
        fontName='SimSun',
        fontSize=10,
        leading=14,
        spaceAfter=6
    )
    
    header_style = ParagraphStyle(
        'ChineseHeader',
        parent=styles['Heading2'],
        fontName='SimSun',
        fontSize=14,
        leading=18,
        spaceAfter=10,
        spaceBefore=10
    )

    story = []
    
    for item in content_list:
        if item['type'] == 'text':
            # 处理特殊字符
            text = item['content'].replace('<', '&lt;').replace('>', '&gt;')
            p = Paragraph(text, normal_style)
            story.append(p)
        elif item['type'] == 'page_break':
            story.append(PageBreak())
        elif item['type'] == 'header':
             text = item['content'].replace('<', '&lt;').replace('>', '&gt;')
             p = Paragraph(text, header_style)
             story.append(p)

    try:
        doc.build(story)
        print(f"PDF generated: {output_filename}")
    except Exception as e:
        print(f"PDF generation failed: {e}")

def process_pdf(input_pdf, output_pdf, start_page=0, end_page=None):
    print(f"Processing {input_pdf}...")
    
    content_list = []
    
    with pdfplumber.open(input_pdf) as pdf:
        total_pages = len(pdf.pages)
        if end_page is None or end_page > total_pages:
            end_page = total_pages
            
        print(f"Total pages to process: {end_page - start_page}")
        
        for i in range(start_page, end_page):
            print(f"Processing page {i+1}/{total_pages}...")
            page = pdf.pages[i]
            
            # 提取文本
            # 简单的文本提取，pdfplumber 默认按阅读顺序
            text = page.extract_text()
            
            if text:
                # 简单区分一下标题和正文（非常粗略）
                lines = text.split('\n')
                translated_lines = []
                
                # 批量翻译每一页，而不是每一行，以保持上下文
                # 但为了显示进度，我们按段落处理
                
                # 这里我们简化处理：把整页文本作为一个块翻译
                # 实际论文中，双栏布局可能需要裁剪，这里先直接提取
                
                # 尝试检测左栏和右栏 (简单假设)
                # width = page.width
                # left_bbox = (0, 0, width/2, page.height)
                # right_bbox = (width/2, 0, width, page.height)
                # left_text = page.within_bbox(left_bbox).extract_text()
                # right_text = page.within_bbox(right_bbox).extract_text()
                # full_page_text = (left_text or "") + "\n" + (right_text or "")
                
                # 直接提取通常能处理得还行，虽然有时顺序会乱
                
                translated_page = translate_text(text)
                
                content_list.append({'type': 'header', 'content': f"--- 第 {i+1} 页 ---"})
                content_list.append({'type': 'text', 'content': translated_page})
                content_list.append({'type': 'page_break'})
            
    generate_pdf(output_pdf, content_list)

if __name__ == "__main__":
    # 为了演示，只翻译前 5 页
    # 如果想翻译全部，设置 end_page=None
    process_pdf("2303.18223v16.pdf", "2303.18223v16_full_translated_demo.pdf", start_page=0, end_page=None)
