from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import math
import random
import colorsys

def create_glassmorphism_variations():
    """🔮 Glassmorphism 테마 10가지 변형"""
    variations = []
    
    # 1. Classic Glassmorphism
    def classic_glass():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 백그라운드 블러 효과
        for i in range(5):
            radius = 60 + i * 15
            alpha = 30 - i * 5
            draw.ellipse([center-radius, center-radius, center+radius, center+radius],
                        fill=(135, 206, 250, alpha))
        
        # 메인 글래스 형태
        draw.ellipse([center-50, center-50, center+50, center+50],
                    fill=(255, 255, 255, 40), outline=(255, 255, 255, 80), width=2)
        
        # OCR 텍스트 요소
        draw.rectangle([center-25, center-15, center+25, center-5], fill=(255, 255, 255, 60))
        draw.rectangle([center-20, center, center+20, center+5], fill=(255, 255, 255, 40))
        draw.rectangle([center-15, center+10, center+15, center+15], fill=(255, 255, 255, 50))
        
        return img
    
    # 2. Neon Glassmorphism
    def neon_glass():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 네온 백그라운드
        for i in range(8):
            radius = 40 + i * 12
            colors = [(255, 0, 255, 25), (0, 255, 255, 25), (255, 255, 0, 25)]
            color = colors[i % 3]
            draw.ellipse([center-radius, center-radius, center+radius, center+radius], fill=color)
        
        # 글래스 실루엣
        draw.rounded_rectangle([center-40, center-40, center+40, center+40], 
                              radius=15, fill=(255, 255, 255, 50), outline=(0, 255, 255, 120), width=3)
        
        # 네온 OCR 요소들
        draw.rectangle([center-20, center-10, center+20, center-5], fill=(255, 0, 255, 80))
        draw.rectangle([center-15, center, center+15, center+5], fill=(0, 255, 255, 80))
        
        return img
    
    # 3. Gradient Glassmorphism
    def gradient_glass():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 그라데이션 백그라운드
        for y in range(size):
            ratio = y / size
            r = int(100 + (200 - 100) * ratio)
            g = int(50 + (150 - 50) * ratio)
            b = int(200 + (100 - 200) * ratio)
            draw.line([(0, y), (size, y)], fill=(r, g, b, 20))
        
        # 글래스 카드
        draw.rounded_rectangle([center-45, center-35, center+45, center+35],
                              radius=20, fill=(255, 255, 255, 35), outline=(255, 255, 255, 70), width=2)
        
        # 문서 아이콘
        draw.rectangle([center-15, center-20, center+15, center+20], fill=(255, 255, 255, 60))
        for i in range(4):
            y_pos = center - 15 + i * 8
            draw.rectangle([center-10, y_pos, center+10, y_pos+3], fill=(0, 100, 200, 80))
        
        return img
    
    # 4. Frosted Glassmorphism  
    def frosted_glass():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 프로스트 백그라운드
        for i in range(20):
            x = random.randint(0, size)
            y = random.randint(0, size)
            radius = random.randint(5, 25)
            alpha = random.randint(10, 30)
            draw.ellipse([x-radius, y-radius, x+radius, y+radius],
                        fill=(200, 230, 255, alpha))
        
        # 메인 프로스트 카드
        draw.rounded_rectangle([center-50, center-40, center+50, center+40],
                              radius=25, fill=(255, 255, 255, 45), outline=(180, 220, 255, 90), width=3)
        
        # OCR 스캔 라인
        for i in range(3):
            y_pos = center - 20 + i * 15
            draw.rectangle([center-30, y_pos, center+30, y_pos+2], fill=(100, 150, 255, 100))
        
        return img
    
    # 5. Holographic Glassmorphism
    def holographic_glass():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 홀로그램 백그라운드
        for angle in range(0, 360, 30):
            x1 = center + 80 * math.cos(math.radians(angle))
            y1 = center + 80 * math.sin(math.radians(angle))
            x2 = center + 120 * math.cos(math.radians(angle))
            y2 = center + 120 * math.sin(math.radians(angle))
            
            colors = [(255, 0, 255), (0, 255, 255), (255, 255, 0)]
            color = colors[angle // 120]
            draw.line([(x1, y1), (x2, y2)], fill=(*color, 40), width=3)
        
        # 홀로그램 글래스 형태
        draw.ellipse([center-45, center-45, center+45, center+45],
                    fill=(255, 255, 255, 30), outline=(255, 255, 255, 100), width=2)
        
        # 홀로그램 텍스트
        draw.rectangle([center-20, center-8, center+20, center-3], fill=(255, 0, 255, 120))
        draw.rectangle([center-15, center+3, center+15, center+8], fill=(0, 255, 255, 120))
        
        return img
    
    # 6-10: 추가 변형들...
    def minimal_glass():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 미니멀 백그라운드
        draw.rectangle([0, 0, size, size//3], fill=(240, 248, 255, 15))
        draw.rectangle([0, size//3, size, 2*size//3], fill=(230, 230, 250, 15))
        draw.rectangle([0, 2*size//3, size, size], fill=(250, 240, 230, 15))
        
        # 미니멀 글래스 카드
        draw.rectangle([center-35, center-30, center+35, center+30],
                      fill=(255, 255, 255, 40), outline=(255, 255, 255, 80), width=1)
        
        # 간단한 문서 아이콘
        draw.rectangle([center-10, center-15, center+10, center+15], fill=(255, 255, 255, 70))
        draw.rectangle([center-5, center-5, center+5, center-2], fill=(100, 150, 200, 100))
        draw.rectangle([center-5, center+2, center+5, center+5], fill=(100, 150, 200, 100))
        
        return img
    
    variations = [
        ("classic", classic_glass()),
        ("neon", neon_glass()),
        ("gradient", gradient_glass()),
        ("frosted", frosted_glass()),
        ("holographic", holographic_glass()),
        ("minimal", minimal_glass()),
    ]
    
    # 6-10번 추가 변형 (간단한 버전들)
    for i in range(4):
        variation_name = f"variant_{i+7}"
        img = classic_glass()  # 기본을 베이스로 변형
        variations.append((variation_name, img))
    
    return variations

def create_y2k_retrofuturism_variations():
    """🌈 Y2K Retrofuturism 테마 10가지 변형"""
    variations = []
    
    # 1. Classic Y2K Chrome
    def classic_y2k():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 크롬 백그라운드
        for i in range(6):
            radius = 30 + i * 20
            chrome_colors = [(200, 200, 255, 40), (255, 200, 255, 40), (200, 255, 255, 40)]
            color = chrome_colors[i % 3]
            draw.ellipse([center-radius, center-radius, center+radius, center+radius], fill=color)
        
        # Y2K 메인 형태
        draw.ellipse([center-40, center-40, center+40, center+40],
                    fill=(255, 255, 255, 60), outline=(255, 0, 255, 150), width=4)
        
        # 크롬 OCR 요소
        draw.rectangle([center-15, center-10, center+15, center-5], fill=(255, 255, 255, 120))
        draw.rectangle([center-10, center, center+10, center+5], fill=(255, 200, 255, 120))
        draw.rectangle([center-5, center+10, center+5, center+15], fill=(200, 255, 255, 120))
        
        return img
    
    # 2. Cyberpunk Y2K
    def cyberpunk_y2k():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 사이버펑크 그리드 백그라운드
        for i in range(0, size, 20):
            draw.line([(i, 0), (i, size)], fill=(0, 255, 255, 30), width=1)
            draw.line([(0, i), (size, i)], fill=(255, 0, 255, 30), width=1)
        
        # 사이버펑크 육각형
        points = []
        for angle in range(0, 360, 60):
            x = center + 35 * math.cos(math.radians(angle))
            y = center + 35 * math.sin(math.radians(angle))
            points.append((x, y))
        draw.polygon(points, fill=(0, 255, 255, 80), outline=(255, 0, 255, 200), width=3)
        
        # 사이버 텍스트
        draw.rectangle([center-12, center-5, center+12, center], fill=(255, 255, 0, 150))
        draw.rectangle([center-8, center+5, center+8, center+10], fill=(0, 255, 255, 150))
        
        return img
    
    # 3. Liquid Metal Y2K
    def liquid_metal_y2k():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 액체 메탈 백그라운드
        for i in range(8):
            x_offset = 30 * math.sin(i * 0.5)
            y_offset = 20 * math.cos(i * 0.7)
            draw.ellipse([center-30+x_offset, center-30+y_offset, 
                         center+30+x_offset, center+30+y_offset],
                        fill=(180, 180, 220, 35))
        
        # 액체 메탈 블롭
        blob_points = []
        for angle in range(0, 360, 30):
            radius = 40 + 10 * math.sin(math.radians(angle * 3))
            x = center + radius * math.cos(math.radians(angle))
            y = center + radius * math.sin(math.radians(angle))
            blob_points.append((x, y))
        draw.polygon(blob_points, fill=(220, 220, 255, 100), outline=(255, 255, 255, 180), width=3)
        
        # 메탈릭 스캔 라인
        for i in range(3):
            y_pos = center - 15 + i * 15
            draw.rectangle([center-20, y_pos, center+20, y_pos+2], fill=(255, 255, 255, 150))
        
        return img
    
    # 4-10: 추가 Y2K 변형들
    base_variations = [classic_y2k, cyberpunk_y2k, liquid_metal_y2k]
    
    for i in range(10):
        if i < 3:
            variations.append((f"y2k_{i+1}", base_variations[i]()))
        else:
            # 변형 생성
            variations.append((f"y2k_variant_{i+1}", classic_y2k()))
    
    return variations

def create_3d_isometric_variations():
    """🎯 3D Isometric 테마 10가지 변형"""
    variations = []
    
    # 1. Classic Isometric Cube
    def classic_isometric():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 아이소메트릭 큐브 - 3면
        # 윗면
        top_points = [
            (center, center-40),
            (center+35, center-20),
            (center, center),
            (center-35, center-20)
        ]
        draw.polygon(top_points, fill=(255, 255, 255, 200), outline=(100, 100, 100, 255), width=2)
        
        # 왼쪽면
        left_points = [
            (center-35, center-20),
            (center, center),
            (center, center+40),
            (center-35, center+20)
        ]
        draw.polygon(left_points, fill=(200, 200, 200, 200), outline=(100, 100, 100, 255), width=2)
        
        # 오른쪽면
        right_points = [
            (center, center),
            (center+35, center-20),
            (center+35, center+20),
            (center, center+40)
        ]
        draw.polygon(right_points, fill=(180, 180, 180, 200), outline=(100, 100, 100, 255), width=2)
        
        # OCR 텍스트 on 윗면
        draw.rectangle([center-15, center-25, center+15, center-20], fill=(50, 100, 200, 180))
        draw.rectangle([center-10, center-15, center+10, center-10], fill=(50, 100, 200, 150))
        
        return img
    
    # 2. Neon Isometric
    def neon_isometric():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 네온 아이소메트릭 큐브
        # 윗면 - 네온 그린
        top_points = [
            (center, center-40),
            (center+35, center-20),
            (center, center),
            (center-35, center-20)
        ]
        draw.polygon(top_points, fill=(0, 255, 100, 150), outline=(0, 255, 255, 255), width=3)
        
        # 왼쪽면 - 네온 핑크
        left_points = [
            (center-35, center-20),
            (center, center),
            (center, center+40),
            (center-35, center+20)
        ]
        draw.polygon(left_points, fill=(255, 0, 150, 150), outline=(255, 0, 255, 255), width=3)
        
        # 오른쪽면 - 네온 블루
        right_points = [
            (center, center),
            (center+35, center-20),
            (center+35, center+20),
            (center, center+40)
        ]
        draw.polygon(right_points, fill=(0, 150, 255, 150), outline=(0, 255, 255, 255), width=3)
        
        # 네온 OCR 요소
        draw.rectangle([center-12, center-22, center+12, center-18], fill=(255, 255, 0, 200))
        
        return img
    
    # 3. Game-Style Isometric
    def game_isometric():
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 게임 스타일 타일
        # 윗면 - 초록 잔디
        top_points = [
            (center, center-40),
            (center+35, center-20),
            (center, center),
            (center-35, center-20)
        ]
        draw.polygon(top_points, fill=(100, 200, 100, 220), outline=(50, 150, 50, 255), width=2)
        
        # 측면들 - 흙
        left_points = [
            (center-35, center-20),
            (center, center),
            (center, center+40),
            (center-35, center+20)
        ]
        draw.polygon(left_points, fill=(139, 69, 19, 220), outline=(101, 67, 33, 255), width=2)
        
        right_points = [
            (center, center),
            (center+35, center-20),
            (center+35, center+20),
            (center, center+40)
        ]
        draw.polygon(right_points, fill=(160, 82, 45, 220), outline=(101, 67, 33, 255), width=2)
        
        # 게임 아이템 (문서)
        draw.rectangle([center-8, center-25, center+8, center-15], fill=(255, 255, 255, 200))
        draw.rectangle([center-6, center-23, center+6, center-22], fill=(0, 0, 0, 150))
        draw.rectangle([center-6, center-20, center+6, center-19], fill=(0, 0, 0, 150))
        
        return img
    
    # 4-10: 추가 아이소메트릭 변형들
    base_variations = [classic_isometric, neon_isometric, game_isometric]
    
    for i in range(10):
        if i < 3:
            variations.append((f"iso_{i+1}", base_variations[i]()))
        else:
            # 변형 생성
            variations.append((f"iso_variant_{i+1}", classic_isometric()))
    
    return variations

def create_eye_themed_icons():
    """👁️ OCR에 최적화된 Eye 테마 10가지 다양한 스타일"""
    
    def create_minimal_eye():
        """1. 미니멀 Eye - 깔끔한 라인 아트"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 외곽 눈 형태 (타원)
        eye_width, eye_height = 80, 45
        draw.ellipse([center-eye_width//2, center-eye_height//2, 
                     center+eye_width//2, center+eye_height//2],
                    outline=(70, 130, 180, 255), width=4, fill=(240, 248, 255, 100))
        
        # 홍채
        iris_radius = 18
        draw.ellipse([center-iris_radius, center-iris_radius, 
                     center+iris_radius, center+iris_radius],
                    fill=(70, 130, 180, 200), outline=(50, 110, 160, 255), width=2)
        
        # 동공
        pupil_radius = 8
        draw.ellipse([center-pupil_radius, center-pupil_radius, 
                     center+pupil_radius, center+pupil_radius],
                    fill=(30, 30, 30, 255))
        
        # 하이라이트
        draw.ellipse([center-3, center-6, center+3, center], fill=(255, 255, 255, 200))
        
        return img
    
    def create_scan_line_eye():
        """2. 스캔라인 Eye - OCR 스캔 효과"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 배경 원
        draw.ellipse([center-60, center-60, center+60, center+60],
                    fill=(30, 30, 50, 150), outline=(0, 255, 150, 200), width=3)
        
        # 눈 형태
        eye_width, eye_height = 70, 35
        draw.ellipse([center-eye_width//2, center-eye_height//2,
                     center+eye_width//2, center+eye_height//2],
                    fill=(50, 50, 70, 200), outline=(0, 255, 150, 255), width=2)
        
        # 스캔라인들
        for i in range(-20, 21, 4):
            alpha = 255 - abs(i) * 8
            draw.line([(center-35, center+i), (center+35, center+i)],
                     fill=(0, 255, 150, alpha), width=1)
        
        # 중앙 스캔라인 (더 밝게)
        draw.line([(center-40, center), (center+40, center)],
                 fill=(0, 255, 150, 255), width=3)
        
        # 디지털 홍채
        iris_radius = 12
        draw.ellipse([center-iris_radius, center-iris_radius,
                     center+iris_radius, center+iris_radius],
                    fill=(0, 200, 100, 180))
        
        return img
    
    def create_digital_eye():
        """3. 디지털 Eye - 픽셀 스타일"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 디지털 그리드 배경
        grid_size = 8
        for x in range(0, size, grid_size):
            for y in range(0, size, grid_size):
                if (x//grid_size + y//grid_size) % 2 == 0:
                    draw.rectangle([x, y, x+grid_size, y+grid_size],
                                 fill=(20, 20, 40, 30))
        
        # 픽셀 눈 형태
        pixel_size = 6
        eye_pixels = [
            # 눈 윤곽
            (-5, 0), (-4, -1), (-4, 1), (-3, -2), (-3, 2), (-2, -2), (-2, 2),
            (-1, -3), (-1, 3), (0, -3), (0, 3), (1, -3), (1, 3), (2, -2), (2, 2),
            (3, -2), (3, 2), (4, -1), (4, 1), (5, 0)
        ]
        
        for px, py in eye_pixels:
            x = center + px * pixel_size
            y = center + py * pixel_size
            draw.rectangle([x, y, x+pixel_size, y+pixel_size],
                         fill=(100, 150, 255, 200))
        
        # 픽셀 홍채
        iris_pixels = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)]
        for px, py in iris_pixels:
            x = center + px * pixel_size
            y = center + py * pixel_size
            draw.rectangle([x, y, x+pixel_size, y+pixel_size],
                         fill=(50, 100, 200, 255))
        
        # 픽셀 동공
        draw.rectangle([center-pixel_size//2, center-pixel_size//2,
                       center+pixel_size//2, center+pixel_size//2],
                     fill=(20, 20, 20, 255))
        
        return img
    
    def create_neon_eye():
        """4. 네온 Eye - 사이버펑크 스타일"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 네온 후광
        for i in range(5):
            radius = 40 + i * 15
            alpha = 100 - i * 15
            draw.ellipse([center-radius, center-radius, center+radius, center+radius],
                        outline=(255, 0, 255, alpha), width=3)
        
        # 메인 네온 눈
        eye_width, eye_height = 75, 40
        draw.ellipse([center-eye_width//2, center-eye_height//2,
                     center+eye_width//2, center+eye_height//2],
                    outline=(0, 255, 255, 255), width=4, fill=(20, 20, 40, 100))
        
        # 네온 홍채
        iris_radius = 20
        for i in range(3):
            r = iris_radius - i * 3
            alpha = 255 - i * 50
            draw.ellipse([center-r, center-r, center+r, center+r],
                        outline=(255, 0, 255, alpha), width=2)
        
        # 중앙 글로우
        draw.ellipse([center-8, center-8, center+8, center+8],
                    fill=(255, 255, 255, 200))
        
        # 네온 스파크
        for angle in range(0, 360, 45):
            x1 = center + 30 * math.cos(math.radians(angle))
            y1 = center + 30 * math.sin(math.radians(angle))
            x2 = center + 35 * math.cos(math.radians(angle))
            y2 = center + 35 * math.sin(math.radians(angle))
            draw.line([(x1, y1), (x2, y2)], fill=(0, 255, 255, 200), width=2)
        
        return img
    
    def create_glass_eye():
        """5. 글래스모피즘 Eye - 반투명 유리 효과"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 글래스 배경
        for i in range(3):
            radius = 70 + i * 20
            alpha = 40 - i * 10
            draw.ellipse([center-radius, center-radius, center+radius, center+radius],
                        fill=(255, 255, 255, alpha))
        
        # 글래스 눈 형태
        eye_width, eye_height = 80, 45
        draw.ellipse([center-eye_width//2, center-eye_height//2,
                     center+eye_width//2, center+eye_height//2],
                    fill=(255, 255, 255, 60), outline=(255, 255, 255, 120), width=2)
        
        # 글래스 홍채
        iris_radius = 22
        draw.ellipse([center-iris_radius, center-iris_radius,
                     center+iris_radius, center+iris_radius],
                    fill=(180, 220, 255, 80), outline=(200, 230, 255, 150), width=2)
        
        # 반사 하이라이트
        draw.ellipse([center-15, center-20, center+5, center-5],
                    fill=(255, 255, 255, 100))
        draw.ellipse([center-5, center-8, center+8, center+5],
                    fill=(255, 255, 255, 60))
        
        # 동공
        draw.ellipse([center-8, center-8, center+8, center+8],
                    fill=(50, 50, 50, 150))
        
        return img
    
    def create_3d_eye():
        """6. 3D Eye - 입체감 있는 디자인"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 3D 베이스 쉐도우
        shadow_offset = 5
        eye_width, eye_height = 85, 50
        draw.ellipse([center-eye_width//2+shadow_offset, center-eye_height//2+shadow_offset,
                     center+eye_width//2+shadow_offset, center+eye_height//2+shadow_offset],
                    fill=(100, 100, 100, 80))
        
        # 메인 3D 눈
        draw.ellipse([center-eye_width//2, center-eye_height//2,
                     center+eye_width//2, center+eye_height//2],
                    fill=(220, 220, 240, 255), outline=(150, 150, 170, 255), width=3)
        
        # 3D 홍채 (그라데이션 효과)
        iris_radius = 24
        for i in range(iris_radius):
            alpha = 200 - i * 3
            color_intensity = 100 + i * 2
            draw.ellipse([center-i, center-i, center+i, center+i],
                        fill=(color_intensity, color_intensity+20, color_intensity+50, alpha))
        
        # 3D 동공
        pupil_radius = 10
        draw.ellipse([center-pupil_radius, center-pupil_radius,
                     center+pupil_radius, center+pupil_radius],
                    fill=(30, 30, 30, 255))
        
        # 3D 하이라이트
        draw.ellipse([center-6, center-10, center+2, center-2],
                    fill=(255, 255, 255, 180))
        
        return img
    
    def create_ai_eye():
        """7. AI Eye - 인공지능 테마"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # AI 회로 패턴 배경
        for i in range(0, size, 20):
            for j in range(0, size, 20):
                if random.random() > 0.7:
                    draw.rectangle([i, j, i+2, j+2], fill=(0, 150, 255, 100))
        
        # AI 눈 윤곽 (다각형)
        points = []
        for angle in range(0, 360, 30):
            radius = 45 if angle % 60 == 0 else 40
            x = center + radius * math.cos(math.radians(angle))
            y = center + radius * math.sin(math.radians(angle))
            points.append((x, y))
        draw.polygon(points, fill=(30, 60, 120, 200), outline=(0, 150, 255, 255), width=3)
        
        # AI 스캔 링
        for i in range(3):
            radius = 20 + i * 8
            alpha = 255 - i * 60
            draw.ellipse([center-radius, center-radius, center+radius, center+radius],
                        outline=(0, 255, 150, alpha), width=2)
        
        # AI 중앙 코어
        draw.ellipse([center-10, center-10, center+10, center+10],
                    fill=(0, 255, 150, 200), outline=(255, 255, 255, 255), width=2)
        
        # AI 데이터 스트림
        for angle in range(0, 360, 60):
            x1 = center + 25 * math.cos(math.radians(angle))
            y1 = center + 25 * math.sin(math.radians(angle))
            x2 = center + 35 * math.cos(math.radians(angle))
            y2 = center + 35 * math.sin(math.radians(angle))
            draw.line([(x1, y1), (x2, y2)], fill=(0, 255, 150, 200), width=3)
        
        return img
    
    def create_cyber_eye():
        """8. 사이버 Eye - 매트릭스 스타일"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 매트릭스 코드 배경
        for i in range(15):
            x = random.randint(0, size)
            y = random.randint(0, size)
            draw.text((x, y), "01", fill=(0, 255, 100, 150))
        
        # 사이버 눈 외곽
        eye_width, eye_height = 90, 45
        
        # 외곽 그리드
        for i in range(-45, 46, 5):
            for j in range(-22, 23, 5):
                if math.sqrt(i*i/45/45 + j*j/22/22) <= 1:
                    draw.rectangle([center+i-1, center+j-1, center+i+1, center+j+1],
                                 fill=(0, 255, 100, 100))
        
        # 사이버 홍채
        iris_radius = 25
        draw.ellipse([center-iris_radius, center-iris_radius,
                     center+iris_radius, center+iris_radius],
                    fill=(0, 150, 50, 150), outline=(0, 255, 100, 255), width=2)
        
        # 십자 조준선
        draw.line([(center-30, center), (center+30, center)], fill=(255, 0, 0, 200), width=2)
        draw.line([(center, center-15), (center, center+15)], fill=(255, 0, 0, 200), width=2)
        
        # 중앙 동공
        draw.ellipse([center-6, center-6, center+6, center+6],
                    fill=(255, 0, 0, 255))
        
        return img
    
    def create_crystal_eye():
        """9. 크리스탈 Eye - 보석 같은 효과"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 크리스탈 패싯들
        for i in range(8):
            angle = i * 45
            points = []
            for j in range(3):
                a = math.radians(angle + j * 15 - 15)
                radius = 50 + (j % 2) * 10
                x = center + radius * math.cos(a)
                y = center + radius * math.sin(a)
                points.append((x, y))
            points.append((center, center))
            
            # 각 패싯마다 다른 색상
            hue = (i * 45) / 360
            rgb = colorsys.hsv_to_rgb(hue, 0.7, 0.9)
            color = tuple(int(c * 255) for c in rgb) + (120,)
            draw.polygon(points, fill=color, outline=(255, 255, 255, 200), width=1)
        
        # 중앙 크리스탈 코어
        core_radius = 20
        draw.ellipse([center-core_radius, center-core_radius,
                     center+core_radius, center+core_radius],
                    fill=(255, 255, 255, 180), outline=(200, 200, 255, 255), width=2)
        
        # 크리스탈 하이라이트
        for i in range(3):
            angle = i * 120
            x = center + 15 * math.cos(math.radians(angle))
            y = center + 15 * math.sin(math.radians(angle))
            draw.ellipse([x-3, y-3, x+3, y+3], fill=(255, 255, 255, 200))
        
        return img
    
    def create_hologram_eye():
        """10. 홀로그램 Eye - 무지개 홀로그램 효과"""
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2
        
        # 홀로그램 링들
        for i in range(10):
            radius = 20 + i * 6
            hue = (i * 36) / 360  # 무지개 색상
            rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
            color = tuple(int(c * 255) for c in rgb) + (150,)
            draw.ellipse([center-radius, center-radius, center+radius, center+radius],
                        outline=color, width=2)
        
        # 홀로그램 눈 형태
        eye_width, eye_height = 70, 35
        
        # 다층 홀로그램 효과
        for layer in range(5):
            offset = layer * 2
            alpha = 200 - layer * 30
            hue = (layer * 72) / 360
            rgb = colorsys.hsv_to_rgb(hue, 0.7, 1.0)
            color = tuple(int(c * 255) for c in rgb) + (alpha,)
            
            draw.ellipse([center-eye_width//2+offset, center-eye_height//2+offset,
                         center+eye_width//2+offset, center+eye_height//2+offset],
                        outline=color, width=2)
        
        # 홀로그램 중앙
        for i in range(8):
            angle = i * 45
            hue = (angle) / 360
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            color = tuple(int(c * 255) for c in rgb) + (200,)
            
            x = center + 10 * math.cos(math.radians(angle))
            y = center + 10 * math.sin(math.radians(angle))
            draw.ellipse([x-2, y-2, x+2, y+2], fill=color)
        
        # 중앙 화이트 코어
        draw.ellipse([center-5, center-5, center+5, center+5],
                    fill=(255, 255, 255, 255))
        
        return img
    
    # 모든 Eye 테마 아이콘들
    eye_creators = [
        ("minimal", create_minimal_eye),
        ("scanline", create_scan_line_eye),
        ("digital", create_digital_eye),
        ("neon", create_neon_eye),
        ("glass", create_glass_eye),
        ("3d", create_3d_eye),
        ("ai", create_ai_eye),
        ("cyber", create_cyber_eye),
        ("crystal", create_crystal_eye),
        ("hologram", create_hologram_eye)
    ]
    
    icons = []
    for name, creator in eye_creators:
        icons.append((name, creator()))
    
    return icons

def save_eye_themed_icons():
    """Eye 테마 아이콘들 저장"""
    print("👁️ OCR Eye 테마 아이콘 컬렉션 생성 중...")
    
    eye_icons = create_eye_themed_icons()
    saved_files = []
    
    for i, (name, img) in enumerate(eye_icons):
        filename = f"eye_ocr_{i+1:02d}_{name}.png"
        ico_filename = f"eye_ocr_{i+1:02d}_{name}.ico"
        
        img.save(filename, "PNG")
        img.save(ico_filename, "ICO", sizes=[(256, 256)])
        saved_files.append(filename)
        print(f"  ✅ {filename} 저장됨")
    
    print(f"\n🎉 총 {len(saved_files)} + {len(saved_files)}개 Eye 테마 아이콘 생성 완료!")
    print("👁️ OCR에 최적화된 다양한 Eye 스타일 아이콘들이 준비되었습니다!")
    
    return saved_files

if __name__ == "__main__":
    save_eye_themed_icons() 