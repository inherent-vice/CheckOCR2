"""Excel and output-folder actions for the legacy Tk shell."""

from __future__ import annotations

import os
import platform
import subprocess
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox
from typing import Any

from checkocr2.ui.file_dialogs import output_folder_for_input_file, output_folder_initial_dir

TK_TCL_ERROR = getattr(tk, "TclError", type("_TkTclError", (Exception,), {}))


def browse_input_excel(
    app: Any,
    *,
    askopenfilename: Callable[..., str] | None = None,
) -> None:
    askopenfilename = askopenfilename or filedialog.askopenfilename
    file_path = askopenfilename(
        title="엑셀 파일 선택",
        filetypes=[("Excel files", "*.xlsx;*.xls")],
    )
    if not file_path:
        return

    app.input_excel_path.set(file_path)
    cleaned_base_path = output_folder_for_input_file(
        file_path,
        clean_folder=app._clean_output_folder_path,
    )
    app.output_folder_path.set(cleaned_base_path)
    app.logger.info(f"Excel 파일 선택됨: {file_path}")
    app.logger.info(f"출력 폴더 자동 설정됨: {cleaned_base_path}")


def browse_output_folder(
    app: Any,
    *,
    askdirectory: Callable[..., str] | None = None,
    initial_dir_func: Callable[[str], str | None] = output_folder_initial_dir,
    showinfo: Callable[[str, str], object] | None = None,
    showerror: Callable[[str, str], object] | None = None,
) -> None:
    askdirectory = askdirectory or filedialog.askdirectory
    showinfo = showinfo or messagebox.showinfo
    showerror = showerror or messagebox.showerror

    try:
        initial_dir = initial_dir_func(app.output_folder_path.get())
        folder_path = askdirectory(
            title="출력 폴더 선택",
            initialdir=initial_dir,
            mustexist=False,
        )

        if not folder_path:
            return

        cleaned_path = app._clean_output_folder_path(folder_path)
        app.output_folder_path.set(cleaned_path)
        app.logger.info(f"출력 폴더 선택됨: {cleaned_path}")

        if cleaned_path.startswith("\\\\"):
            showinfo(
                "네트워크 폴더 선택",
                f"네트워크 폴더가 선택되었습니다.\n\n"
                f"경로: {cleaned_path}\n\n"
                f"• 네트워크 연결 상태를 확인하세요\n"
                f"• 쓰기 권한이 있는지 확인하세요",
            )

    except (OSError, TK_TCL_ERROR, ValueError) as exc:
        app.logger.error(f"폴더 선택 중 오류: {exc}")
        showerror("오류", f"폴더 선택 중 오류가 발생했습니다.\n\n{exc}")


def open_output_folder(
    app: Any,
    *,
    system: Callable[[], str] = platform.system,
    exists: Callable[[str], bool] = os.path.exists,
    makedirs: Callable[..., object] = os.makedirs,
    startfile: Callable[[str], object] | None = None,
    run: Callable[..., object] = subprocess.run,
    askyesno: Callable[[str, str], bool] | None = None,
    showwarning: Callable[[str, str], object] | None = None,
    showerror: Callable[[str, str], object] | None = None,
) -> None:
    askyesno = askyesno or messagebox.askyesno
    showwarning = showwarning or messagebox.showwarning
    showerror = showerror or messagebox.showerror

    output_path = app.output_folder_path.get().strip()
    if not output_path:
        showwarning("경고", "출력 폴더가 설정되지 않았습니다.")
        return

    try:
        current_system = system()
        cleaned_path = str(output_path).strip()

        app.logger.info(f"출력 폴더 열기 시도 - 시스템: {current_system}, 원본 경로: {cleaned_path}")

        if current_system == "Windows":
            _open_windows_output_folder(
                app,
                cleaned_path,
                exists=exists,
                makedirs=makedirs,
                startfile=startfile or os.startfile,
                run=run,
                askyesno=askyesno,
                showwarning=showwarning,
            )
        elif current_system == "Darwin":
            _open_posix_output_folder(
                app,
                cleaned_path,
                command="open",
                system_name="macOS",
                run=run,
            )
        else:
            _open_posix_output_folder(
                app,
                cleaned_path,
                command="xdg-open",
                system_name="Linux",
                run=run,
            )

    except FileNotFoundError:
        showerror("오류", f"폴더 또는 파일을 찾을 수 없습니다.\n경로를 확인해주세요.\n\n경로: {output_path}")
        app.logger.error(f"폴더 열기 실패: FileNotFoundError for {output_path}")
    except subprocess.CalledProcessError as exc:
        showerror("오류", f"폴더 열기 명령어 실행 실패: {exc}\n\n경로: {output_path}")
        app.logger.error(f"폴더 열기 명령어 실행 실패: {exc} for {output_path}")
    except subprocess.TimeoutExpired:
        showerror("오류", "폴더 열기 시간 초과\n네트워크 연결을 확인하세요.")
        app.logger.error("폴더 열기 시간 초과")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        showerror(
            "오류",
            f"알 수 없는 오류 발생: {exc}\n\n경로: {output_path}\n\n네트워크 연결 및 접근 권한을 확인하세요.",
        )
        app.logger.error(f"알 수 없는 오류 발생: {exc} for {output_path}")


def _open_windows_output_folder(
    app: Any,
    cleaned_path: str,
    *,
    exists: Callable[[str], bool],
    makedirs: Callable[..., object],
    startfile: Callable[[str], object],
    run: Callable[..., object],
    askyesno: Callable[[str, str], bool],
    showwarning: Callable[[str, str], object],
) -> None:
    if cleaned_path.startswith("\\") and not cleaned_path.startswith("\\\\"):
        cleaned_path = "\\" + cleaned_path
        app.logger.info(f"UNC 경로 정규화: {cleaned_path}")

    cleaned_path_windows = cleaned_path.replace("/", "\\")
    app.logger.info(f"Windows 형식 경로 변환 후: {cleaned_path_windows}")

    is_unc = cleaned_path_windows.startswith("\\\\")
    try:
        if not exists(cleaned_path_windows):
            if is_unc:
                if not _prepare_unc_output_folder(
                    app,
                    cleaned_path_windows,
                    exists=exists,
                    makedirs=makedirs,
                    askyesno=askyesno,
                    showwarning=showwarning,
                ):
                    return
            else:
                if askyesno(
                    "폴더 생성",
                    f"폴더가 존재하지 않습니다.\n생성하시겠습니까?\n\n경로: {cleaned_path_windows}",
                ):
                    makedirs(cleaned_path_windows, exist_ok=True)
                    app.logger.info(f"로컬 폴더 생성됨: {cleaned_path_windows}")
                else:
                    return
        else:
            app.logger.info(f"폴더가 이미 존재합니다: {cleaned_path_windows}")
    except (OSError, ValueError) as path_error:
        app.logger.warning(f"경로 접근 확인 중 오류: {path_error}")

    try:
        startfile(cleaned_path_windows)
        app.logger.info("출력 폴더 열기 (Windows Explorer) 완료")
    except OSError as startfile_error:
        app.logger.error(f"os.startfile 실패: {startfile_error}")
        try:
            run(["explorer", cleaned_path_windows], check=True, timeout=10)
            app.logger.info("출력 폴더 열기 (explorer.exe) 완료")
        except (OSError, subprocess.SubprocessError) as explorer_error:
            app.logger.error(f"explorer.exe 호출 실패: {explorer_error}")
            raise explorer_error


def _prepare_unc_output_folder(
    app: Any,
    cleaned_path_windows: str,
    *,
    exists: Callable[[str], bool],
    makedirs: Callable[..., object],
    askyesno: Callable[[str, str], bool],
    showwarning: Callable[[str, str], object],
) -> bool:
    app.logger.info("UNC 경로입니다. 네트워크 연결을 확인합니다.")
    try:
        path_parts = cleaned_path_windows.split("\\")
        if len(path_parts) >= 4:
            server_share = "\\\\" + path_parts[2] + "\\" + path_parts[3]
            if exists(server_share):
                makedirs(cleaned_path_windows, exist_ok=True)
                app.logger.info(f"UNC 네트워크 폴더 생성됨: {cleaned_path_windows}")
            else:
                app.logger.warning(f"네트워크 서버에 접근할 수 없습니다: {server_share}")
                showwarning(
                    "네트워크 오류",
                    f"네트워크 서버에 접근할 수 없습니다.\n\n"
                    f"서버: {server_share}\n"
                    f"• 네트워크 연결을 확인하세요\n"
                    f"• 접근 권한을 확인하세요\n"
                    f"• VPN 연결이 필요할 수 있습니다",
                )
                return False
    except (OSError, ValueError) as exc:
        app.logger.error(f"UNC 경로 접근 오류: {exc}")
        if not askyesno(
            "네트워크 폴더 오류",
            f"네트워크 폴더에 접근할 수 없습니다.\n\n"
            f"오류: {exc}\n\n"
            f"그래도 폴더 열기를 시도하시겠습니까?",
        ):
            return False
    return True


def _open_posix_output_folder(
    app: Any,
    cleaned_path: str,
    *,
    command: str,
    system_name: str,
    run: Callable[..., object],
) -> None:
    if cleaned_path.startswith(("\\", "//")):
        smb_path = "smb:" + cleaned_path.replace("\\", "/")
        app.logger.info(f"{system_name} SMB 경로 변환 후: {smb_path}")
        run([command, smb_path], check=True, timeout=10)
        app.logger.info(f"출력 폴더 열기 시도 ({system_name} smb) 완료")
    else:
        app.logger.info(f"{system_name} 로컬 경로: {cleaned_path}")
        run([command, cleaned_path], check=True, timeout=10)
        app.logger.info(f"출력 폴더 열기 시도 ({system_name}) 완료")
