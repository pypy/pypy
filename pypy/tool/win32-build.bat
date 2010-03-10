setlocal

set ROOTDIR=%~dp0..\..
cd %ROOTDIR%

set PYTHON=c:\python26\python.exe
set TRANSLATE=pypy/translator/goal/translate.py
set TRANSLATEOPTS=--batch
set TARGET=pypy/translator/goal/targetpypystandalone
set TARGETOPTS=

%PYTHON% %TRANSLATE%             --output=pypy-c.exe         %TRANSLATEOPTS% %TARGET% %TARGETOPTS%
%PYTHON% %TRANSLATE% -Ojit       --output=pypy-jit.exe       %TRANSLATEOPTS% %TARGET% %TARGETOPTS%
%PYTHON% %TRANSLATE% --stackless --output=pypy-stackless.exe %TRANSLATEOPTS% %TARGET% %TARGETOPTS%
%PYTHON% %TRANSLATE% --sandbox   --output=pypy-sandbox.exe   %TRANSLATEOPTS% %TARGET% %TARGETOPTS%

set ZIP=zip.exe
set ZIPFILE=pypy-1.2-win32.zip
copy ..\expat-2.0.1\win32\bin\release\libexpat.dll .

del /s pypy\lib\*.pyc lib-python\*.pyc
del    %ZIPFILE%
%ZIP%    %ZIPFILE% *.exe *.dll
%ZIP% -r %ZIPFILE% pypy\lib lib-python
%ZIP% -d %ZIPFILE% lib-python\2.5.2\plat-*
