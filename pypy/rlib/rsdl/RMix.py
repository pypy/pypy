from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform as platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rsdl import RSDL
import sys

if sys.platform == 'darwin':
    eci = ExternalCompilationInfo(
        includes = ['SDL_mixer.h'],
        frameworks = ['SDL_mixer'],
        include_dirs = ['/Library/Frameworks/SDL_Mixer.framework/Versions/A/Headers']
    )
else:
    eci = ExternalCompilationInfo(
        includes=['SDL_mixer.h'],
        libraries=['SDL_mixer'],
    )

eci = eci.merge(RSDL.eci)

ChunkPtr             = lltype.Ptr(lltype.ForwardReference())

class CConfig:
    _compilation_info_ = eci

    Chunk              = platform.Struct('Mix_Chunk', [])

globals().update(platform.configure(CConfig))

ChunkPtr.TO.become(Chunk)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

OpenAudio = external('Mix_OpenAudio',
                     [rffi.INT, RSDL.Uint16, rffi.INT, rffi.INT],
                     rffi.INT)

CloseAudio = external('Mix_CloseAudio', [], lltype.Void)

_LoadWAV   = external('Mix_LoadWAV_RW',
                     [RSDL.RWopsPtr, rffi.INT],
                     ChunkPtr)

def LoadWAV(filename_ccharp):
    _LoadWAV(RSDL.RWFromFile(filename_ccharp, rffi.str2charp('rb')), 1)


