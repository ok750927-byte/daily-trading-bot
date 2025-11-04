@echo off
echo Removing build and dist directories...
rmdir /S /Q build 2>nul
rmdir /S /Q dist 2>nul
rmdir /S /Q dist_release 2>nul
for /D %%I in (dist_pyinstaller*) do rmdir /S /Q "%%I" 2>nul
necho Clean complete.
