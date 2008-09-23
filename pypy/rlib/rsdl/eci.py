from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.tool.cbuild import CompilationError
import py
import sys

def get_rsdl_compilation_info():
    if sys.platform == 'darwin':
        eci = ExternalCompilationInfo(
            includes = ['SDL.h', 
                        #'Init.h',
                        #'SDLMain.m'
                        #'SDLMain.h'*/
                        ],
            include_dirs = ['/Library/Frameworks/SDL.framework/Versions/A/Headers',
                            #str(py.magic.autopath().dirpath().join('macosx-sdl-main'))
                            ],
            link_extra = [
                str(py.magic.autopath().dirpath().join('macosx-sdl-main/SDLMain.m')),
                #'macosx-sdl-main/SDLMain.m',
                '-I', '/Library/Frameworks/SDL.framework/Versions/A/Headers',
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
