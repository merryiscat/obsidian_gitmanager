# Git Manager

간단하고 직관적인 Git 관리 GUI 프로그램

## 주요 기능

### 📥 Quick Pull
- 아침 출근 시 클릭
- `git pull` 실행
- 원격 저장소의 최신 변경사항을 가져옵니다

### 📤 Quick Push
- 퇴근 시 클릭
- `git add .` + `git commit` + `git push` 한번에 실행
- 모든 변경사항을 자동으로 커밋하고 푸시합니다

### 📊 Status
- 현재 Git 상태 확인
- 변경된 파일 목록 표시
- 실시간 상태 새로고침

### 📜 History
- 최근 커밋 히스토리 20개 표시
- 커밋 메시지, 작성자, 날짜 확인

### ⏰ Auto Sync
- 지정된 시간에 자동으로 Pull/Push 실행
- 기본값: 오전 9시 Pull, 오후 6시 Push
- 사용자 정의 시간 설정 가능

### ⚙️ Settings
- 커밋 메시지 템플릿 설정
- 기본값: "update"
- 저장소 경로 저장

## 설치 방법

### 방법 1: 실행 파일 사용 (추천)
1. `build_exe.bat` 실행
2. `dist` 폴더에 생성된 `GitManager.exe` 실행

### 방법 2: Python으로 직접 실행
```bash
# 의존성 설치
pip install -r requirements.txt

# 프로그램 실행
python git_manager.py
```

## 사용 방법

### 초기 설정
1. 프로그램 실행
2. "Browse" 버튼을 클릭하여 Git 저장소 폴더 선택
3. 설정이 자동으로 저장됩니다 (config.json)

### 일반 사용
1. **출근 시**: "⬇️ Quick Pull" 버튼 클릭
2. **작업 진행**: 노트 정리 등 작업 수행
3. **퇴근 시**: "⬆️ Quick Push" 버튼 클릭

### 자동 동기화 설정
1. "Auto Sync" 탭으로 이동
2. "Enable Auto Sync" 체크
3. Pull 시간과 Push 시간 설정 (HH:MM 형식)
4. "Save Schedule" 버튼 클릭
5. 프로그램을 백그라운드로 실행해두면 자동으로 동기화됩니다

## 파일 구조

```
git-manager/
├── git_manager.py      # 메인 프로그램
├── config.json         # 설정 파일 (자동 생성)
├── requirements.txt    # Python 패키지 목록
├── build_exe.bat       # .exe 빌드 스크립트
└── README.md          # 이 파일
```

## 시스템 요구사항

- Windows 10 이상
- Python 3.8 이상 (소스 코드 실행 시)
- Git 설치 필요

## 주의사항

1. **Git 설치 필수**: 시스템에 Git이 설치되어 있어야 합니다
2. **인터넷 연결**: Pull/Push 작업 시 인터넷 연결 필요
3. **Git 인증**: 원격 저장소 인증 설정이 되어 있어야 합니다
   - SSH 키 또는 credential helper 설정 필요
4. **자동 동기화**: 프로그램이 실행 중일 때만 작동합니다

## 설정 파일 (config.json)

```json
{
  "repo_path": "C:/path/to/your/repo",
  "commit_message": "update",
  "auto_sync_enabled": false,
  "pull_time": "09:00",
  "push_time": "18:00"
}
```

## 트러블슈팅

### "Invalid Git repository" 오류
- Git 저장소가 초기화된 폴더인지 확인
- `.git` 폴더가 있는지 확인

### Push 실패
- 인터넷 연결 확인
- Git 인증 설정 확인 (SSH 키 또는 credential helper)
- 원격 저장소 권한 확인

### Auto Sync가 작동하지 않음
- 프로그램이 실행 중인지 확인
- 시간 형식이 "HH:MM" (24시간 형식)인지 확인
- "Enable Auto Sync"가 체크되어 있는지 확인

## 개발자 정보

- Python 3.x
- tkinter (GUI)
- GitPython (Git 작업)
- schedule (자동 스케줄링)
- PyInstaller (.exe 빌드)

## 라이선스

개인 사용 및 수정 가능
