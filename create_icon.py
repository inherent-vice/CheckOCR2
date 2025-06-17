from PIL import Image, ImageDraw, ImageFont
import os

def create_ocr_icon():
    # 아이콘 크기 (Windows .ico 파일은 보통 32x32, 48x48, 256x256 등의 크기를 지원)
    size = 256
    
    # 이미지 생성 (RGBA 모드로 투명도 지원)
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 배경 원 그리기 (파란색 그라데이션 효과)
    center = size // 2
    radius = size // 2 - 10
    
    # 배경 원 (진한 파란색)
    draw.ellipse([center-radius, center-radius, center+radius, center+radius], 
                 fill=(30, 144, 255, 255), outline=(0, 100, 200, 255), width=3)
    
    # 내부 원 (밝은 파란색)
    inner_radius = radius - 20
    draw.ellipse([center-inner_radius, center-inner_radius, center+inner_radius, center+inner_radius], 
                 fill=(70, 180, 255, 200))
    
    # 문서 모양 그리기 (흰색)
    doc_width = size // 3
    doc_height = size // 2
    doc_x = center - doc_width // 2
    doc_y = center - doc_height // 2
    
    # 문서 배경
    draw.rectangle([doc_x, doc_y, doc_x + doc_width, doc_y + doc_height], 
                   fill=(255, 255, 255, 255), outline=(200, 200, 200, 255), width=2)
    
    # 문서 내부 텍스트 라인들 (OCR 스캔된 텍스트를 의미)
    line_color = (100, 100, 100, 255)
    line_width = 2
    line_spacing = doc_height // 6
    
    for i in range(4):
        y_pos = doc_y + line_spacing + (i * line_spacing)
        line_length = doc_width - 20 if i % 2 == 0 else doc_width - 30
        draw.rectangle([doc_x + 10, y_pos, doc_x + line_length, y_pos + 3], 
                       fill=line_color)
    
    # 돋보기 그리기 (OCR/검색을 의미)
    mag_center_x = center + radius // 2
    mag_center_y = center - radius // 2
    mag_radius = 15
    
    # 돋보기 렌즈
    draw.ellipse([mag_center_x - mag_radius, mag_center_y - mag_radius, 
                  mag_center_x + mag_radius, mag_center_y + mag_radius], 
                 fill=(255, 255, 255, 200), outline=(50, 50, 50, 255), width=3)
    
    # 돋보기 손잡이
    handle_length = 20
    handle_angle_x = mag_center_x + mag_radius * 0.7
    handle_angle_y = mag_center_y + mag_radius * 0.7
    handle_end_x = handle_angle_x + handle_length * 0.7
    handle_end_y = handle_angle_y + handle_length * 0.7
    
    draw.line([handle_angle_x, handle_angle_y, handle_end_x, handle_end_y], 
              fill=(50, 50, 50, 255), width=4)
    
    # 여러 크기로 저장 (Windows .ico 파일 호환성을 위해)
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for s in sizes:
        resized = img.resize((s, s), Image.Resampling.LANCZOS)
        images.append(resized)
    
    # .ico 파일로 저장
    img.save('app_icon.ico', format='ICO', sizes=[(s, s) for s in sizes])
    print("아이콘 파일 'app_icon.ico'가 생성되었습니다!")
    
    # PNG 파일로도 저장 (미리보기용)
    img.save('app_icon_preview.png', format='PNG')
    print("미리보기 파일 'app_icon_preview.png'도 생성되었습니다!")

if __name__ == "__main__":
    create_ocr_icon() 