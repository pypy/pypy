@echo off

SET ROMNAME=rom4

echo -- COMPILING
for %%S in (*.asm) do (
..\bin\rgbasm -o%%S.obj %%S
)
echo.

echo -- LINK FILE
echo [Objects] > link.txt
dir /b *.obj >> link.txt
echo [Output] >> link.txt
echo %ROMNAME%.gb >> link.txt
type link.txt
echo.

echo -- LINKING
..\bin\xlink -m%ROMNAME%.txt -n%ROMNAME%.sym link.txt
del link.txt
echo.

echo -- FIXING ROM
..\bin\rgbfix -v -p -t%ROMNAME% %ROMNAME%.gb
del *.obj
echo.

echo -- DONE