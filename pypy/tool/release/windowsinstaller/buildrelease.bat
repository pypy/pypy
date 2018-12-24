@setlocal
@echo off


set D=%~dp0
set PCBUILD=%D%..\..\..\..\PCbuild\
if "%Py_OutDir%"=="" set Py_OutDir=%PCBUILD%
set EXTERNALS=%D%..\..\externals\windows-installer\

set BUILDX86=
set BUILDX64=
set TARGET=Rebuild
set TESTTARGETDIR=
set PGO=-m test -q --pgo
set BUILDNUGET=1
set BUILDZIP=1


:CheckOpts
if "%1" EQU "-h" goto Help
if "%1" EQU "-o" (set OUTDIR=%~2) && shift && shift && goto CheckOpts
if "%1" EQU "--out" (set OUTDIR=%~2) && shift && shift && goto CheckOpts


if "%1" NEQ "" echo Invalid option: "%1" && exit /B 1

if not defined BUILDX86 if not defined BUILDX64 (set BUILDX86=1) && (set BUILDX64=1)

call "%PCBUILD%find_msbuild.bat" %MSBUILD%
if ERRORLEVEL 1 (echo Cannot locate MSBuild.exe on PATH or as MSBUILD variable & exit /b 2)


%MSBUILD% "%D%bundle\releaselocal.wixproj" /t:Rebuild /p:RebuildAll=true
if errorlevel 1 exit /B

exit /B 0

:Help
echo buildrelease.bat [--out DIR]
echo                  [-h]
echo.
echo    --out (-o)          Specify an additional output directory for installers
echo    -h                  Display this help information
echo.
