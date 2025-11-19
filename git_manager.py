#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Manager - Git 작업을 위한 간단한 GUI 프로그램
"""

__version__ = "2.4"

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import git
import json
import os
import threading
import schedule
import time
from datetime import datetime
import sys
import winreg
from PIL import Image, ImageDraw
import pystray


class GitManager:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Git Manager v{__version__}")
        self.root.geometry("800x600")

        # 설정 파일 경로 (사용자 AppData 폴더 사용)
        appdata_dir = os.path.join(os.getenv('APPDATA'), 'GitManager')
        os.makedirs(appdata_dir, exist_ok=True)
        self.config_file = os.path.join(appdata_dir, 'config.json')
        self.config = self.load_config()
        self.repo = None

        # 자동 동기화 스레드
        self.sync_thread = None
        self.sync_running = False

        # 시스템 트레이
        self.tray_icon = None
        self.minimized_to_tray = False

        # UI 생성
        self.create_ui()

        # 윈도우 닫기 이벤트 설정
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 경로가 존재하면 저장소 초기화
        if self.config.get("repo_path"):
            self.set_repo_path(self.config["repo_path"])

    def load_config(self):
        """JSON 파일에서 설정 불러오기"""
        default_config = {
            "repo_path": "",
            "commit_message": "update",
            "auto_sync_enabled": False,
            "pull_time": "09:00",
            "push_time": "18:00",
            "repositories": [],  # 저장소 리스트: [{"name": "이름", "path": "경로"}, ...]
            "current_repo_index": -1,  # 현재 선택된 저장소 인덱스
            "minimize_to_tray": False,  # 백그라운드 실행 (시스템 트레이)
            "auto_start": False  # PC 시작 시 자동 실행
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기본값과 병합
                    default_config.update(config)
                    return default_config
            except Exception as e:
                self.log_message(f"설정 불러오기 오류: {e}", "error")

        return default_config

    def save_config(self):
        """JSON 파일에 설정 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.log_message("설정 저장됨", "success")
        except Exception as e:
            self.log_message(f"설정 저장 오류: {e}", "error")

    def create_ui(self):
        """메인 UI 생성"""
        # 상단 프레임 - 빠른 작업
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        # 저장소 선택 (드롭다운)
        ttk.Label(top_frame, text="저장소:").pack(side=tk.LEFT, padx=5)

        self.repo_combo_var = tk.StringVar()
        self.repo_combo = ttk.Combobox(top_frame, textvariable=self.repo_combo_var,
                                       width=50, state="readonly")
        self.repo_combo.pack(side=tk.LEFT, padx=5)
        self.repo_combo.bind("<<ComboboxSelected>>", self.on_repo_selected)

        ttk.Button(top_frame, text="찾아보기", command=self.browse_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="💾 저장", command=self.save_current_repo).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="🗑️ 삭제", command=self.delete_current_repo).pack(side=tk.LEFT, padx=5)

        # 빠른 작업 버튼
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X)

        self.pull_btn = ttk.Button(button_frame, text="⬇️ Quick Pull",
                                    command=self.quick_pull, width=20)
        self.pull_btn.pack(side=tk.LEFT, padx=10)

        self.push_btn = ttk.Button(button_frame, text="⬆️ Quick Push",
                                    command=self.quick_push, width=20)
        self.push_btn.pack(side=tk.LEFT, padx=10)

        self.status_btn = ttk.Button(button_frame, text="📊 Refresh Status",
                                     command=self.refresh_status, width=20)
        self.status_btn.pack(side=tk.LEFT, padx=10)

        # 노트북 (탭)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 탭 1: 상태
        status_frame = ttk.Frame(notebook)
        notebook.add(status_frame, text="상태")

        ttk.Label(status_frame, text="현재 변경사항:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=5, pady=5)
        self.status_text = scrolledtext.ScrolledText(status_frame, height=15, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 탭 2: 히스토리
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="히스토리")

        history_toolbar = ttk.Frame(history_frame)
        history_toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(history_toolbar, text="최근 커밋:").pack(side=tk.LEFT, padx=5)
        ttk.Button(history_toolbar, text="새로고침", command=self.refresh_history).pack(side=tk.LEFT, padx=5)

        self.history_text = scrolledtext.ScrolledText(history_frame, height=15, wrap=tk.WORD)
        self.history_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 탭 3: 자동 동기화
        autosync_frame = ttk.Frame(notebook)
        notebook.add(autosync_frame, text="자동 동기화")

        self.auto_sync_var = tk.BooleanVar(value=self.config.get("auto_sync_enabled", False))
        ttk.Checkbutton(autosync_frame, text="자동 동기화 활성화",
                       variable=self.auto_sync_var,
                       command=self.toggle_auto_sync).pack(anchor=tk.W, padx=10, pady=10)

        time_frame = ttk.Frame(autosync_frame)
        time_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(time_frame, text="Pull 시간 (HH:MM):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.pull_time_var = tk.StringVar(value=self.config.get("pull_time", "09:00"))
        ttk.Entry(time_frame, textvariable=self.pull_time_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(time_frame, text="Push 시간 (HH:MM):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.push_time_var = tk.StringVar(value=self.config.get("push_time", "18:00"))
        ttk.Entry(time_frame, textvariable=self.push_time_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(autosync_frame, text="일정 저장", command=self.save_schedule).pack(padx=10, pady=10)

        ttk.Label(autosync_frame, text="일정 상태:", font=('Arial', 9, 'bold')).pack(anchor=tk.W, padx=10, pady=5)
        self.schedule_status_text = scrolledtext.ScrolledText(autosync_frame, height=8, wrap=tk.WORD)
        self.schedule_status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 탭 4: 설정
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="설정")

        # 커밋 메시지 설정
        ttk.Label(settings_frame, text="커밋 메시지 템플릿:",
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.commit_msg_var = tk.StringVar(value=self.config.get("commit_message", "update"))
        ttk.Entry(settings_frame, textvariable=self.commit_msg_var, width=50).pack(padx=10, pady=5)

        # 구분선
        ttk.Separator(settings_frame, orient='horizontal').pack(fill=tk.X, padx=10, pady=20)

        # 프로그램 동작 설정
        ttk.Label(settings_frame, text="프로그램 동작:",
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=(0, 10))

        # 백그라운드 실행
        self.minimize_to_tray_var = tk.BooleanVar(value=self.config.get("minimize_to_tray", False))
        ttk.Checkbutton(settings_frame, text="닫기 버튼 클릭 시 백그라운드 실행 (시스템 트레이로 최소화)",
                       variable=self.minimize_to_tray_var).pack(anchor=tk.W, padx=30, pady=5)

        # 자동 시작
        self.auto_start_var = tk.BooleanVar(value=self.config.get("auto_start", False))
        ttk.Checkbutton(settings_frame, text="Windows 시작 시 자동 실행",
                       variable=self.auto_start_var).pack(anchor=tk.W, padx=30, pady=5)

        # 설명 레이블
        ttk.Label(settings_frame, text="💡 백그라운드 실행: 프로그램을 닫으면 시스템 트레이에서 실행됩니다",
                 foreground="gray", font=('Arial', 8)).pack(anchor=tk.W, padx=30, pady=(0, 5))
        ttk.Label(settings_frame, text="💡 자동 실행: PC 부팅 시 Git Manager가 자동으로 시작됩니다",
                 foreground="gray", font=('Arial', 8)).pack(anchor=tk.W, padx=30, pady=(0, 10))

        ttk.Button(settings_frame, text="설정 저장", command=self.save_settings).pack(padx=10, pady=10)

        # 탭 5: 로그
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="로그")

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 컬러 출력을 위한 텍스트 태그 설정
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("info", foreground="blue")

        # 초기 로그
        self.log_message("Git Manager 시작됨", "info")
        if self.config.get("repo_path"):
            self.log_message(f"저장소: {self.config['repo_path']}", "info")

        # 저장소 콤보박스 로드
        self.refresh_repo_combo()

    def browse_folder(self):
        """저장소 폴더 찾아보기"""
        folder = filedialog.askdirectory(title="Git 저장소 선택")
        if folder:
            self.set_repo_path(folder)

    def set_repo_path(self, path):
        """저장소 경로 설정 및 초기화"""
        try:
            self.repo = git.Repo(path)
            self.config["repo_path"] = path
            self.save_config()

            # 콤보박스 업데이트 - 저장소 리스트에 있으면 선택, 없으면 경로만 표시
            repositories = self.config.get("repositories", [])
            found = False
            for idx, repo in enumerate(repositories):
                if repo['path'] == path:
                    self.repo_combo_var.set(f"{repo['name']} - {repo['path']}")
                    found = True
                    break

            if not found:
                # 저장소 리스트에 없으면 경로만 표시
                self.repo_combo_var.set(path)

            self.log_message(f"저장소 로드됨: {path}", "success")
            self.refresh_status()
        except Exception as e:
            self.log_message(f"저장소 로드 오류: {e}", "error")
            messagebox.showerror("오류", f"유효하지 않은 Git 저장소:\n{e}")

    def quick_pull(self):
        """git pull 실행"""
        # ALL 옵션 선택 시 전체 저장소 Pull
        selected = self.repo_combo_var.get()
        if selected == "🌐 ALL":
            self.pull_all_repos()
            return

        if not self.repo:
            messagebox.showwarning("경고", "먼저 저장소를 선택해주세요")
            return

        self.log_message("Quick Pull 실행 중...", "info")
        try:
            origin = self.repo.remotes.origin
            result = origin.pull()
            self.log_message(f"Pull 완료: {result}", "success")
            self.refresh_status()
            messagebox.showinfo("성공", "Pull이 성공적으로 완료되었습니다!")
        except Exception as e:
            self.log_message(f"Pull 오류: {e}", "error")
            messagebox.showerror("오류", f"Pull 실패:\n{e}")

    def quick_push(self):
        """git add, commit, push 실행"""
        # ALL 옵션 선택 시 전체 저장소 Push
        selected = self.repo_combo_var.get()
        if selected == "🌐 ALL":
            self.push_all_repos()
            return

        if not self.repo:
            messagebox.showwarning("경고", "먼저 저장소를 선택해주세요")
            return

        self.log_message("Quick Push 실행 중...", "info")
        try:
            # 변경사항 확인
            if not self.repo.is_dirty(untracked_files=True):
                self.log_message("커밋할 변경사항이 없습니다", "info")
                messagebox.showinfo("정보", "커밋할 변경사항이 없습니다")
                return

            # 모든 변경사항 추가
            self.repo.git.add(A=True)
            self.log_message("모든 변경사항 추가됨", "success")

            # 커밋
            commit_msg = self.config.get("commit_message", "update")
            self.repo.index.commit(commit_msg)
            self.log_message(f"커밋 완료: {commit_msg}", "success")

            # 푸시
            origin = self.repo.remotes.origin
            result = origin.push()
            self.log_message(f"Push 완료: {result}", "success")

            self.refresh_status()
            messagebox.showinfo("성공", "Push가 성공적으로 완료되었습니다!")
        except Exception as e:
            self.log_message(f"Push 오류: {e}", "error")
            messagebox.showerror("오류", f"Push 실패:\n{e}")

    def refresh_status(self):
        """git 상태 새로고침"""
        if not self.repo:
            self.status_text.delete(1.0, tk.END)
            self.status_text.insert(tk.END, "저장소가 로드되지 않음")
            return

        try:
            status_output = self.repo.git.status()
            self.status_text.delete(1.0, tk.END)
            self.status_text.insert(tk.END, status_output)
            self.log_message("상태 새로고침됨", "info")
        except Exception as e:
            self.log_message(f"상태 오류: {e}", "error")

    def refresh_history(self):
        """커밋 히스토리 새로고침"""
        if not self.repo:
            self.history_text.delete(1.0, tk.END)
            self.history_text.insert(tk.END, "저장소가 로드되지 않음")
            return

        try:
            commits = list(self.repo.iter_commits('HEAD', max_count=20))
            self.history_text.delete(1.0, tk.END)

            for commit in commits:
                commit_time = datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                commit_info = f"[{commit_time}] {commit.hexsha[:7]} - {commit.message.strip()}\n"
                commit_info += f"작성자: {commit.author.name} <{commit.author.email}>\n\n"
                self.history_text.insert(tk.END, commit_info)

            self.log_message("히스토리 새로고침됨", "info")
        except Exception as e:
            self.log_message(f"히스토리 오류: {e}", "error")

    def toggle_auto_sync(self):
        """자동 동기화 켜기/끄기"""
        enabled = self.auto_sync_var.get()
        self.config["auto_sync_enabled"] = enabled
        self.save_config()

        if enabled:
            self.start_auto_sync()
        else:
            self.stop_auto_sync()

    def save_schedule(self):
        """자동 동기화 일정 저장"""
        self.config["pull_time"] = self.pull_time_var.get()
        self.config["push_time"] = self.push_time_var.get()
        self.save_config()

        if self.auto_sync_var.get():
            self.stop_auto_sync()
            self.start_auto_sync()

        messagebox.showinfo("성공", "일정이 저장되었습니다!")

    def start_auto_sync(self):
        """자동 동기화 스케줄러 시작"""
        if self.sync_running:
            return

        schedule.clear()

        pull_time = self.config.get("pull_time", "09:00")
        push_time = self.config.get("push_time", "18:00")

        schedule.every().day.at(pull_time).do(self.scheduled_pull)
        schedule.every().day.at(push_time).do(self.scheduled_push)

        self.sync_running = True
        self.sync_thread = threading.Thread(target=self.run_schedule, daemon=True)
        self.sync_thread.start()

        self.log_message(f"자동 동기화 활성화됨: Pull {pull_time}, Push {push_time}", "success")
        self.update_schedule_status()

    def stop_auto_sync(self):
        """자동 동기화 스케줄러 중지"""
        self.sync_running = False
        schedule.clear()
        self.log_message("자동 동기화 비활성화됨", "info")
        self.update_schedule_status()

    def run_schedule(self):
        """스케줄러 루프 실행"""
        while self.sync_running:
            schedule.run_pending()
            time.sleep(60)  # 매 분마다 확인

    def scheduled_pull(self):
        """예약된 pull 작업"""
        self.log_message("자동 동기화: 예약된 pull 실행 중", "info")
        self.quick_pull()

    def scheduled_push(self):
        """예약된 push 작업"""
        self.log_message("자동 동기화: 예약된 push 실행 중", "info")
        self.quick_push()

    def update_schedule_status(self):
        """일정 상태 표시 업데이트"""
        self.schedule_status_text.delete(1.0, tk.END)

        if self.auto_sync_var.get():
            status = f"✅ 자동 동기화 활성화됨\n\n"
            status += f"예약된 작업:\n"
            status += f"  • Pull:  매일 {self.config.get('pull_time', '09:00')}\n"
            status += f"  • Push:  매일 {self.config.get('push_time', '18:00')}\n\n"
            status += f"다음 예약 실행:\n"

            for job in schedule.jobs:
                status += f"  • {job}\n"
        else:
            status = "❌ 자동 동기화 비활성화됨\n\n"
            status += "자동 pull/push 작업을 예약하려면 자동 동기화를 활성화하세요."

        self.schedule_status_text.insert(tk.END, status)

    def save_settings(self):
        """설정 저장"""
        self.config["commit_message"] = self.commit_msg_var.get()
        self.config["minimize_to_tray"] = self.minimize_to_tray_var.get()
        self.config["auto_start"] = self.auto_start_var.get()

        # 자동 시작 설정 적용
        if self.auto_start_var.get():
            self.enable_auto_start()
        else:
            self.disable_auto_start()

        self.save_config()
        messagebox.showinfo("성공", "설정이 저장되었습니다!")

    def log_message(self, message, msg_type="info"):
        """로그에 메시지 추가"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry, msg_type)
        self.log_text.see(tk.END)

    # 저장소 관리 메서드들
    def refresh_repo_combo(self):
        """저장소 콤보박스 새로고침"""
        repositories = self.config.get("repositories", [])

        # 콤보박스 항목 생성
        items = ["🌐 ALL"]  # ALL 옵션을 맨 위에 추가
        for repo in repositories:
            items.append(f"{repo['name']} - {repo['path']}")

        self.repo_combo['values'] = items

        # 현재 선택된 저장소 표시
        current_path = self.config.get("repo_path", "")
        if current_path:
            for idx, repo in enumerate(repositories):
                if repo['path'] == current_path:
                    self.repo_combo_var.set(items[idx + 1])  # +1 because of ALL option
                    break
        elif items:
            self.repo_combo_var.set(items[0])  # 기본값: ALL

        self.log_message(f"저장소 리스트 새로고침됨 (총 {len(repositories)}개)", "info")

    def on_repo_selected(self, event=None):
        """저장소 선택 콜백"""
        selected = self.repo_combo_var.get()

        if not selected or selected == "🌐 ALL":
            # ALL 선택 시 현재 저장소 초기화
            self.repo = None
            self.config["repo_path"] = ""
            self.save_config()
            self.log_message("ALL 모드: 전체 저장소 작업 가능", "info")
            return

        # 선택된 저장소 찾기
        repositories = self.config.get("repositories", [])
        for repo_info in repositories:
            display_text = f"{repo_info['name']} - {repo_info['path']}"
            if selected == display_text:
                self.set_repo_path(repo_info['path'])
                self.log_message(f"저장소 선택됨: {repo_info['name']}", "success")
                break

    def save_current_repo(self):
        """현재 표시된 경로를 저장소 리스트에 저장"""
        current_path = self.config.get("repo_path", "")
        if not current_path:
            messagebox.showwarning("경고", "먼저 저장소를 선택해주세요 (찾아보기 버튼 사용)")
            return

        # Git 저장소인지 확인
        try:
            git.Repo(current_path)
        except Exception as e:
            messagebox.showerror("오류", f"유효하지 않은 Git 저장소:\n{e}")
            return

        # 이미 등록된 저장소인지 확인
        repositories = self.config.get("repositories", [])
        for repo in repositories:
            if repo['path'] == current_path:
                messagebox.showinfo("정보", "이미 등록된 저장소입니다")
                return

        # 이름 입력받기
        name = os.path.basename(current_path)
        name = simpledialog.askstring("저장소 이름",
                                     "저장소 이름을 입력하세요:",
                                     initialvalue=name)
        if not name:
            return

        # 추가
        repositories.append({"name": name, "path": current_path})
        self.config["repositories"] = repositories
        self.save_config()
        self.refresh_repo_combo()
        self.log_message(f"저장소 저장됨: {name} ({current_path})", "success")
        messagebox.showinfo("성공", f"저장소가 저장되었습니다: {name}")

    def delete_current_repo(self):
        """선택된 저장소를 리스트에서 삭제"""
        selected = self.repo_combo_var.get()

        if not selected or selected == "🌐 ALL":
            messagebox.showwarning("경고", "삭제할 저장소를 선택해주세요")
            return

        # 선택된 저장소 찾기
        repositories = self.config.get("repositories", [])
        for idx, repo in enumerate(repositories):
            display_text = f"{repo['name']} - {repo['path']}"
            if selected == display_text:
                # 삭제 확인
                confirm = messagebox.askyesno("확인",
                                            f"'{repo['name']}' 저장소를 삭제하시겠습니까?\n(실제 파일은 삭제되지 않습니다)")
                if not confirm:
                    return

                # 삭제
                removed_repo = repositories.pop(idx)
                self.config["repositories"] = repositories

                # 현재 선택된 저장소인 경우 초기화
                if self.config.get("repo_path") == repo['path']:
                    self.repo = None
                    self.config["repo_path"] = ""

                self.save_config()
                self.refresh_repo_combo()
                self.log_message(f"저장소 삭제됨: {removed_repo['name']}", "info")
                messagebox.showinfo("성공", "저장소가 삭제되었습니다")
                return

        messagebox.showerror("오류", "저장소를 찾을 수 없습니다")

    def pull_all_repos(self):
        """전체 저장소 Pull"""
        repositories = self.config.get("repositories", [])
        if not repositories:
            messagebox.showwarning("경고", "등록된 저장소가 없습니다")
            return

        confirm = messagebox.askyesno("확인",
                                      f"총 {len(repositories)}개 저장소에 대해 Pull을 실행하시겠습니까?")
        if not confirm:
            return

        self.log_message(f"=== 전체 저장소 Pull 시작 (총 {len(repositories)}개) ===", "info")
        success_count = 0
        fail_count = 0

        for repo_info in repositories:
            try:
                self.log_message(f"Pull 중: {repo_info['name']} ({repo_info['path']})", "info")
                repo = git.Repo(repo_info['path'])
                origin = repo.remotes.origin
                result = origin.pull()
                self.log_message(f"  ✓ 완료: {repo_info['name']}", "success")
                success_count += 1
            except Exception as e:
                self.log_message(f"  ✗ 실패: {repo_info['name']} - {e}", "error")
                fail_count += 1

        summary = f"=== 전체 Pull 완료: 성공 {success_count}개, 실패 {fail_count}개 ==="
        self.log_message(summary, "success" if fail_count == 0 else "info")
        messagebox.showinfo("완료", f"전체 Pull이 완료되었습니다\n성공: {success_count}개\n실패: {fail_count}개")

    def push_all_repos(self):
        """전체 저장소 Push"""
        repositories = self.config.get("repositories", [])
        if not repositories:
            messagebox.showwarning("경고", "등록된 저장소가 없습니다")
            return

        confirm = messagebox.askyesno("확인",
                                      f"총 {len(repositories)}개 저장소에 대해 Push를 실행하시겠습니까?")
        if not confirm:
            return

        self.log_message(f"=== 전체 저장소 Push 시작 (총 {len(repositories)}개) ===", "info")
        success_count = 0
        fail_count = 0
        skip_count = 0

        commit_msg = self.config.get("commit_message", "update")

        for repo_info in repositories:
            try:
                self.log_message(f"Push 중: {repo_info['name']} ({repo_info['path']})", "info")
                repo = git.Repo(repo_info['path'])

                # 변경사항 확인
                if not repo.is_dirty(untracked_files=True):
                    self.log_message(f"  ○ 건너뜀: {repo_info['name']} (변경사항 없음)", "info")
                    skip_count += 1
                    continue

                # Add, Commit, Push
                repo.git.add(A=True)
                repo.index.commit(commit_msg)
                origin = repo.remotes.origin
                result = origin.push()
                self.log_message(f"  ✓ 완료: {repo_info['name']}", "success")
                success_count += 1
            except Exception as e:
                self.log_message(f"  ✗ 실패: {repo_info['name']} - {e}", "error")
                fail_count += 1

        summary = f"=== 전체 Push 완료: 성공 {success_count}개, 실패 {fail_count}개, 건너뜀 {skip_count}개 ==="
        self.log_message(summary, "success" if fail_count == 0 else "info")
        messagebox.showinfo("완료",
                          f"전체 Push가 완료되었습니다\n성공: {success_count}개\n실패: {fail_count}개\n건너뜀: {skip_count}개")

    # 시스템 트레이 및 자동 시작 기능
    def on_closing(self):
        """윈도우 닫기 이벤트 처리"""
        if self.config.get("minimize_to_tray", False):
            # 백그라운드 실행 설정이 켜져있으면 트레이로 최소화
            self.minimize_to_system_tray()
        else:
            # 일반 종료
            self.quit_app()

    def minimize_to_system_tray(self):
        """시스템 트레이로 최소화"""
        self.root.withdraw()  # 윈도우 숨기기
        self.minimized_to_tray = True

        if not self.tray_icon:
            # 트레이 아이콘 생성
            self.create_tray_icon()

        self.log_message("백그라운드로 실행 중 (시스템 트레이)", "info")

    def create_tray_icon(self):
        """시스템 트레이 아이콘 생성"""
        # 간단한 아이콘 이미지 생성 (G 문자)
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, 63, 63], fill='#2196F3')
        draw.text((10, 10), 'GM', fill='white')

        # 트레이 메뉴
        menu = pystray.Menu(
            pystray.MenuItem("열기", self.show_from_tray),
            pystray.MenuItem("종료", self.quit_from_tray)
        )

        # 트레이 아이콘 생성
        self.tray_icon = pystray.Icon("GitManager", image, "Git Manager", menu)

        # 백그라운드 스레드에서 실행
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def show_from_tray(self, icon=None, item=None):
        """트레이에서 윈도우 복원"""
        self.root.deiconify()  # 윈도우 보이기
        self.root.lift()  # 맨 앞으로
        self.minimized_to_tray = False

        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def quit_from_tray(self, icon=None, item=None):
        """트레이에서 종료"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit_app()

    def quit_app(self):
        """프로그램 종료"""
        # 자동 동기화 중지
        if self.sync_running:
            self.stop_auto_sync()

        # 트레이 아이콘 정리
        if self.tray_icon:
            self.tray_icon.stop()

        self.log_message("Git Manager 종료", "info")
        self.root.quit()
        self.root.destroy()

    def enable_auto_start(self):
        """Windows 시작 시 자동 실행 활성화"""
        try:
            # 실행 파일 경로
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 경우
                exe_path = sys.executable
            else:
                # 개발 환경
                exe_path = os.path.abspath(sys.argv[0])

            # 레지스트리 키 열기
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )

            # 레지스트리에 등록
            winreg.SetValueEx(key, "GitManager", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)

            self.log_message("자동 시작 활성화됨", "success")
        except Exception as e:
            self.log_message(f"자동 시작 설정 오류: {e}", "error")
            messagebox.showerror("오류", f"자동 시작 설정 실패:\n{e}")

    def disable_auto_start(self):
        """Windows 시작 시 자동 실행 비활성화"""
        try:
            # 레지스트리 키 열기
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )

            # 레지스트리에서 삭제
            try:
                winreg.DeleteValue(key, "GitManager")
                self.log_message("자동 시작 비활성화됨", "info")
            except FileNotFoundError:
                # 이미 없는 경우
                pass

            winreg.CloseKey(key)
        except Exception as e:
            self.log_message(f"자동 시작 해제 오류: {e}", "error")


def main():
    root = tk.Tk()
    app = GitManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
