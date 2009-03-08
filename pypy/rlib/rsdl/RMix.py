import sys
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform as platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rsdl import RSDL


if sys.platform == 'darwin':
    eci = ExternalCompilationInfo(
        includes = ['SDL_mixer.h'],
        frameworks = ['SDL_mixer'],
        include_dirs = ['/Library/Frameworks/SDL_Mixer.framework/Headers']
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

    Chunk              = platform.Struct('Mix_Chunk', [('allocated', rffi.INT),
                                                       ('abuf', RSDL.Uint8P),
                                                       ('alen', RSDL.Uint32),
                                                       ('volume', RSDL.Uint8)])

globals().update(platform.configure(CConfig))

ChunkPtr.TO.become(Chunk)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

OpenAudio = external('Mix_OpenAudio',
                     [rffi.INT, RSDL.Uint16, rffi.INT, rffi.INT],
                     rffi.INT)

CloseAudio = external('Mix_CloseAudio', [], lltype.Void)

LoadWAV_RW   = external('Mix_LoadWAV_RW',
                     [RSDL.RWopsPtr, rffi.INT],
                     ChunkPtr)

def LoadWAV(filename_ccharp):
    return LoadWAV_RW(RSDL.RWFromFile(filename_ccharp, rffi.str2charp('rb')), 1)

PlayChannelTimed = external('Mix_PlayChannelTimed',
                       [rffi.INT, ChunkPtr, rffi.INT, rffi.INT],
                       rffi.INT)

def PlayChannel(channel,chunk,loops):
    return PlayChannelTimed(channel, chunk, loops, -1)
