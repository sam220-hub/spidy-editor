@echo off
rem spidy - the skill's command on Windows. Same steps as: python scripts\ghost.py ...
rem Put this folder on PATH, or call it with its full path: D:\path\spidy doctor
rem
rem It finds Python itself. An editor or service that was already running when Python was installed
rem still has the old PATH, where "python" is only the Microsoft Store alias: that one opens the
rem Store and runs nothing, so the launcher looks for a real interpreter instead.
setlocal EnableExtensions
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "SPIDY_PY="
set "SPIDY_PY_ARGS="

rem 1) python.exe on PATH, skipped when it is the WindowsApps store alias
rem    (findstr is literal with /c:, and a trailing \" would be read as an escaped quote)
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
  if not defined SPIDY_PY echo %%I| findstr /i /c:"WindowsApps" >nul || set "SPIDY_PY=%%I"
)
rem 2) the per-user and per-machine folders winget and python.org install into
if not defined SPIDY_PY for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if not defined SPIDY_PY if exist "%%D\python.exe" set "SPIDY_PY=%%D\python.exe"
if not defined SPIDY_PY for /d %%D in ("%ProgramFiles%\Python3*") do if not defined SPIDY_PY if exist "%%D\python.exe" set "SPIDY_PY=%%D\python.exe"
rem 3) the py launcher, asked for 3.x (it lives next to the per-user installs)
if not defined SPIDY_PY if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set "SPIDY_PY=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" & set "SPIDY_PY_ARGS=-3"
if not defined SPIDY_PY if exist "%ProgramFiles%\Python Launcher\py.exe" set "SPIDY_PY=%ProgramFiles%\Python Launcher\py.exe" & set "SPIDY_PY_ARGS=-3"
if not defined SPIDY_PY (
  echo spidy: no Python found. Install it with: winget install Python.Python.3.12 1>&2
  exit /b 9009
)
rem ghost.py refreshes PATH from the registry, so node, npx and ffmpeg are found even when this
rem shell started before they were installed
"%SPIDY_PY%" %SPIDY_PY_ARGS% "%~dp0scripts\ghost.py" %*
exit /b %ERRORLEVEL%
