#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Manager - Git 작업을 위한 간단한 GUI 프로그램
"""

__version__ = "2.0"

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import git
import json
import os
import threading
import schedule
import time
from datetime import datetime


class GitManager:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Git Manager v{__version__}")
        self.root.geometry("800x600")

        # 설정
        self.config_file = "config.json"
        self.config = self.load_config()
        self.repo = None

        # 자동 동기화 스레드
        self.sync_thread = None
        self.sync_running = False

        # UI 생성
        self.create_ui()

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
            "current_repo_index": -1  # 현재 선택된 저장소 인덱스
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

        # 저장소 경로
        ttk.Label(top_frame, text="저장소:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar(value=self.config.get("repo_path", ""))
        path_entry = ttk.Entry(top_frame, textvariable=self.path_var, width=50)
        path_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(top_frame, text="찾아보기", command=self.browse_folder).pack(side=tk.LEFT, padx=5)

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

        ttk.Label(settings_frame, text="커밋 메시지 템플릿:",
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=10)

        self.commit_msg_var = tk.StringVar(value=self.config.get("commit_message", "update"))
        ttk.Entry(settings_frame, textvariable=self.commit_msg_var, width=50).pack(padx=10, pady=5)

        ttk.Button(settings_frame, text="설정 저장", command=self.save_settings).pack(padx=10, pady=10)

        # 탭 5: 저장소 관리
        repo_mgmt_frame = ttk.Frame(notebook)
        notebook.add(repo_mgmt_frame, text="저장소 관리")

        # 상단 버튼 영역
        repo_btn_frame = ttk.Frame(repo_mgmt_frame)
        repo_btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(repo_btn_frame, text="➕ 저장소 추가", command=self.add_repository, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(repo_btn_frame, text="➖ 저장소 삭제", command=self.remove_repository, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(repo_btn_frame, text="✓ 선택", command=self.select_repository, width=15).pack(side=tk.LEFT, padx=5)

        # 리스트박스 영역
        list_frame = ttk.Frame(repo_mgmt_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        ttk.Label(list_frame, text="등록된 저장소:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=5, pady=5)

        # 스크롤바와 리스트박스
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.repo_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Arial', 10))
        self.repo_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.repo_listbox.yview)

        # 전체 작업 버튼 영역
        all_btn_frame = ttk.Frame(repo_mgmt_frame)
        all_btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(all_btn_frame, text="전체 저장소 작업:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Button(all_btn_frame, text="⬇️ All Pull", command=self.pull_all_repos, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(all_btn_frame, text="⬆️ All Push", command=self.push_all_repos, width=15).pack(side=tk.LEFT, padx=5)

        # 탭 6: 로그
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

        # 저장소 리스트 로드
        self.refresh_repo_list()

    def browse_folder(self):
        """저장소 폴더 찾아보기"""
        folder = filedialog.askdirectory(title="Git 저장소 선택")
        if folder:
            self.set_repo_path(folder)

    def set_repo_path(self, path):
        """저장소 경로 설정 및 초기화"""
        try:
            self.repo = git.Repo(path)
            self.path_var.set(path)
            self.config["repo_path"] = path
            self.save_config()
            self.log_message(f"저장소 로드됨: {path}", "success")
            self.refresh_status()
        except Exception as e:
            self.log_message(f"저장소 로드 오류: {e}", "error")
            messagebox.showerror("오류", f"유효하지 않은 Git 저장소:\n{e}")

    def quick_pull(self):
        """git pull 실행"""
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
        self.save_config()
        messagebox.showinfo("성공", "설정이 저장되었습니다!")

    def log_message(self, message, msg_type="info"):
        """로그에 메시지 추가"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry, msg_type)
        self.log_text.see(tk.END)

    # 저장소 관리 메서드들
    def refresh_repo_list(self):
        """저장소 리스트 새로고침"""
        self.repo_listbox.delete(0, tk.END)
        repositories = self.config.get("repositories", [])
        current_index = self.config.get("current_repo_index", -1)

        for idx, repo in enumerate(repositories):
            display_text = f"{repo['name']} - {repo['path']}"
            if idx == current_index:
                display_text = f"★ {display_text}"
            self.repo_listbox.insert(tk.END, display_text)

        self.log_message(f"저장소 리스트 새로고침됨 (총 {len(repositories)}개)", "info")

    def add_repository(self):
        """저장소 추가"""
        folder = filedialog.askdirectory(title="추가할 Git 저장소 선택")
        if not folder:
            return

        # Git 저장소인지 확인
        try:
            git.Repo(folder)
        except Exception as e:
            messagebox.showerror("오류", f"유효하지 않은 Git 저장소:\n{e}")
            return

        # 이름 입력받기
        name = os.path.basename(folder)
        name = tk.simpledialog.askstring("저장소 이름",
                                         "저장소 이름을 입력하세요:",
                                         initialvalue=name)
        if not name:
            return

        # 중복 확인
        repositories = self.config.get("repositories", [])
        for repo in repositories:
            if repo['path'] == folder:
                messagebox.showwarning("경고", "이미 추가된 저장소입니다")
                return

        # 추가
        repositories.append({"name": name, "path": folder})
        self.config["repositories"] = repositories
        self.save_config()
        self.refresh_repo_list()
        self.log_message(f"저장소 추가됨: {name} ({folder})", "success")
        messagebox.showinfo("성공", f"저장소가 추가되었습니다: {name}")

    def remove_repository(self):
        """저장소 삭제"""
        selection = self.repo_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 저장소를 선택해주세요")
            return

        idx = selection[0]
        repositories = self.config.get("repositories", [])

        if idx >= len(repositories):
            return

        repo = repositories[idx]
        confirm = messagebox.askyesno("확인",
                                      f"'{repo['name']}' 저장소를 삭제하시겠습니까?\n(실제 파일은 삭제되지 않습니다)")
        if not confirm:
            return

        # 현재 선택된 저장소인 경우 초기화
        current_index = self.config.get("current_repo_index", -1)
        if current_index == idx:
            self.config["current_repo_index"] = -1
            self.config["repo_path"] = ""
            self.repo = None
            self.path_var.set("")
        elif current_index > idx:
            self.config["current_repo_index"] = current_index - 1

        # 삭제
        removed_repo = repositories.pop(idx)
        self.config["repositories"] = repositories
        self.save_config()
        self.refresh_repo_list()
        self.log_message(f"저장소 삭제됨: {removed_repo['name']}", "info")
        messagebox.showinfo("성공", "저장소가 삭제되었습니다")

    def select_repository(self):
        """저장소 선택"""
        selection = self.repo_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "선택할 저장소를 클릭해주세요")
            return

        idx = selection[0]
        repositories = self.config.get("repositories", [])

        if idx >= len(repositories):
            return

        repo = repositories[idx]
        self.config["current_repo_index"] = idx
        self.config["repo_path"] = repo['path']
        self.save_config()
        self.set_repo_path(repo['path'])
        self.refresh_repo_list()
        messagebox.showinfo("성공", f"'{repo['name']}' 저장소가 선택되었습니다")

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


def main():
    root = tk.Tk()
    app = GitManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
