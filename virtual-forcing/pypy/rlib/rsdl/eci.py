from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import CompilationError
import py
import sys

def get_rsdl_compilation_info():
    if sys.platform == 'darwin':
        eci = ExternalCompilationInfo(
            includes = ['SDL.h'],
            include_dirs = ['/Library/Frameworks/SDL.framework/Headers'],
            link_files = [
                str(py.path.local(__file__).dirpath().join('macosx-sdl-main/SDLMain.m')),
            ],
            frameworks = ['SDL', 'Cocoa']
        )
    else:
        eci = ExternalCompilationInfo(
            includes=['SDL.h'],
            )
        eci = eci.merge(ExternalCompilationInfo.from_config_tool('sdl-config'))
    return eci

def check_sdl_installation():
    from pypy.rpython.tool import rffi_platform as platform
    platform.verify_eci(get_rsdl_compilation_info())

SDLNotInstalled = (ImportError, CompilationError)
