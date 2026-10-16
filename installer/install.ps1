<#
  모션 스튜디오 + Claude Code(Opus 5.5) 설치 스크립트
  Install_MotionStudio.cmd 를 더블클릭하면 이 스크립트가 실행됩니다.
  이미 설치한 PC에서 다시 실행하면 엔진·템플릿·도구·스킬만 새 버전으로 바꾸고, 만들어 둔 브랜드와 영상은 그대로 둡니다.

  옵션:
    -Target <폴더>  설치 위치 (기본: 문서\motion-studio)
    -DryRun         아무것도 설치하거나 바꾸지 않고, 무엇이 필요한지만 점검합니다.
    -Yes            모든 질문에 기본값으로 답합니다.
#>
param(
    [string]$Target,
    [switch]$DryRun,
    [switch]$Yes
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { $Host.UI.RawUI.WindowTitle = '모션 스튜디오 설치' } catch {}

$Model = 'claude-opus-5-5'
$ProjectName = 'motion-studio'
$ShortcutName = '모션 스튜디오 (Claude Code).lnk'
$AppShortcutName = '모션 스튜디오.lnk'
$Here = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$Payload = Join-Path $Here $ProjectName
# GitHub 에서 'Download ZIP' 으로 받은 경우: installer 폴더 바로 위가 프로그램 폴더
if (-not (Test-Path (Join-Path $Payload 'tools\build.py')) -and (Test-Path (Join-Path (Split-Path $Here -Parent) 'tools\build.py'))) {
    $Payload = Split-Path $Here -Parent
}
if (-not $Target) { $Target = Join-Path ([Environment]::GetFolderPath('MyDocuments')) $ProjectName }
$Summary = New-Object System.Collections.Generic.List[string]

function Step($n, $msg) { Write-Host ''; Write-Host "[$n/8] $msg" -ForegroundColor Cyan }
function Info($msg) { Write-Host "      $msg" }
function Good($msg) { Write-Host "      $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "      $msg" -ForegroundColor Yellow }
function Note($msg) { $Summary.Add($msg) | Out-Null }

function Ask($question, [bool]$default = $true) {
    if ($Yes) { return $default }
    $suffix = if ($default) { '[Y/n]' } else { '[y/N]' }
    $answer = Read-Host "      $question $suffix"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $default }
    return @('y', 'yes', '예', '네', 'ㅛ') -contains $answer.Trim().ToLower()
}

function Has($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = (@($machine, $user) | Where-Object { $_ }) -join ';'
}

function Add-UserPath($dir) {
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $parts = @(); if ($user) { $parts = $user -split ';' | Where-Object { $_ } }
    if ($parts -notcontains $dir) {
        if (-not $DryRun) { [Environment]::SetEnvironmentVariable('Path', (($parts + $dir) -join ';'), 'User') }
        Info "사용자 PATH에 추가: $dir"
    }
    if (($env:Path -split ';') -notcontains $dir) { $env:Path = "$env:Path;$dir" }
}

function Install-WithWinget($id, [string[]]$extra = @()) {
    if ($DryRun) { Info "(점검 모드) 설치 예정: winget install --id $id"; return $true }
    if (-not (Has 'winget')) { Warn "winget 이 없어서 $id 를 설치하지 못했어요. 직접 설치한 뒤 이 설치 프로그램을 다시 실행해 주세요."; return $false }
    $wargs = @('install', '--id', $id, '-e', '--source', 'winget', '--accept-source-agreements', '--accept-package-agreements') + $extra
    & winget @wargs | Out-Host
    $code = $LASTEXITCODE
    Update-SessionPath
    # 0 = 설치됨, -1978335189(0x8A15002B) = 이미 최신 버전
    return ($code -eq 0 -or $code -eq -1978335189)
}

function Find-Python {
    $candidates = New-Object System.Collections.Generic.List[string]
    if (Has 'py') {
        try {
            $exe = & py -3 -c "import sys;print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $exe) { $candidates.Add(($exe | Select-Object -First 1).Trim()) }
        } catch {}
    }
    Get-Command python -All -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -and $_.Source -notlike '*\WindowsApps\*' } |
        ForEach-Object { $candidates.Add($_.Source) }
    Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "$env:ProgramFiles\Python3*\python.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | ForEach-Object { $candidates.Add($_.FullName) }
    foreach ($c in ($candidates | Select-Object -Unique)) {
        try {
            $v = & $c -c "import sys;print(sys.version_info[0]*100+sys.version_info[1])" 2>$null
            if ($LASTEXITCODE -eq 0 -and [int]($v | Select-Object -First 1) -ge 310) { return $c }
        } catch {}
    }
    return $null
}

# robocopy 종료 코드 0~7은 성공
function Robo([string[]]$roboArgs) {
    & robocopy @roboArgs /NFL /NDL /NJH /NJS /NP | Out-Null
    return ($LASTEXITCODE -lt 8)
}

Write-Host '=========================================================' -ForegroundColor DarkYellow
Write-Host '  모션 스튜디오 + Claude Code (Opus 5.5) 설치' -ForegroundColor Yellow
if ($DryRun) { Write-Host '  점검 모드: 아무것도 설치하거나 바꾸지 않습니다' -ForegroundColor Yellow }
Write-Host '=========================================================' -ForegroundColor DarkYellow
Info "설치 위치: $Target"
if ($Target -match 'OneDrive') {
    Warn '설치 위치가 OneDrive 로 동기화되는 폴더예요. 렌더 파일이 많이 동기화되거나 파일이 잠겨 오류가 날 수 있어요.'
    Warn '원하면 -Target 옵션으로 다른 곳에 설치하세요. 예) powershell -ExecutionPolicy Bypass -File .\install.ps1 -Target C:\motion-studio'
    Note '설치 위치가 OneDrive 폴더'
}

# ---------------------------------------------------------------- 1. winget
Step 1 'Windows 패키지 관리자(winget) 확인'
if (-not (Has 'winget')) {
    # 이미 필요한 게 다 깔려 있으면 winget 없이도 계속 (설치가 필요한 단계에서만 안내)
    Warn 'winget이 없습니다. Python·ffmpeg 가 이미 있으면 그대로 진행하고, 없으면 그 단계에서 안내할게요.'
    Warn 'winget: Microsoft Store 의 "앱 설치 관리자(App Installer)" https://apps.microsoft.com/detail/9NBLGGH4NNS1'
    Note 'winget 없음 (필요하면 앱 설치 관리자 설치)'
} else { Good 'winget 있음' }

# ---------------------------------------------------------------- 2. Claude Code
Step 2 'Claude Code'
$claudeBin = Join-Path $env:USERPROFILE '.local\bin'
if (Test-Path (Join-Path $claudeBin 'claude.exe')) { Add-UserPath $claudeBin }
if (Has 'claude') {
    Good ("이미 설치됨: " + ((& claude --version 2>$null) | Select-Object -First 1))
} elseif ($DryRun) {
    Info '(점검 모드) 설치 예정: irm https://claude.ai/install.ps1 | iex'
} else {
    Info '공식 설치 스크립트로 설치합니다...'
    & powershell -NoProfile -ExecutionPolicy Bypass -Command 'irm https://claude.ai/install.ps1 | iex'
    Update-SessionPath
    if (Test-Path (Join-Path $claudeBin 'claude.exe')) { Add-UserPath $claudeBin }
    if (Has 'claude') { Good ("설치됨: " + ((& claude --version 2>$null) | Select-Object -First 1)) }
    else { Warn 'Claude Code 설치를 확인하지 못했습니다. 새 PowerShell 창에서 claude --version 을 실행해 보세요.'; Note 'Claude Code 설치 확인 필요' }
}

# ---------------------------------------------------------------- 3. Git (선택)
Step 3 'Git for Windows (선택: Claude Code가 Bash 도구를 쓸 수 있게 해 줌)'
if (Has 'git') { Good 'Git 있음' }
elseif (Ask 'Git for Windows를 설치할까요? (관리자 확인 창이 뜰 수 있어요)' $true) {
    if (Install-WithWinget 'Git.Git') { Good 'Git 설치 완료' } else { Warn 'Git 설치에 실패했습니다. 없어도 PowerShell로 작업할 수 있습니다.' }
} else { Info '건너뜀 (Claude Code는 PowerShell로 명령을 실행합니다)' }

# ---------------------------------------------------------------- 4. Python
Step 4 'Python 3.10 이상'
$py = Find-Python
if ($py) { Good "있음: $py" }
else {
    Info 'Python 3.12를 설치합니다...'
    $ok = Install-WithWinget 'Python.Python.3.12' @('--override', '/quiet InstallAllUsers=0 InstallLauncherAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0')
    if (-not $DryRun) {
        $py = Find-Python
        if ($py) { Good "설치됨: $py" } else { Warn 'Python을 찾지 못했습니다. 창을 닫고 Install_MotionStudio.cmd 를 다시 실행해 주세요.'; exit 1 }
    }
}

# ---------------------------------------------------------------- 5. ffmpeg
Step 5 'ffmpeg (MP4 인코딩)'
$wingetLinks = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links'
if (-not (Has 'ffmpeg') -and (Test-Path (Join-Path $wingetLinks 'ffmpeg.exe'))) { Add-UserPath $wingetLinks }
if (Has 'ffmpeg') { Good 'ffmpeg 있음' }
else {
    $ok = Install-WithWinget 'Gyan.FFmpeg'
    if (-not $DryRun) {
        if (Test-Path (Join-Path $wingetLinks 'ffmpeg.exe')) { Add-UserPath $wingetLinks }
        if (Has 'ffmpeg') { Good 'ffmpeg 설치 완료' } else { Warn 'ffmpeg를 찾지 못했습니다. 새 창에서 ffmpeg -version 을 확인해 주세요.'; Note 'ffmpeg 확인 필요' }
    }
}

# ---------------------------------------------------------------- 6. 스튜디오 폴더
Step 6 "스튜디오 폴더 준비 ($Target)"
# 켜져 있는 모션 스튜디오 앱(예전 버전)을 끔. 안 끄면 새로 설치해도 창이 예전 코드로 계속 돌아감
$runningApp = @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -like "*$ProjectName*tools*app.py*" })
if ($runningApp.Count -gt 0) {
    if ($DryRun) { Info "(점검 모드) 켜져 있는 모션 스튜디오 앱 $($runningApp.Count)개를 끌 예정" }
    else {
        Info '켜져 있는 모션 스튜디오 앱을 끕니다 (설치가 끝나면 새 버전으로 다시 열려요).'
        $runningApp | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 1
    }
}
if (-not (Test-Path (Join-Path $Payload 'tools\build.py'))) {
    Warn "설치할 파일($ProjectName)이 옆에 없습니다. 압축을 먼저 풀고, 풀린 폴더에서 Install_MotionStudio.cmd 를 실행하세요."
    if (-not $DryRun) { exit 1 }
} else {
    $same = (Test-Path $Target) -and ((Resolve-Path $Target).Path -eq (Resolve-Path $Payload).Path)
    if ($same) { Good '이미 설치 위치에 있습니다' }
    elseif (-not (Test-Path $Target)) {
        if ($DryRun) { Info "(점검 모드) $Payload → $Target 새로 복사 예정" }
        else {
            New-Item -ItemType Directory -Force -Path (Split-Path $Target -Parent) | Out-Null
            Copy-Item -LiteralPath $Payload -Destination $Target -Recurse
            Good '복사 완료'
        }
    }
    elseif ($DryRun) { Info "(점검 모드) 이미 설치돼 있음 → 백업 후 엔진·템플릿·도구·스킬 업데이트 예정 (brands, videos, out 은 그대로)" }
    else {
        Info '이미 설치돼 있습니다. 만들어 둔 브랜드·영상은 그대로 두고 엔진·템플릿·도구·스킬만 새 버전으로 바꿉니다.'
        if (Ask '계속할까요? (먼저 out 폴더를 뺀 전체를 백업해 둡니다)' $true) {
            $backup = "$Target-backup-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
            if (Robo @($Target, $backup, '/E', '/XD', (Join-Path $Target 'out'))) { Info "백업: $backup"; Note "이전 버전 백업 위치: $backup" }
            else { Warn '백업에 실패해서 업데이트를 멈췄습니다.'; exit 1 }
            # 브랜드·영상: 없는 파일(새 예시)만 추가
            $okA = Robo @($Payload, $Target, '/E', '/XD', (Join-Path $Payload 'brands'), (Join-Path $Payload 'videos'), (Join-Path $Payload 'out'))
            $okB = $true; $okC = $true
            if (Test-Path (Join-Path $Payload 'brands')) { $okB = Robo @((Join-Path $Payload 'brands'), (Join-Path $Target 'brands'), '/E', '/XC', '/XN', '/XO') }
            if (Test-Path (Join-Path $Payload 'videos')) { $okC = Robo @((Join-Path $Payload 'videos'), (Join-Path $Target 'videos'), '/E', '/XC', '/XN', '/XO') }
            # 예시 필름의 화면 렌더(master.mp4): 없는 것만 넣어 둠 → 앱에서 '음악만 다시 합치기'가 바로 됨
            $okD = $true
            if (Test-Path (Join-Path $Payload 'out')) { $okD = Robo @((Join-Path $Payload 'out'), (Join-Path $Target 'out'), '/E', '/XC', '/XN', '/XO') }
            if ($okA -and $okB -and $okC -and $okD) { Good '업데이트 완료' } else { Warn '일부 파일을 복사하지 못했습니다.'; Note '업데이트 중 복사 오류 확인 필요' }
        } else { Info '건너뜀 (기존 폴더 그대로 사용)' }
    }
}

# ---------------------------------------------------------------- 7. 파이썬 패키지 + 크로미움
Step 7 '빌드·렌더 도구 (Python 패키지, 렌더링용 크로미움)'
$env:PYTHONUTF8 = '1'
if ($DryRun) { Info '(점검 모드) pip install -r requirements.txt, python -m playwright install chromium 예정' }
elseif ($py) {
    Push-Location $Target
    & $py -m pip install --upgrade pip --disable-pip-version-check | Out-Host
    & $py -m pip install -r requirements.txt --disable-pip-version-check | Out-Host
    if ($LASTEXITCODE -ne 0) { Warn 'Python 패키지 설치 중 오류가 났습니다. 위 메시지를 확인해 주세요.'; Note 'pip 설치 오류 확인 필요' }
    & $py -m playwright install chromium | Out-Host
    if ($LASTEXITCODE -ne 0) { Warn '크로미움 설치 중 오류가 났습니다.'; Note '크로미움 설치 오류 확인 필요' }
    if (Ask '로고·캐릭터 배경 지우기 도구(rembg, 약 500MB)도 설치할까요? 나중에 필요할 때 해도 됩니다.' $false) {
        & $py -m pip install -r requirements-tools.txt --disable-pip-version-check | Out-Host
        if ($LASTEXITCODE -ne 0) { Warn '배경 지우기 도구 설치 중 오류가 났습니다.'; Note 'rembg 설치 오류 확인 필요' }
        # rembg 가 쓰는 onnxruntime 은 Visual C++ 재배포 패키지가 없으면 실행하자마자 죽을 수 있음 (오류 코드 3221225477)
        if (Has 'winget') { Install-WithWinget 'Microsoft.VCRedist.2015+.x64' | Out-Null }
        & $py -c "import onnxruntime" 2>$null
        if ($LASTEXITCODE -ne 0) { Warn '배경 지우기 AI 도구가 이 PC에서 실행되지 않아요. 앱은 단순 방식(단색 배경 지우기)으로 대신 지워요.'; Note '배경 지우기는 단순 방식으로 동작' }
    }
    Pop-Location
}

# ---------------------------------------------------------------- 8. 모델 설정, 바로가기, 시험 렌더
Step 8 'Opus 5.5 설정, 바탕화면 바로가기, 시험 렌더'
Info "스튜디오 폴더는 .claude\settings.json 에 $Model 이 지정돼 있습니다."
$userSettings = Join-Path $env:USERPROFILE '.claude\settings.json'
if (Ask '이 PC의 다른 폴더에서도 Claude Code 기본 모델을 Opus 5.5로 할까요?' $true) {
    if ($DryRun) { Info "(점검 모드) $userSettings 의 model 을 $Model 로 설정 예정" }
    else {
        $utf8 = New-Object System.Text.UTF8Encoding($false)
        New-Item -ItemType Directory -Force -Path (Split-Path $userSettings -Parent) | Out-Null
        if (Test-Path $userSettings) {
            try {
                $raw = [System.IO.File]::ReadAllText($userSettings)
                $obj = $raw | ConvertFrom-Json
                Copy-Item $userSettings "$userSettings.bak" -Force
                if ($obj.PSObject.Properties.Name -contains 'model') { $obj.model = $Model }
                else { $obj | Add-Member -NotePropertyName 'model' -NotePropertyValue $Model }
                [System.IO.File]::WriteAllText($userSettings, ($obj | ConvertTo-Json -Depth 64), $utf8)
                Good "사용자 설정에 반영 (이전 파일: settings.json.bak)"
            } catch { Warn "기존 사용자 설정을 읽지 못해 건드리지 않았습니다. Claude Code 안에서 /model 로 Opus를 고르면 됩니다." }
        } else {
            [System.IO.File]::WriteAllText($userSettings, "{`n  `"model`": `"$Model`"`n}`n", $utf8)
            Good '사용자 설정 만듦'
        }
    }
}

$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop $ShortcutName
$appLnkPath = Join-Path $desktop $AppShortcutName
$safeTarget = $Target.Replace("'", "''")
if ($DryRun) { Info "(점검 모드) 바로가기 만들 예정: $appLnkPath, $lnkPath" }
else {
    # 화면으로 쓰는 앱 (콘솔 창 없이 pythonw 로 실행)
    $shellA = New-Object -ComObject WScript.Shell
    $pyw = if ($py) { Join-Path (Split-Path $py -Parent) 'pythonw.exe' } else { $null }
    if ($pyw -and (Test-Path $pyw)) {
        $alnk = $shellA.CreateShortcut($appLnkPath)
        $alnk.TargetPath = $pyw
        $alnk.Arguments = '"' + (Join-Path $Target 'tools\app.py') + '"'
        $alnk.WorkingDirectory = $Target
        $ico = Join-Path $Target 'app\icon.ico'
        if (Test-Path $ico) { $alnk.IconLocation = "$ico,0" }
        $alnk.Description = '모션 스튜디오 앱 (광고 모션 그래픽 만들기)'
        $alnk.Save()
        Good "바로가기: $appLnkPath"
    } else {
        Warn 'pythonw.exe 를 찾지 못해 앱 바로가기를 만들지 못했습니다. 스튜디오 폴더의 StudioApp.cmd 로 열 수 있어요.'
        Note '앱 바로가기 대신 StudioApp.cmd 사용'
    }
    # StudioApp.cmd·StudioApp_debug.cmd 가 패키지를 설치한 바로 그 파이썬을 쓰게 (PATH 의 다른 파이썬 말고)
    if ($py -and (Test-Path $py)) {
        $oem = [System.Text.Encoding]::GetEncoding([Console]::OutputEncoding.CodePage)
        $runW = if ($pyw -and (Test-Path $pyw)) { "start `"`" `"$pyw`" tools\app.py" } else { "start `"`" `"$py`" tools\app.py" }
        [System.IO.File]::WriteAllText((Join-Path $Target 'StudioApp.cmd'), "@echo off`r`ncd /d `"%~dp0`"`r`n$runW`r`n", $oem)
        [System.IO.File]::WriteAllText((Join-Path $Target 'StudioApp_debug.cmd'), "@echo off`r`ncd /d `"%~dp0`"`r`nset PYTHONUTF8=1`r`necho Motion Studio - debug mode. Keep this window open and send a screenshot if an error appears.`r`n`"$py`" tools\app.py`r`npause`r`n", $oem)
    }
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($lnkPath)
    $lnk.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $lnk.Arguments = "-NoExit -ExecutionPolicy Bypass -Command `"`$env:PYTHONUTF8='1'; Set-Location -LiteralPath '$safeTarget'; claude`""
    $lnk.WorkingDirectory = $Target
    $claudeExe = Join-Path $claudeBin 'claude.exe'
    if (Test-Path $claudeExe) { $lnk.IconLocation = "$claudeExe,0" }
    $lnk.Description = '모션 스튜디오 폴더에서 Claude Code 시작'
    $lnk.Save()
    Good "바로가기: $lnkPath"
}

# 구글 Gemini API 키 (앱의 '음악 만들기' 자동 생성용, 선택). PC마다 사용자 폴더에만 저장
$msSettings = Join-Path $env:USERPROFILE '.motion-studio\settings.json'
$hasKey = $false
if (Test-Path $msSettings) { try { $hasKey = [bool]((Get-Content $msSettings -Raw -Encoding UTF8 | ConvertFrom-Json).gemini_api_key) } catch {} }
if ($hasKey) { Good 'Gemini API 키가 이미 저장돼 있어요 (음악 만들기 자동).' }
elseif ($DryRun -or $Yes -or -not $py) { Info 'Gemini API 키는 나중에 앱의 설정 탭 > 음악 만들기에서 넣을 수 있어요.' }
else {
    Info '앱의 "음악 만들기"를 자동으로 쓰려면 구글 Gemini API 키가 필요해요 (곡당 약 0.04~0.08달러, 결제 연결 필요).'
    Info '없으면 그냥 엔터를 누르세요. 나중에 앱 설정 탭에서 넣거나, Gemini 앱으로 무료로 만들 수 있어요.'
    $sec = Read-Host '      Gemini API 키 (AIza…로 시작, 입력은 가려져요)' -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
    if (-not [string]::IsNullOrWhiteSpace($plain)) {
        $plain.Trim() | & $py (Join-Path $Target 'tools\music.py') key --stdin | Out-Host
        if ($LASTEXITCODE -eq 0) { Good 'Gemini API 키를 저장했어요.' } else { Warn 'Gemini API 키를 저장하지 못했어요. 앱 설정 탭에서 다시 넣어 주세요.' }
    }
    $plain = $null
}

if ($DryRun) { Info '(점검 모드) 시험 빌드·렌더 생략' }
elseif ($py) {
    Push-Location $Target
    if (Test-Path (Join-Path $Target 'videos\haru-weekend-event\video.json')) {
        & $py tools\build.py haru-weekend-event tall | Out-Host
        & $py tools\render.py haru-weekend-event tall shots 1.5 | Out-Host
        $shot = Join-Path $Target 'out\haru-weekend-event\tall\shots\t001.50.png'
        if (Test-Path $shot) { Good "시험 렌더 성공: $shot" } else { Warn '시험 렌더 결과가 없습니다. 위 오류 메시지를 확인해 주세요.'; Note '시험 렌더 실패' }
    } else {
        # GitHub ZIP 으로 설치하면 예시 영상이 없어서, 렌더용 크로미움이 뜨는지만 봄
        & $py -c "from playwright.sync_api import sync_playwright as s; p = s().start(); b = p.chromium.launch(); b.close(); p.stop(); print('chromium ok')" | Out-Host
        if ($LASTEXITCODE -eq 0) { Good '렌더용 크로미움 준비 완료' } else { Warn '렌더용 크로미움을 띄우지 못했습니다. 위 오류 메시지를 확인해 주세요.'; Note '크로미움 점검 실패' }
    }
    & $py -c "import sys; sys.path.insert(0, 'tools'); import app; print('app ok')" | Out-Host
    if ($LASTEXITCODE -eq 0) { Good '앱 준비 완료' } else { Warn '앱을 불러오지 못했습니다. 위 오류 메시지를 확인해 주세요.'; Note '앱 점검 실패' }
    Pop-Location
}

# ---------------------------------------------------------------- 마무리
Write-Host ''
Write-Host '=========================================================' -ForegroundColor DarkYellow
if ($DryRun) { Write-Host '  점검 끝 (아무것도 바꾸지 않았습니다)' -ForegroundColor Green }
elseif ($Summary.Count -eq 0) { Write-Host '  설치 끝' -ForegroundColor Green }
else { Write-Host '  설치는 끝났지만 확인할 것이 있습니다:' -ForegroundColor Yellow; $Summary | ForEach-Object { Write-Host "   - $_" -ForegroundColor Yellow } }
Write-Host '=========================================================' -ForegroundColor DarkYellow
if (-not $DryRun) {
    Info '바탕화면 아이콘이 두 개 생겼어요.'
    Info '  "모션 스튜디오": 화면으로 쓰는 앱 (계정·문구·사진·미리보기·MP4)'
    Info '  "모션 스튜디오 (Claude Code)": 말로 시키는 Claude Code'
    Info 'Claude Code를 처음 열면 브라우저가 열리고 Claude 계정으로 로그인합니다 (Pro·Max·Team·Enterprise).'
    Info '앱의 "Claude에게 문구 맡기기"도 이 로그인을 씁니다. 먼저 Claude Code에서 한 번 로그인해 주세요.'
    if (Ask '지금 Claude Code를 열어 로그인할까요?' $true) { Start-Process -FilePath $lnkPath }
    if ((Test-Path $appLnkPath) -and (Ask '모션 스튜디오 앱도 열까요?' $true)) { Start-Process -FilePath $appLnkPath }
}
