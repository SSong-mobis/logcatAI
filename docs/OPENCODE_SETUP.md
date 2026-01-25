# OpenCode 설치 및 설정 가이드

## Windows PowerShell 실행 정책 문제 해결

Windows에서 npm 명령을 실행할 때 다음과 같은 오류가 발생할 수 있습니다:

```
npm : 이 시스템에서 스크립트를 실행할 수 없으므로 C:\Program Files\nodejs\npm.ps1 파일을 로드할 수 없습니다.
```

### 해결 방법

**방법 1: PowerShell 실행 정책 변경 (권장)**

관리자 권한으로 PowerShell을 실행하고 다음 명령을 실행:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**방법 2: npx 사용 (자동 처리)**

이 프로젝트는 **npx를 우선적으로 사용**하도록 구현되어 있습니다. 
npm이 직접 실행되지 않아도 npx를 통해 OpenCode를 자동으로 다운로드하고 실행할 수 있습니다.

**방법 3: CMD 사용**

PowerShell 대신 명령 프롬프트(CMD)를 사용:

```cmd
npm --version
npm install -g @opencode-ai/cli
```

## OpenCode 설치

### 자동 설치 (npx 사용 - 권장)

코드에서 자동으로 npx를 통해 OpenCode를 실행하므로 별도 설치가 필요 없습니다.

### 수동 설치

**전역 설치:**
```bash
npm install -g @opencode-ai/cli
```

**또는 공식 설치 스크립트 (Linux/Mac):**
```bash
curl -fsSL https://opencode.ai/install | bash
```

## 초기 설정

OpenCode를 처음 사용할 때 초기 설정이 필요합니다:

```bash
opencode init
```

또는 npx 사용:
```bash
npx -y @opencode-ai/cli init
```

설정 항목:
1. 기본 모델 제공자 선택 (Ollama/OpenAI/Anthropic)
2. 샌드박스 모드 설정
3. 기본 플러그인 선택

## API 키 설정 (선택사항)

클라우드 모델(OpenAI, Anthropic)을 사용하는 경우:

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."
$env:OPENAI_API_KEY="sk-..."
```

**Windows (CMD):**
```cmd
set ANTHROPIC_API_KEY=sk-ant-...
set OPENAI_API_KEY=sk-...
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

영구적으로 설정하려면 환경 변수 설정 파일에 추가하세요.

## 확인

설치가 완료되었는지 확인:

```bash
opencode --version
```

또는 npx 사용:
```bash
npx -y @opencode-ai/cli --version
```

## 문제 해결

### npx가 작동하지 않는 경우

1. Node.js가 올바르게 설치되었는지 확인:
   ```bash
   node --version
   ```

2. npm 캐시 정리:
   ```bash
   npm cache clean --force
   ```

3. 네트워크 연결 확인

### 실행 정책 오류가 계속 발생하는 경우

1. 관리자 권한으로 PowerShell 실행
2. 실행 정책 확인:
   ```powershell
   Get-ExecutionPolicy
   ```
3. 실행 정책 변경:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

## 참고

- 이 프로젝트는 npx를 우선적으로 사용하므로 npm 전역 설치가 필수는 아닙니다.
- npx는 패키지를 자동으로 다운로드하고 실행하므로 첫 실행 시 약간의 시간이 걸릴 수 있습니다.
