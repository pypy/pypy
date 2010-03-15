setlocal

set ROOTDIR=%~dp0..\..
cd %ROOTDIR%

set ZIPEXE=zip
set PYTHON=c:\python26\python.exe
set TRANSLATE=pypy/translator/goal/translate.py
set TRANSLATEOPTS=--batch
set TARGET=pypy/translator/goal/targetpypystandalone
set TARGETOPTS=

copy /y ..\expat-2.0.1\win32\bin\release\libexpat.dll .

call :make_pypy pypy-1.2-win32.zip           pypy.exe           -Ojit
call :make_pypy pypy-1.2-win32-nojit.zip     pypy-nojit.exe
call :make_pypy pypy-1.2-win32-stackless.zip pypy-stackless.exe --stackless
REM call :make_pypy pypy-1.2-win32-sandbox.zip   pypy-sandbox.exe   --sandbox

goto :EOF

REM =========================================
:make_pypy
REM make_pypy subroutine
REM %1 is the zip filename
REM %2 is pypy.exe filename
REM %3 and others are the translation options

set ZIPFILE=%1
set PYPYEXE=%2
set EXTRAOPTS=%3 %4 %5 %6 %7 %8 %9

%PYTHON% %TRANSLATE% --output=%PYPYEXE% %TRANSLATEOPTS% %EXTRAOPTS% %TARGET% %TARGETOPTS%
del %ZIPFILE%
del /s pypy\lib\*.pyc lib-python\*.pyc
%ZIPEXE%    %ZIPFILE% %PYPYEXE% *.dll
%ZIPEXE% -r %ZIPFILE% pypy\lib lib-python
%ZIPEXE% -d %ZIPFILE% lib-python\2.5.2\plat-*
