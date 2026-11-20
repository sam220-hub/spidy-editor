@echo off
rem ghost - the old name of the skill's command; kept so existing notes keep working.
rem spidy.cmd holds the real launcher (it finds Python and refreshes PATH).
call "%~dp0spidy.cmd" %*
exit /b %ERRORLEVEL%
