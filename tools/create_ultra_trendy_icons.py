from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import math
import random

def create_glassmorphism_icon():
    """🔮 Glassmorphism - 반투명 유리 효과의 초세련 디자인"""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    
    # 배경 그라데이션 (깊이감)
    for i in range(size//2):
        ratio = i / (size//2)
        # 딥 블루에서 퍼플로 그라데이션
        r = int(30 + (120 - 30) * ratio)
        g = int(30 + (80 - 30) * ratio)  
        b = int(60 + (200 - 60) * ratio)
        alpha = int(20 + 30 * (1 - ratio))
        
        draw.ellipse([center-i, center-i, center+i, center+i], 
                    fill=(r, g, b, alpha))
    
    # 메인 글래스 원형 (반투명)
    glass_radius = 80
    # 여러 겹의 글래스 효과
    for layer in range(5):
        current_radius = glass_radius - layer * 2
        alpha = 40 - layer * 5
        
        # 글래스 본체
        draw.ellipse([center-current_radius, center-current_radius, 
                     center+current_radius, center+current_radius], 
                    fill=(255, 255, 255, alpha))
        
        # 글래스 하이라이트
        highlight_offset = layer * 3
        draw.ellipse([center-current_radius+highlight_offset, 
                     center-current_radius+highlight_offset,
                     center+current_radius-20, center+current_radius-20], 
                    outline=(255, 255, 255, 80-layer*10), width=2)
    
    # 중앙 OCR 심볼 (frosted glass 효과)
    doc_width = 50
    doc_height = 65
    doc_x = center - doc_width // 2
    doc_y = center - doc_height // 2
    
    # 문서 배경 (frosted glass)
    draw.rounded_rectangle([doc_x, doc_y, doc_x + doc_width, doc_y + doc_height], 
                          radius=8, fill=(255, 255, 255, 120), 
                          outline=(255, 255, 255, 180), width=2)
    
    # 스캔 라인들 (블러 효과)
    for i in range(6):
        y_pos = doc_y + 12 + (i * 8)
        line_width = doc_width - 16 - (i % 2) * 8
        alpha = 200 - i * 15
        
        draw.rounded_rectangle([doc_x + 8, y_pos, doc_x + 8 + line_width, y_pos + 3], 
                              radius=2, fill=(100, 150, 255, alpha))
    
    # 글래스 하이라이트 스트로크
    draw.ellipse([center-glass_radius+15, center-glass_radius+15, 
                 center-glass_radius+35, center-glass_radius+35], 
                outline=(255, 255, 255, 150), width=3)
    
    return img

def create_y2k_holographic_icon():
    """🌈 Y2K Retrofuturism - 홀로그램 크롬 효과의 사이버틱 디자인"""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    
    # 홀로그램 배경 (iridescent 효과)
    for i in range(100):
        angle = i * 3.6  # 360도를 100등분
        radius = 120
        
        # 무지개 색상 계산
        hue_shift = (i * 7) % 360
        if hue_shift < 60:
            r, g, b = 255, int(255 * hue_shift / 60), 255
        elif hue_shift < 120:
            r, g, b = int(255 * (120 - hue_shift) / 60), 255, 255
        elif hue_shift < 180:
            r, g, b = 255, 255, int(255 * (hue_shift - 120) / 60)
        elif hue_shift < 240:
            r, g, b = 255, int(255 * (240 - hue_shift) / 60), 255
        elif hue_shift < 300:
            r, g, b = int(255 * (hue_shift - 240) / 60), 255, 255
        else:
            r, g, b = 255, 255, int(255 * (360 - hue_shift) / 60)
        
        # 크롬 효과를 위한 알파값 조정
        alpha = int(30 + 20 * math.sin(i * 0.2))
        
        x1 = center + int(radius * math.cos(math.radians(angle)))
        y1 = center + int(radius * math.sin(math.radians(angle)))
        x2 = center + int((radius-30) * math.cos(math.radians(angle)))
        y2 = center + int((radius-30) * math.sin(math.radians(angle)))
        
        draw.line([x1, y1, x2, y2], fill=(r, g, b, alpha), width=2)
    
    # 메인 크롬 원형
    chrome_radius = 70
    for layer in range(10):
        current_radius = chrome_radius - layer * 2
        
        # 크롬 그라데이션 (핑크-블루-퍼플)
        if layer < 3:
            color = (255, 20, 147, 180 - layer * 20)  # Hot Pink
        elif layer < 6:
            color = (0, 191, 255, 160 - layer * 15)   # Deep Sky Blue  
        else:
            color = (138, 43, 226, 140 - layer * 10)  # Blue Violet
            
        draw.ellipse([center-current_radius, center-current_radius, 
                     center+current_radius, center+current_radius], 
                    outline=color, width=2)
    
    # Y2K 스타일 OCR 심볼
    # 사이버틱 텍스트 블록
    block_size = 40
    block_x = center - block_size // 2
    block_y = center - block_size // 2
    
    # 네온 핑크 텍스트 블록
    draw.rounded_rectangle([block_x, block_y, block_x + block_size, block_y + block_size], 
                          radius=5, fill=(255, 20, 147, 200), 
                          outline=(0, 255, 255, 255), width=2)
    
    # 홀로그램 스캔 라인들
    for i in range(5):
        y_pos = block_y + 8 + (i * 6)
        line_length = block_size - 16 + (i % 2) * 8
        
        # 사이버틱 컬러 (cyan/magenta)
        if i % 2 == 0:
            color = (0, 255, 255, 255)  # Cyan
        else:
            color = (255, 0, 255, 255)  # Magenta
            
        draw.rectangle([block_x + 8, y_pos, block_x + 8 + line_length, y_pos + 2], 
                      fill=color)
    
    # 홀로그램 글리치 효과
    for i in range(8):
        glitch_x = center - 50 + random.randint(0, 100)
        glitch_y = center - 50 + random.randint(0, 100)
        glitch_size = random.randint(2, 6)
        
        glitch_color = random.choice([
            (255, 0, 255, 150),   # Magenta
            (0, 255, 255, 150),   # Cyan
            (255, 255, 0, 150)    # Yellow
        ])
        
        draw.rectangle([glitch_x, glitch_y, glitch_x + glitch_size, glitch_y + 1], 
                      fill=glitch_color)
    
    return img

def create_3d_isometric_icon():
    """🎲 3D Isometric - 입체적 아이소메트릭 게임풍 디자인"""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    
    # 아이소메트릭 배경 (큐브 패턴)
    cube_size = 15
    for row in range(-3, 4):
        for col in range(-3, 4):
            # 아이소메트릭 좌표 변환
            iso_x = center + (col - row) * cube_size * 0.866
            iso_y = center + (col + row) * cube_size * 0.5
            
            # 거리에 따른 알파값
            distance = math.sqrt(row*row + col*col)
            alpha = max(0, int(50 - distance * 8))
            
            if alpha > 0:
                # 미니 큐브 그리기
                draw.polygon([
                    (iso_x, iso_y),
                    (iso_x + cube_size * 0.866, iso_y + cube_size * 0.5),
                    (iso_x, iso_y + cube_size),
                    (iso_x - cube_size * 0.866, iso_y + cube_size * 0.5)
                ], fill=(100, 150, 255, alpha), outline=(80, 120, 200, alpha))
    
    # 메인 3D 문서 큐브
    doc_width = 50
    doc_height = 60
    doc_depth = 20
    
    # 큐브 시작점
    base_x = center - doc_width // 2
    base_y = center - doc_height // 2
    
    # 정면 (밝은 회색)
    front_points = [
        (base_x, base_y),
        (base_x + doc_width, base_y),
        (base_x + doc_width, base_y + doc_height),
        (base_x, base_y + doc_height)
    ]
    draw.polygon(front_points, fill=(240, 240, 245, 255), outline=(200, 200, 210, 255), width=2)
    
    # 우측면 (중간 회색)  
    right_points = [
        (base_x + doc_width, base_y),
        (base_x + doc_width + doc_depth * 0.866, base_y - doc_depth * 0.5),
        (base_x + doc_width + doc_depth * 0.866, base_y + doc_height - doc_depth * 0.5),
        (base_x + doc_width, base_y + doc_height)
    ]
    draw.polygon(right_points, fill=(200, 200, 210, 255), outline=(160, 160, 170, 255), width=2)
    
    # 윗면 (가장 밝은 회색)
    top_points = [
        (base_x, base_y),
        (base_x + doc_depth * 0.866, base_y - doc_depth * 0.5),
        (base_x + doc_width + doc_depth * 0.866, base_y - doc_depth * 0.5),
        (base_x + doc_width, base_y)
    ]
    draw.polygon(top_points, fill=(250, 250, 255, 255), outline=(220, 220, 230, 255), width=2)
    
    # 정면에 OCR 텍스트 라인들 (3D 효과)
    for i in range(6):
        line_y = base_y + 15 + (i * 7)
        line_width = doc_width - 20 - (i % 2) * 10
        
        # 메인 라인
        draw.rectangle([base_x + 10, line_y, base_x + 10 + line_width, line_y + 3], 
                      fill=(80, 120, 200, 255))
        
        # 3D 그림자 효과
        shadow_offset = 2
        draw.rectangle([base_x + 10 + shadow_offset, line_y + shadow_offset, 
                       base_x + 10 + line_width + shadow_offset, line_y + 3 + shadow_offset], 
                      fill=(40, 60, 100, 100))
    
    # 3D 스캔 빔 효과
    beam_start_x = base_x - 30
    beam_start_y = base_y + doc_height // 2
    beam_end_x = base_x + doc_width + 30
    beam_end_y = base_y + doc_height // 2
    
    # 스캔 빔 (그라데이션)
    for i in range(5):
        alpha = 150 - i * 20
        beam_width = 8 - i
        
        draw.line([beam_start_x, beam_start_y + i, beam_end_x, beam_end_y + i], 
                 fill=(255, 255, 100, alpha), width=beam_width)
    
    # 3D 스캔 포인터들
    for i in range(3):
        pointer_x = base_x + (i + 1) * doc_width // 4
        pointer_y = beam_start_y - 15
        
        # 3D 포인터 큐브
        pointer_points = [
            (pointer_x, pointer_y),
            (pointer_x + 6, pointer_y),
            (pointer_x + 8, pointer_y - 3),
            (pointer_x + 2, pointer_y - 3)
        ]
        draw.polygon(pointer_points, fill=(255, 100, 100, 255), outline=(200, 50, 50, 255))
    
    return img

def create_all_ultra_trendy_icons():
    """🔥 2024 초트렌디 아이콘 3종 생성"""
    
    print("🔥 2024 Ultra Trendy OCR 아이콘 생성 중...")
    print("💎 최신 디자인 사조 반영: Glassmorphism, Y2K Retrofuturism, 3D Isometric")
    
    # 스타일 1: Glassmorphism  
    print("\n🔮 생성 중: Glassmorphism...")
    icon1 = create_glassmorphism_icon()
    icon1.save('app_icon_glassmorphism.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    icon1.save('app_icon_glassmorphism.png', format='PNG')
    print("✅ Glassmorphism 완료: 반투명 유리 효과의 초세련 프리미엄 디자인")
    
    # 스타일 2: Y2K Retrofuturism
    print("\n🌈 생성 중: Y2K Retrofuturism...")
    icon2 = create_y2k_holographic_icon()
    icon2.save('app_icon_y2k_retro.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    icon2.save('app_icon_y2k_retro.png', format='PNG')
    print("✅ Y2K Retrofuturism 완료: 홀로그램 크롬 효과의 사이버펑크 스타일")
    
    # 스타일 3: 3D Isometric
    print("\n🎲 생성 중: 3D Isometric...")
    icon3 = create_3d_isometric_icon()
    icon3.save('app_icon_3d_isometric.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    icon3.save('app_icon_3d_isometric.png', format='PNG')
    print("✅ 3D Isometric 완료: 입체적 아이소메트릭 게임풍 디자인")
    
    print("\n🎉 Ultra Trendy 아이콘 3종 완성!")
    print("📱 각 스타일별 특징:")
    print("🔮 Glassmorphism: iOS/macOS 스타일 고급스러운 반투명 유리 효과")
    print("🌈 Y2K Retro: TikTok/Instagram 핫한 홀로그램 사이버펑크 스타일") 
    print("🎲 3D Isometric: Discord/Figma 스타일 입체적 게임풍 디자인")
    print("\n📁 .ico와 .png 파일이 모두 생성되었습니다!")

if __name__ == "__main__":
    create_all_ultra_trendy_icons() 