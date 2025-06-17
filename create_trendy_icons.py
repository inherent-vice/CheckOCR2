from PIL import Image, ImageDraw, ImageFilter
import math

def create_icon_style1_modern_gradient():
    """스타일 1: 모던 그라데이션 - 파란색에서 보라색으로 그라데이션되는 세련된 디자인"""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 그라데이션 배경 원 만들기
    center = size // 2
    radius = size // 2 - 20
    
    # 그라데이션 효과를 위한 여러 원 그리기
    for i in range(radius):
        # 파란색(#4A90E2)에서 보라색(#8E44AD)으로 그라데이션
        ratio = i / radius
        r = int(74 + (142 - 74) * ratio)
        g = int(144 + (68 - 144) * ratio)
        b = int(226 + (173 - 226) * ratio)
        
        current_radius = radius - i
        alpha = int(255 * (0.8 + 0.2 * (1 - ratio)))
        
        draw.ellipse([center - current_radius, center - current_radius, 
                     center + current_radius, center + current_radius], 
                    fill=(r, g, b, alpha))
    
    # 세련된 AI/스캔 심볼 - 기하학적 형태
    # 중앙에 세련된 문서 스캔 라인들
    line_width = 4
    line_spacing = 12
    start_x = center - 40
    end_x = center + 40
    
    for i in range(6):
        y_pos = center - 30 + (i * line_spacing)
        line_alpha = 255 - (i * 20)  # 점점 투명해지는 효과
        length_offset = i * 5  # 길이가 점점 짧아지는 효과
        
        draw.rectangle([start_x + length_offset, y_pos, 
                       end_x - length_offset, y_pos + line_width], 
                      fill=(255, 255, 255, line_alpha))
    
    # 스캔 레이저 효과
    scan_y = center + 10
    draw.rectangle([start_x - 10, scan_y, end_x + 10, scan_y + 2], 
                  fill=(255, 255, 255, 255))
    
    return img

def create_icon_style2_neon_glow():
    """스타일 2: 네온 글로우 - 사이버펑크 느낌의 네온 효과"""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    
    # 어두운 배경 원
    radius = size // 2 - 15
    draw.ellipse([center - radius, center - radius, center + radius, center + radius], 
                fill=(20, 20, 30, 255))
    
    # 네온 외곽선 효과 (여러겹)
    for i in range(5):
        glow_radius = radius + i * 2
        alpha = 100 - (i * 15)
        draw.ellipse([center - glow_radius, center - glow_radius, 
                     center + glow_radius, center + glow_radius], 
                    outline=(0, 255, 200, alpha), width=2)
    
    # 중앙 홀로그램 텍스트 효과
    # 네온 그린 컬러 사용
    neon_color = (0, 255, 150, 255)
    
    # 홀로그램 스타일 텍스트 라인들
    line_width = 3
    for i in range(8):
        y_pos = center - 50 + (i * 12)
        line_length = 60 - abs(i - 3.5) * 8  # 중앙이 가장 긴 다이아몬드 형태
        start_x = center - line_length // 2
        end_x = center + line_length // 2
        
        # 메인 라인
        draw.rectangle([start_x, y_pos, end_x, y_pos + line_width], fill=neon_color)
        
        # 글로우 효과
        draw.rectangle([start_x - 1, y_pos - 1, end_x + 1, y_pos + line_width + 1], 
                      outline=(0, 255, 150, 100), width=1)
    
    # 네온 스캔 포인트들
    for i in range(3):
        point_x = center - 30 + (i * 30)
        point_y = center + 40
        point_radius = 3
        
        # 메인 포인트
        draw.ellipse([point_x - point_radius, point_y - point_radius, 
                     point_x + point_radius, point_y + point_radius], 
                    fill=neon_color)
        
        # 글로우 링
        for j in range(3):
            glow_r = point_radius + j * 2
            alpha = 80 - (j * 20)
            draw.ellipse([point_x - glow_r, point_y - glow_r, 
                         point_x + glow_r, point_y + glow_r], 
                        outline=(0, 255, 150, alpha), width=1)
    
    return img

def create_icon_style3_minimal_geometric():
    """스타일 3: 미니멀 기하학적 - 깔끔하고 현대적인 기하학적 디자인"""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    
    # 깔끔한 원형 배경 (소프트한 그라데이션)
    radius = size // 2 - 25
    
    # 소프트한 색상 조합 (연한 청록색)
    base_color = (64, 196, 255)  # 밝은 청록색
    
    for i in range(radius):
        ratio = i / radius
        alpha = int(255 * (0.9 - ratio * 0.3))  # 중앙이 더 진하고 바깥으로 갈수록 투명
        brightness = 1 - ratio * 0.3
        
        r = int(base_color[0] * brightness)
        g = int(base_color[1] * brightness)
        b = int(base_color[2] * brightness)
        
        current_radius = radius - i
        draw.ellipse([center - current_radius, center - current_radius, 
                     center + current_radius, center + current_radius], 
                    fill=(r, g, b, alpha))
    
    # 기하학적 문서 아이콘 (육각형 기반)
    # 육각형 문서 모양
    hex_size = 35
    hex_center_y = center - 10
    
    # 육각형 좌표 계산
    hex_points = []
    for i in range(6):
        angle = i * math.pi / 3
        x = center + hex_size * math.cos(angle)
        y = hex_center_y + hex_size * math.sin(angle)
        hex_points.append((x, y))
    
    # 육각형 그리기 (화이트)
    draw.polygon(hex_points, fill=(255, 255, 255, 240), outline=(200, 200, 200, 255), width=2)
    
    # 내부 데이터 시각화 (점선 패턴)
    for i in range(4):
        y_pos = hex_center_y - 15 + (i * 8)
        dots_count = 5 - i % 2  # 지그재그 패턴
        
        for j in range(dots_count):
            dot_x = center - 12 + (j * 6)
            dot_radius = 2
            draw.ellipse([dot_x - dot_radius, y_pos - dot_radius, 
                         dot_x + dot_radius, y_pos + dot_radius], 
                        fill=(100, 100, 100, 200))
    
    # 하단에 세련된 스캔 바
    scan_bar_y = center + 35
    scan_bar_width = 80
    scan_bar_height = 6
    
    # 메인 스캔 바
    draw.rectangle([center - scan_bar_width//2, scan_bar_y, 
                   center + scan_bar_width//2, scan_bar_y + scan_bar_height], 
                  fill=(255, 255, 255, 220))
    
    # 움직이는 스캔 라인 효과
    scan_line_x = center - 10
    draw.rectangle([scan_line_x, scan_bar_y - 2, scan_line_x + 3, scan_bar_y + scan_bar_height + 2], 
                  fill=(64, 196, 255, 255))
    
    return img

def create_all_trendy_icons():
    """3가지 트렌디한 아이콘을 모두 생성"""
    
    print("🎨 트렌디한 OCR 아이콘 3종 생성 중...")
    
    # 스타일 1: 모던 그라데이션
    icon1 = create_icon_style1_modern_gradient()
    icon1.save('app_icon_style1_modern.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    icon1.save('app_icon_style1_modern.png', format='PNG')
    print("✅ 스타일 1 완료: 모던 그라데이션 (파일: app_icon_style1_modern)")
    
    # 스타일 2: 네온 글로우
    icon2 = create_icon_style2_neon_glow()
    icon2.save('app_icon_style2_neon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    icon2.save('app_icon_style2_neon.png', format='PNG')
    print("✅ 스타일 2 완료: 네온 글로우 (파일: app_icon_style2_neon)")
    
    # 스타일 3: 미니멀 기하학적
    icon3 = create_icon_style3_minimal_geometric()
    icon3.save('app_icon_style3_minimal.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    icon3.save('app_icon_style3_minimal.png', format='PNG')
    print("✅ 스타일 3 완료: 미니멀 기하학적 (파일: app_icon_style3_minimal)")
    
    print("\n🎉 3가지 트렌디한 아이콘이 모두 생성되었습니다!")
    print("📁 각 스타일별로 .ico와 .png 파일이 생성되었으니 미리보기하시고 선택해주세요.")
    print("\n스타일 설명:")
    print("1️⃣ 모던 그라데이션: 파란색→보라색 그라데이션의 세련된 현대적 디자인")
    print("2️⃣ 네온 글로우: 사이버펑크 스타일의 네온 효과와 홀로그램 느낌")
    print("3️⃣ 미니멀 기하학적: 깔끔하고 심플한 기하학적 패턴의 모던 디자인")

if __name__ == "__main__":
    create_all_trendy_icons() 