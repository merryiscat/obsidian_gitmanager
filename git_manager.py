#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Manager - Simple GUI for Git operations
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
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
        self.root.title("Git Manager")
        self.root.geometry("800x600")

        # Configuration
        self.config_file = "config.json"
        self.config = self.load_config()
        self.repo = None

        # Auto-sync thread
        self.sync_thread = None
        self.sync_running = False

        # Create UI
        self.create_ui()

        # Initialize repo if path exists
        if self.config.get("repo_path"):
            self.set_repo_path(self.config["repo_path"])

    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
            "repo_path": "",
            "commit_message": "update",
            "auto_sync_enabled": False,
            "pull_time": "09:00",
            "push_time": "18:00"
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults
                    default_config.update(config)
                    return default_config
            except Exception as e:
                self.log_message(f"Error loading config: {e}", "error")

        return default_config

    def save_config(self):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.log_message("Configuration saved", "success")
        except Exception as e:
            self.log_message(f"Error saving config: {e}", "error")

    def create_ui(self):
        """Create the main UI"""
        # Top frame - Quick actions
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        # Repository path
        ttk.Label(top_frame, text="Repository:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar(value=self.config.get("repo_path", ""))
        path_entry = ttk.Entry(top_frame, textvariable=self.path_var, width=50)
        path_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(top_frame, text="Browse", command=self.browse_folder).pack(side=tk.LEFT, padx=5)

        # Quick action buttons
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

        # Notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Status
        status_frame = ttk.Frame(notebook)
        notebook.add(status_frame, text="Status")

        ttk.Label(status_frame, text="Current Changes:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=5, pady=5)
        self.status_text = scrolledtext.ScrolledText(status_frame, height=15, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 2: History
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="History")

        history_toolbar = ttk.Frame(history_frame)
        history_toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(history_toolbar, text="Recent Commits:").pack(side=tk.LEFT, padx=5)
        ttk.Button(history_toolbar, text="Refresh", command=self.refresh_history).pack(side=tk.LEFT, padx=5)

        self.history_text = scrolledtext.ScrolledText(history_frame, height=15, wrap=tk.WORD)
        self.history_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 3: Auto Sync
        autosync_frame = ttk.Frame(notebook)
        notebook.add(autosync_frame, text="Auto Sync")

        self.auto_sync_var = tk.BooleanVar(value=self.config.get("auto_sync_enabled", False))
        ttk.Checkbutton(autosync_frame, text="Enable Auto Sync",
                       variable=self.auto_sync_var,
                       command=self.toggle_auto_sync).pack(anchor=tk.W, padx=10, pady=10)

        time_frame = ttk.Frame(autosync_frame)
        time_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(time_frame, text="Pull Time (HH:MM):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.pull_time_var = tk.StringVar(value=self.config.get("pull_time", "09:00"))
        ttk.Entry(time_frame, textvariable=self.pull_time_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(time_frame, text="Push Time (HH:MM):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.push_time_var = tk.StringVar(value=self.config.get("push_time", "18:00"))
        ttk.Entry(time_frame, textvariable=self.push_time_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(autosync_frame, text="Save Schedule", command=self.save_schedule).pack(padx=10, pady=10)

        ttk.Label(autosync_frame, text="Schedule Status:", font=('Arial', 9, 'bold')).pack(anchor=tk.W, padx=10, pady=5)
        self.schedule_status_text = scrolledtext.ScrolledText(autosync_frame, height=8, wrap=tk.WORD)
        self.schedule_status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tab 4: Settings
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")

        ttk.Label(settings_frame, text="Commit Message Template:",
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=10)

        self.commit_msg_var = tk.StringVar(value=self.config.get("commit_message", "update"))
        ttk.Entry(settings_frame, textvariable=self.commit_msg_var, width=50).pack(padx=10, pady=5)

        ttk.Button(settings_frame, text="Save Settings", command=self.save_settings).pack(padx=10, pady=10)

        # Tab 5: Log
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Log")

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure text tags for colored output
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("info", foreground="blue")

        # Initial log
        self.log_message("Git Manager started", "info")
        if self.config.get("repo_path"):
            self.log_message(f"Repository: {self.config['repo_path']}", "info")

    def browse_folder(self):
        """Browse for repository folder"""
        folder = filedialog.askdirectory(title="Select Git Repository")
        if folder:
            self.set_repo_path(folder)

    def set_repo_path(self, path):
        """Set repository path and initialize"""
        try:
            self.repo = git.Repo(path)
            self.path_var.set(path)
            self.config["repo_path"] = path
            self.save_config()
            self.log_message(f"Repository loaded: {path}", "success")
            self.refresh_status()
        except Exception as e:
            self.log_message(f"Error loading repository: {e}", "error")
            messagebox.showerror("Error", f"Invalid Git repository:\n{e}")

    def quick_pull(self):
        """Execute git pull"""
        if not self.repo:
            messagebox.showwarning("Warning", "Please select a repository first")
            return

        self.log_message("Executing Quick Pull...", "info")
        try:
            origin = self.repo.remotes.origin
            result = origin.pull()
            self.log_message(f"Pull completed: {result}", "success")
            self.refresh_status()
            messagebox.showinfo("Success", "Pull completed successfully!")
        except Exception as e:
            self.log_message(f"Pull error: {e}", "error")
            messagebox.showerror("Error", f"Pull failed:\n{e}")

    def quick_push(self):
        """Execute git add, commit, and push"""
        if not self.repo:
            messagebox.showwarning("Warning", "Please select a repository first")
            return

        self.log_message("Executing Quick Push...", "info")
        try:
            # Check if there are changes
            if not self.repo.is_dirty(untracked_files=True):
                self.log_message("No changes to commit", "info")
                messagebox.showinfo("Info", "No changes to commit")
                return

            # Add all changes
            self.repo.git.add(A=True)
            self.log_message("Added all changes", "success")

            # Commit
            commit_msg = self.config.get("commit_message", "update")
            self.repo.index.commit(commit_msg)
            self.log_message(f"Committed with message: {commit_msg}", "success")

            # Push
            origin = self.repo.remotes.origin
            result = origin.push()
            self.log_message(f"Push completed: {result}", "success")

            self.refresh_status()
            messagebox.showinfo("Success", "Push completed successfully!")
        except Exception as e:
            self.log_message(f"Push error: {e}", "error")
            messagebox.showerror("Error", f"Push failed:\n{e}")

    def refresh_status(self):
        """Refresh git status"""
        if not self.repo:
            self.status_text.delete(1.0, tk.END)
            self.status_text.insert(tk.END, "No repository loaded")
            return

        try:
            status_output = self.repo.git.status()
            self.status_text.delete(1.0, tk.END)
            self.status_text.insert(tk.END, status_output)
            self.log_message("Status refreshed", "info")
        except Exception as e:
            self.log_message(f"Status error: {e}", "error")

    def refresh_history(self):
        """Refresh commit history"""
        if not self.repo:
            self.history_text.delete(1.0, tk.END)
            self.history_text.insert(tk.END, "No repository loaded")
            return

        try:
            commits = list(self.repo.iter_commits('HEAD', max_count=20))
            self.history_text.delete(1.0, tk.END)

            for commit in commits:
                commit_time = datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                commit_info = f"[{commit_time}] {commit.hexsha[:7]} - {commit.message.strip()}\n"
                commit_info += f"Author: {commit.author.name} <{commit.author.email}>\n\n"
                self.history_text.insert(tk.END, commit_info)

            self.log_message("History refreshed", "info")
        except Exception as e:
            self.log_message(f"History error: {e}", "error")

    def toggle_auto_sync(self):
        """Toggle auto sync on/off"""
        enabled = self.auto_sync_var.get()
        self.config["auto_sync_enabled"] = enabled
        self.save_config()

        if enabled:
            self.start_auto_sync()
        else:
            self.stop_auto_sync()

    def save_schedule(self):
        """Save auto sync schedule"""
        self.config["pull_time"] = self.pull_time_var.get()
        self.config["push_time"] = self.push_time_var.get()
        self.save_config()

        if self.auto_sync_var.get():
            self.stop_auto_sync()
            self.start_auto_sync()

        messagebox.showinfo("Success", "Schedule saved!")

    def start_auto_sync(self):
        """Start auto sync scheduler"""
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

        self.log_message(f"Auto sync enabled: Pull at {pull_time}, Push at {push_time}", "success")
        self.update_schedule_status()

    def stop_auto_sync(self):
        """Stop auto sync scheduler"""
        self.sync_running = False
        schedule.clear()
        self.log_message("Auto sync disabled", "info")
        self.update_schedule_status()

    def run_schedule(self):
        """Run the scheduler loop"""
        while self.sync_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def scheduled_pull(self):
        """Scheduled pull operation"""
        self.log_message("Auto sync: Executing scheduled pull", "info")
        self.quick_pull()

    def scheduled_push(self):
        """Scheduled push operation"""
        self.log_message("Auto sync: Executing scheduled push", "info")
        self.quick_push()

    def update_schedule_status(self):
        """Update schedule status display"""
        self.schedule_status_text.delete(1.0, tk.END)

        if self.auto_sync_var.get():
            status = f"✅ Auto Sync ENABLED\n\n"
            status += f"Scheduled Tasks:\n"
            status += f"  • Pull:  Every day at {self.config.get('pull_time', '09:00')}\n"
            status += f"  • Push:  Every day at {self.config.get('push_time', '18:00')}\n\n"
            status += f"Next scheduled runs:\n"

            for job in schedule.jobs:
                status += f"  • {job}\n"
        else:
            status = "❌ Auto Sync DISABLED\n\n"
            status += "Enable auto sync to schedule automatic pull/push operations."

        self.schedule_status_text.insert(tk.END, status)

    def save_settings(self):
        """Save settings"""
        self.config["commit_message"] = self.commit_msg_var.get()
        self.save_config()
        messagebox.showinfo("Success", "Settings saved!")

    def log_message(self, message, msg_type="info"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry, msg_type)
        self.log_text.see(tk.END)


def main():
    root = tk.Tk()
    app = GitManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
