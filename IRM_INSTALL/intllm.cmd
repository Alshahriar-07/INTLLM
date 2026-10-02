@echo off
rem INTLLM command shim.
rem Lets `intllm` (and `intllm --version` / `intllm --help`) launch the
rem installed application from a new terminal. It forwards all arguments to the
rem application executable that lives next to this script.
setlocal
"%~dp0INTLLM.exe" %*
exit /b %ERRORLEVEL%
