@echo off
setlocal

if not exist ".env" (
  if exist "env.example" (
    copy "env.example" ".env" >NUL
  )
)

python scripts\smoke_paper.py
exit /b %ERRORLEVEL%
