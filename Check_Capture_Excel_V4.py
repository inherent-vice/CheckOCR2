import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import pyperclip
import pyautogui
import time
import os
from PIL import Image
import numpy as np
import cv2
from paddleocr import PaddleOCR

############################################
# 드래그로 좌표를 지정하는 Overlay Window #
############################################
class DragCaptureOverlay(tk.Toplevel):
    """
    전 화면에 반투명 창을 띄워서
    마우스 드래그로 영역(x1, y1, x2, y2)을 지정할 수 있는 클래스.
    color: 드래그 박스 색상 (예: "red", "blue", "white")
    """
    def __init__(self, master=None, color="red"):
        super().__init__(master)
        self.master = master
        self.color = color

        # 전체 화면으로 만들기
        self.attributes("-fullscreen", True)
        # 항상 위에 표시
        self.attributes("-topmost", True)
        # 배경색 + 투명도 설정
        self.configure(bg="black")
        self.attributes("-alpha", 0.3)

        # 캔버스
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 드래그 시작점
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        

        # 이벤트 바인딩
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # 최종 좌표
        self.x1, self.y1, self.x2, self.y2 = None, None, None, None

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        # 사각형 초기화
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline=self.color, width=2
        )

    def on_move_press(self, event):
        # 마우스 드래그 중 갱신
        curX, curY = (event.x, event.y)
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, curX, curY)

    def on_button_release(self, event):
        # 드래그 끝
        end_x, end_y = (event.x, event.y)
        self.x1 = min(self.start_x, end_x)
        self.y1 = min(self.start_y, end_y)
        self.x2 = max(self.start_x, end_x)
        self.y2 = max(self.start_y, end_y)
        self.destroy()


############################################
# 포인터 한 번 클릭으로 좌표를 지정하는 Overlay
############################################
class PointCaptureOverlay(tk.Toplevel):
    """
    전 화면에 반투명 창을 띄워서
    마우스 한 번 클릭(x, y)을 지정할 수 있는 클래스.
    color: 마우스 클릭 시 표시할 점의 색상(옵션)
    """
    def __init__(self, master=None, color="red"):
        super().__init__(master)
        self.master = master
        self.color = color

        # 전체 화면으로 만들기
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        self.attributes("-alpha", 0.3)

        # 캔버스
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 최종 클릭좌표
        self.click_x = None
        self.click_y = None

        # 이벤트 바인딩
        self.canvas.bind("<ButtonPress-1>", self.on_click)

    def on_click(self, event):
        self.click_x = event.x
        self.click_y = event.y
        # 선택 지점을 간단히 표시(원)
        r = 5
        self.canvas.create_oval(
            self.click_x - r, self.click_y - r,
            self.click_x + r, self.click_y + r,
            fill=self.color, outline=self.color
        )
        # 클릭 완료 후 창 닫기
        self.destroy()


############################################
# 메인 GUI + OCR 로직이 결합된 코드
############################################
class CheckCaptureOCRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Check_Capture_OCR")

        # ===== 기본값 설정 =====
        self.input_excel_path = tk.StringVar()
        self.output_folder_path = tk.StringVar()

        # -- ClickPoint 기본값 --
        self.click_x = tk.IntVar(value=340)
        self.click_y = tk.IntVar(value=165)

        # -- AllArea 기본값 --
        self.allarea_x1 = tk.IntVar(value=15)
        self.allarea_y1 = tk.IntVar(value=200)
        self.allarea_x2 = tk.IntVar(value=15 + 1830)  # 1845
        self.allarea_y2 = tk.IntVar(value=200 + 670)  # 870

        # -- DateArea 기본값 --
        self.datearea_x1 = tk.IntVar(value=826)
        self.datearea_y1 = tk.IntVar(value=88)
        self.datearea_x2 = tk.IntVar(value=1064)
        self.datearea_y2 = tk.IntVar(value=127)

        # -- RateArea 기본값 --
        self.ratearea_x1 = tk.IntVar(value=1069)
        self.ratearea_y1 = tk.IntVar(value=89)
        self.ratearea_x2 = tk.IntVar(value=1326)
        self.ratearea_y2 = tk.IntVar(value=126)

        # -- 딜레이 기본값 --
        self.paste_delay = tk.DoubleVar(value=0.5)
        self.loading_delay = tk.DoubleVar(value=2.5)

        self._build_ui()

    def _build_ui(self):
        # 1) 엑셀 입력/출력 경로
        frm_excel = tk.Frame(self)
        frm_excel.pack(padx=5, pady=5, fill="x")

        # Input Excel
        lbl_in = tk.Label(frm_excel, text="Input_Excel")
        lbl_in.grid(row=0, column=0, sticky="w")
        ent_in = tk.Entry(frm_excel, textvariable=self.input_excel_path, width=50)
        ent_in.grid(row=0, column=1, padx=5)
        btn_in = tk.Button(frm_excel, text="Browse", command=self.browse_input_excel)
        btn_in.grid(row=0, column=2, padx=5)

        # Output
        lbl_out = tk.Label(frm_excel, text="Output")
        lbl_out.grid(row=1, column=0, sticky="w", pady=(5, 0))
        ent_out = tk.Entry(frm_excel, textvariable=self.output_folder_path, width=50)
        ent_out.grid(row=1, column=1, padx=5, pady=(5, 0))
        btn_out = tk.Button(frm_excel, text="Browse", command=self.browse_output_folder)
        btn_out.grid(row=1, column=2, padx=5, pady=(5, 0))

        # 2) ClickPoint
        frm_click = tk.Frame(self)
        frm_click.pack(padx=5, pady=5, fill="x")

        lbl_click = tk.Label(frm_click, text="ClickPoint (x, y)")
        lbl_click.grid(row=0, column=0, sticky="w")

        ent_click_x = tk.Entry(frm_click, textvariable=self.click_x, width=5)
        ent_click_x.grid(row=0, column=1)
        ent_click_y = tk.Entry(frm_click, textvariable=self.click_y, width=5)
        ent_click_y.grid(row=0, column=2)

        btn_click_reloc = tk.Button(frm_click, text="Relocate", command=self.relocate_clickpoint)
        btn_click_reloc.grid(row=0, column=3, padx=5)

        # 3) AllArea / DateArea / RateArea
        frm_area = tk.Frame(self)
        frm_area.pack(padx=5, pady=5, fill="x")

        # AllArea
        lbl_all = tk.Label(frm_area, text="AllArea (x1, y1, x2, y2)")
        lbl_all.grid(row=0, column=0, sticky="w")

        ent_all_x1 = tk.Entry(frm_area, textvariable=self.allarea_x1, width=5)
        ent_all_x1.grid(row=0, column=1)
        ent_all_y1 = tk.Entry(frm_area, textvariable=self.allarea_y1, width=5)
        ent_all_y1.grid(row=0, column=2)
        ent_all_x2 = tk.Entry(frm_area, textvariable=self.allarea_x2, width=5)
        ent_all_x2.grid(row=0, column=3)
        ent_all_y2 = tk.Entry(frm_area, textvariable=self.allarea_y2, width=5)
        ent_all_y2.grid(row=0, column=4)
        btn_all_reloc = tk.Button(frm_area, text="Relocate", command=self.relocate_allarea)
        btn_all_reloc.grid(row=0, column=5, padx=5)

        # DateArea
        lbl_date = tk.Label(frm_area, text="DateArea (x1, y1, x2, y2)")
        lbl_date.grid(row=1, column=0, sticky="w", pady=(5, 0))

        ent_date_x1 = tk.Entry(frm_area, textvariable=self.datearea_x1, width=5)
        ent_date_x1.grid(row=1, column=1, pady=(5, 0))
        ent_date_y1 = tk.Entry(frm_area, textvariable=self.datearea_y1, width=5)
        ent_date_y1.grid(row=1, column=2, pady=(5, 0))
        ent_date_x2 = tk.Entry(frm_area, textvariable=self.datearea_x2, width=5)
        ent_date_x2.grid(row=1, column=3, pady=(5, 0))
        ent_date_y2 = tk.Entry(frm_area, textvariable=self.datearea_y2, width=5)
        ent_date_y2.grid(row=1, column=4, pady=(5, 0))
        btn_date_reloc = tk.Button(frm_area, text="Relocate", command=self.relocate_datearea)
        btn_date_reloc.grid(row=1, column=5, padx=5, pady=(5, 0))

        # RateArea
        lbl_rate = tk.Label(frm_area, text="RateArea (x1, y1, x2, y2)")
        lbl_rate.grid(row=2, column=0, sticky="w", pady=(5, 0))

        ent_rate_x1 = tk.Entry(frm_area, textvariable=self.ratearea_x1, width=5)
        ent_rate_x1.grid(row=2, column=1, pady=(5, 0))
        ent_rate_y1 = tk.Entry(frm_area, textvariable=self.ratearea_y1, width=5)
        ent_rate_y1.grid(row=2, column=2, pady=(5, 0))
        ent_rate_x2 = tk.Entry(frm_area, textvariable=self.ratearea_x2, width=5)
        ent_rate_x2.grid(row=2, column=3, pady=(5, 0))
        ent_rate_y2 = tk.Entry(frm_area, textvariable=self.ratearea_y2, width=5)
        ent_rate_y2.grid(row=2, column=4, pady=(5, 0))
        btn_rate_reloc = tk.Button(frm_area, text="Relocate", command=self.relocate_ratearea)
        btn_rate_reloc.grid(row=2, column=5, padx=5, pady=(5, 0))

        # 4) 딜레이
        frm_delay = tk.Frame(self)
        frm_delay.pack(padx=5, pady=5, fill="x")

        lbl_paste = tk.Label(frm_delay, text="Paste_delay")
        lbl_paste.grid(row=0, column=0, sticky="w")
        ent_paste = tk.Entry(frm_delay, textvariable=self.paste_delay, width=5)
        ent_paste.grid(row=0, column=1, padx=(5, 15))

        lbl_load = tk.Label(frm_delay, text="Loading_delay")
        lbl_load.grid(row=0, column=2, sticky="w")
        ent_load = tk.Entry(frm_delay, textvariable=self.loading_delay, width=5)
        ent_load.grid(row=0, column=3, padx=(5, 15))

        # 실행 버튼
        btn_run = tk.Button(self, text="실행", command=self.run_ocr_process)
        btn_run.pack(pady=10)

    ######################
    # Browse 버튼 동작들 #
    ######################
    def browse_input_excel(self):
        file_path = filedialog.askopenfilename(
            title="엑셀 파일 선택",
            filetypes=[("Excel files", "*.xlsx;*.xls")]
        )
        if file_path:
            self.input_excel_path.set(file_path)
            # 선택된 엑셀 폴더를 기본 Output으로
            base_path = os.path.dirname(file_path)
            self.output_folder_path.set(base_path)

    def browse_output_folder(self):
        folder_path = filedialog.askdirectory(title="출력 폴더 선택")
        if folder_path:
            self.output_folder_path.set(folder_path)

    ##############################
    # Relocate(영역/포인트) 부분 #
    ##############################
    def relocate_clickpoint(self):
        """ClickPoint를 마우스 한 번으로 지정"""
        overlay = PointCaptureOverlay(self, color="red")
        self.wait_window(overlay)
        if overlay.click_x is not None:
            self.click_x.set(overlay.click_x)
            self.click_y.set(overlay.click_y)

    def relocate_allarea(self):
        overlay = DragCaptureOverlay(self, color="red")
        self.wait_window(overlay)
        if overlay.x1 is not None:
            self.allarea_x1.set(overlay.x1)
            self.allarea_y1.set(overlay.y1)
            self.allarea_x2.set(overlay.x2)
            self.allarea_y2.set(overlay.y2)

    def relocate_datearea(self):
        overlay = DragCaptureOverlay(self, color="blue")
        self.wait_window(overlay)
        if overlay.x1 is not None:
            self.datearea_x1.set(overlay.x1)
            self.datearea_y1.set(overlay.y1)
            self.datearea_x2.set(overlay.x2)
            self.datearea_y2.set(overlay.y2)

    def relocate_ratearea(self):
        overlay = DragCaptureOverlay(self, color="white")
        self.wait_window(overlay)
        if overlay.x1 is not None:
            self.ratearea_x1.set(overlay.x1)
            self.ratearea_y1.set(overlay.y1)
            self.ratearea_x2.set(overlay.x2)
            self.ratearea_y2.set(overlay.y2)

    ##############################
    # 실행 버튼 동작: OCR 로직
    ##############################
    def run_ocr_process(self):
        input_file = self.input_excel_path.get().strip()
        output_dir = self.output_folder_path.get().strip()
        if not input_file or not os.path.exists(input_file):
            messagebox.showwarning("경고", "유효한 Input Excel 파일 경로를 지정하세요.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showwarning("경고", "유효한 Output 폴더를 지정하세요.")
            return

        paste_d = self.paste_delay.get()
        load_d = self.loading_delay.get()

        # ClickPoint
        click_x = self.click_x.get()
        click_y = self.click_y.get()

        # AllArea (절대좌표)
        x1_all = self.allarea_x1.get()
        y1_all = self.allarea_y1.get()
        x2_all = self.allarea_x2.get()
        y2_all = self.allarea_y2.get()

        # DateArea (절대좌표)
        x1_date = self.datearea_x1.get()
        y1_date = self.datearea_y1.get()
        x2_date = self.datearea_x2.get()
        y2_date = self.datearea_y2.get()

        # RateArea (절대좌표)
        x1_rate = self.ratearea_x1.get()
        y1_rate = self.ratearea_y1.get()
        x2_rate = self.ratearea_x2.get()
        y2_rate = self.ratearea_y2.get()

        try:
            # 엑셀 로드
            all_sheets = pd.read_excel(input_file, sheet_name=None, engine='openpyxl')
            sheet_names = list(all_sheets.keys())
            if not sheet_names:
                messagebox.showinfo("정보", "엑셀 파일에 시트가 없습니다.") 
                return

            sheet_name = sheet_names[0]
            df = all_sheets[sheet_name]
            if df.empty:
                messagebox.showinfo("정보", f"시트 '{sheet_name}'에 데이터가 없습니다.")
                return

            # output 디렉토리에 이미지 저장 폴더 생성
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            save_folder = os.path.join(output_dir, base_name)
            os.makedirs(save_folder, exist_ok=True)

            if '종목코드' not in df.columns or '종목명' not in df.columns:
                messagebox.showinfo("정보", "엑셀에 '종목코드' 혹은 '종목명' 열이 없습니다.")
                return

            results = []
            for index, row in df.iterrows():
                stock_code = str(row['종목코드']).strip()
                stock_name = str(row['종목명']).strip()

                if pd.notna(stock_code) and pd.notna(stock_name):
                    # 클립보드에 종목코드 복사
                    pyperclip.copy(stock_code)

                    # 특정 좌표에서 더블클릭 => (click_x, click_y)
                    pyautogui.click(x=click_x, y=click_y, clicks=2, interval=0.1)

                    # 붙여넣기
                    time.sleep(paste_d)
                    pyautogui.hotkey('ctrl', 'v')

                    # 화면 로딩 대기
                    time.sleep(load_d)

                    # ------------------
                    # 1) AllArea 스크린샷
                    # ------------------
                    width_all = x2_all - x1_all
                    height_all = y2_all - y1_all
                    screenshot_all = pyautogui.screenshot(region=(x1_all, y1_all, width_all, height_all))
                    safe_stock_code = stock_code.replace('/', '_').replace('\\', '_')
                    allarea_path = os.path.join(save_folder, f"{safe_stock_code}.png")
                    screenshot_all.save(allarea_path)

                    # ------------------
                    # 2) DateArea 스크린샷
                    # ------------------
                    width_date = x2_date - x1_date
                    height_date = y2_date - y1_date
                    screenshot_date = pyautogui.screenshot(region=(x1_date, y1_date, width_date, height_date))
                    date_path = os.path.join(save_folder, f"{safe_stock_code}_date.png")
                    screenshot_date.save(date_path)

                    # ------------------
                    # 3) RateArea 스크린샷
                    # ------------------
                    width_rate = x2_rate - x1_rate
                    height_rate = y2_rate - y1_rate
                    screenshot_rate = pyautogui.screenshot(region=(x1_rate, y1_rate, width_rate, height_rate))
                    rate_path = os.path.join(save_folder, f"{safe_stock_code}_rate.png")
                    screenshot_rate.save(rate_path)

                    # OCR을 위해 (index, date_path, rate_path)를 저장
                    results.append((index, date_path, rate_path))

            # OCR 수행 (Date/Rate 절대 영역 이미지)
            ocr_results = self.perform_ocr(results)

            # 결과 df에 기록
            for idx, date_text, rate_text in ocr_results:
                df.at[idx, '날짜_OCR'] = date_text
                df.at[idx, '표면금리_OCR'] = rate_text

            # 저장
            new_file_path = os.path.splitext(input_file)[0] + '_updated.xlsx'
            with pd.ExcelWriter(new_file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

            messagebox.showinfo("정보", "종목코드 작업과 OCR 결과 업데이트가 완료되었습니다.")

        except Exception as e:
            messagebox.showerror("오류", f"오류 발생: {e}")

    def perform_ocr(self, results):
        """
        results: (index, date_path, rate_path) 형태의 튜플 목록

        return: [
          (index, date_text, rate_text),
          ...
        ]
        - PaddleOCR만 사용
        - DateArea, RateArea 이미지 OCR 후, 소수점 3자리까지 표시된 금리 문자열을 반환
        - OCR 후 임시 스크린샷(date_path, rate_path)은 삭제
        """
        reader_paddle = PaddleOCR(lang='en', use_angle_cls=True, show_log=False)

        ocr_results = []
        for index, date_path, rate_path in results:
            date_text_clean = ''
            rate_text_clean = ''

            try:
                # --------------------
                # Date 이미지
                # --------------------
                date_img = Image.open(date_path)
                date_img = self.preprocess_image(date_img)

                # Rate 이미지
                rate_img = Image.open(rate_path)
                rate_img = self.preprocess_image(rate_img)

                # PaddleOCR
                date_res_p = reader_paddle.ocr(np.array(date_img)) or []
                rate_res_p = reader_paddle.ocr(np.array(rate_img)) or []

                date_text_p = ""
                rate_text_p = ""

                if len(date_res_p) > 0 and len(date_res_p[0]) > 0:
                    date_text_p = date_res_p[0][0][1][0]
                if len(rate_res_p) > 0 and len(rate_res_p[0]) > 0:
                    rate_text_p = rate_res_p[0][0][1][0]

                # 문자열 치환
                date_text_clean = (
                    date_text_p.replace('V', '')
                               .replace('v', '')
                               .replace(',', '.')
                               .replace('Q', '0')
                               .replace('O', '0')
                )
                rate_text_clean = (
                    rate_text_p.replace(',', '.')
                               .replace('Q', '0')
                               .replace('O', '0')
                               .replace('o', '0')
                )

                # 금리값을 소수점 세 자리까지
                # 문자열이 숫자로 잘 변환된다면 포매팅, 실패하면 원본 그대로
                try:
                    rate_val = float(rate_text_clean)
                    rate_text_clean = f"{rate_val:.3f}"
                except ValueError:
                    pass

            except Exception as e:
                print(f"OCR 처리 중 오류 발생(Index: {index}): {e}")
            finally:
                # DateArea, RateArea 스크린샷 삭제
                if os.path.exists(date_path):
                    os.remove(date_path)
                if os.path.exists(rate_path):
                    os.remove(rate_path)

            # 결과 저장
            ocr_results.append((index, date_text_clean, rate_text_clean))

        return ocr_results

    def preprocess_image(self, pil_img):
        """흑백 전처리(간단)"""
        gray = pil_img.convert('L')
        arr = np.array(gray)
        return Image.fromarray(arr)


if __name__ == "__main__":
    app = CheckCaptureOCRApp()
    app.mainloop()
