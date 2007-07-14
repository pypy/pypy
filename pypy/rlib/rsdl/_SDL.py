from ctypes import *


import pypy.rpython.rctypes.implementation
from pypy.rpython.rctypes.tool import util
from pypy.rpython.rctypes.tool.ctypes_platform import Library, configure

import distutils.errors

prefix = '/usr/local'

try:
    class CConfig:
        _header_ = ''
        _includes_ = ['SDL.h']
        _include_dirs_ = [prefix+'/include/SDL']
        SDL = Library('SDL')
    
    cconfig = configure(CConfig)
    libSDL = cconfig['SDL']
except distutils.errors.CCompilerError:
    libSDL = CDLL(prefix+'/lib/libSDL.dylib')

STRING = c_char_p
WSTRING = c_wchar_p

SDLK_w = 119
SDLK_KP3 = 259
SDL_NUMEVENTS = 32
SDL_KEYDOWNMASK = 4
DUMMY_ENUM_VALUE = 0
SDLK_2 = 50
SDL_EVENT_RESERVED5 = 21
CD_STOPPED = 1
SDLK_QUOTEDBL = 34
SDLK_6 = 54
SDLK_GREATER = 62
SDLK_WORLD_19 = 179
SDLK_WORLD_37 = 197
SDLK_WORLD_23 = 183
SDLK_t = 116
SDL_AUDIO_PLAYING = 1
SDL_EVENT_RESERVEDA = 14
SDL_VIDEORESIZEMASK = 65536
SDL_QUITMASK = 4096
SDL_SYSWMEVENTMASK = 8192
SDL_AUDIO_STOPPED = 0
KMOD_RSHIFT = 2
SDL_EVENT_RESERVED4 = 20
SDLK_WORLD_92 = 252
SDLK_KP_PERIOD = 266
SDLK_l = 108
SDLK_AT = 64
SDLK_KP_PLUS = 270
SDLK_WORLD_32 = 192
SDLK_KP5 = 261
SDL_JOYAXISMOTION = 7
SDLK_WORLD_88 = 248
SDLK_QUOTE = 39
SDLK_WORLD_21 = 181
SDLK_WORLD_95 = 255
SDLK_LCTRL = 306
SDLK_FIRST = 0
SDL_GL_SWAP_CONTROL = 16
SDL_JOYBUTTONDOWNMASK = 1024
SDLK_WORLD_44 = 204
SDLK_WORLD_30 = 190
SDLK_WORLD_82 = 242
SDLK_COLON = 58
SDL_GL_RED_SIZE = 0
SDLK_WORLD_94 = 254
SDL_GL_MULTISAMPLEBUFFERS = 13
SDL_UNSUPPORTED = 4
_ISupper = 256
SDLK_F12 = 293
__GCONV_IGNORE_ERRORS = 2
SDL_JOYBUTTONUP = 11
SDLK_CLEAR = 12
SDL_AUDIO_PAUSED = 2
SDLK_UNDO = 322
SDL_ACTIVEEVENT = 1
SDLK_MENU = 319
SDLK_LSHIFT = 304
SDLK_RALT = 307
SDLK_F4 = 285
_ISprint = 16384
SDLK_WORLD_75 = 235
_ISpunct = 4
SDLK_HASH = 35
SDL_MOUSEEVENTMASK = 112
SDL_EFREAD = 1
SDLK_F5 = 286
SDLK_WORLD_0 = 160
SDLK_KP_EQUALS = 272
SDL_GL_STENCIL_SIZE = 7
SDL_MOUSEBUTTONDOWNMASK = 32
SDLK_LEFTBRACKET = 91
SDLK_COMPOSE = 314
SDLK_WORLD_27 = 187
SDL_JOYEVENTMASK = 3968
SDLK_WORLD_68 = 228
SDLK_WORLD_89 = 249
SDL_JOYAXISMOTIONMASK = 128
SDLK_WORLD_2 = 162
SDLK_HELP = 315
SDL_GRAB_FULLSCREEN = 2
SDLK_KP0 = 256
SDLK_UNDERSCORE = 95
__GCONV_FULL_OUTPUT = 5
SDL_MOUSEMOTION = 4
SDL_GL_ACCUM_ALPHA_SIZE = 11
SDL_GRAB_OFF = 0
CD_PAUSED = 3
__GCONV_ILLEGAL_INPUT = 6
SDLK_WORLD_72 = 232
SDL_EVENT_RESERVED2 = 18
SDLK_PAGEUP = 280
SDLK_LEFT = 276
CD_PLAYING = 2
SDLK_WORLD_48 = 208
SDLK_F7 = 288
SDLK_WORLD_34 = 194
SDLK_WORLD_86 = 246
SDLK_WORLD_38 = 198
SDL_MOUSEBUTTONUP = 6
SDLK_SLASH = 47
KMOD_CAPS = 8192
SDLK_SYSREQ = 317
SDLK_0 = 48
SDLK_WORLD_62 = 222
SDLK_KP_MINUS = 269
SDL_GL_BUFFER_SIZE = 4
SDLK_WORLD_64 = 224
SDLK_BREAK = 318
SDL_FALSE = 0
SDLK_RETURN = 13
SDLK_POWER = 320
SDLK_WORLD_24 = 184
SDLK_WORLD_17 = 177
SDLK_PAGEDOWN = 281
SDL_GL_MULTISAMPLESAMPLES = 14
SDLK_F3 = 284
SDLK_8 = 56
SDLK_F2 = 283
SDLK_RIGHTPAREN = 41
SDLK_WORLD_36 = 196
SDLK_WORLD_84 = 244
SDLK_LALT = 308
CD_TRAYEMPTY = 0
SDLK_WORLD_55 = 215
SDL_KEYUPMASK = 8
SDLK_WORLD_93 = 253
SDLK_DOLLAR = 36
SDLK_UP = 273
SDLK_RIGHTBRACKET = 93
SDL_GL_ACCUM_BLUE_SIZE = 10
SDLK_j = 106
SDLK_WORLD_6 = 166
SDLK_KP8 = 264
SDLK_WORLD_18 = 178
SDLK_F8 = 289
SDLK_WORLD_69 = 229
SDLK_WORLD_61 = 221
SDLK_WORLD_45 = 205
SDLK_WORLD_31 = 191
SDLK_WORLD_83 = 243
SDL_JOYBALLMOTION = 8
SDLK_RMETA = 309
SDLK_TAB = 9
SDLK_x = 120
SDLK_WORLD_60 = 220
SDL_GL_DOUBLEBUFFER = 5
SDLK_SEMICOLON = 59
SDLK_KP_DIVIDE = 267
SDLK_WORLD_16 = 176
SDLK_WORLD_59 = 219
SDLK_F10 = 291
SDLK_WORLD_8 = 168
SDLK_KP1 = 257
SDLK_WORLD_14 = 174
SDLK_LMETA = 310
SDLK_WORLD_80 = 240
SDLK_WORLD_58 = 218
SDLK_WORLD_76 = 236
SDL_JOYHATMOTIONMASK = 512
SDLK_COMMA = 44
SDL_GL_STEREO = 12
SDLK_F6 = 287
SDL_EFSEEK = 3
SDLK_WORLD_90 = 250
SDLK_p = 112
KMOD_RESERVED = 32768
_ISdigit = 2048
SDL_VIDEOEXPOSEMASK = 131072
SDLK_WORLD_10 = 170
SDL_KEYDOWN = 2
SDLK_WORLD_66 = 226
__GCONV_ILLEGAL_DESCRIPTOR = 8
SDLK_WORLD_42 = 202
SDL_PEEKEVENT = 1
SDLK_WORLD_56 = 216
SDLK_WORLD_28 = 188
SDLK_LSUPER = 311
SDLK_F1 = 282
SDL_GL_GREEN_SIZE = 1
SDLK_EXCLAIM = 33
SDLK_WORLD_91 = 251
SDL_MOUSEBUTTONUPMASK = 64
SDL_LASTERROR = 5
__GCONV_INTERNAL_ERROR = 9
SDL_GRAB_QUERY = -1
__GCONV_EMPTY_INPUT = 4
SDLK_o = 111
SDL_ACTIVEEVENTMASK = 2
SDLK_RSUPER = 312
SDLK_KP6 = 262
__GCONV_NODB = 2
__GCONV_NOMEM = 3
SDLK_EURO = 321
SDL_GL_ALPHA_SIZE = 3
SDLK_WORLD_51 = 211
__GCONV_INCOMPLETE_INPUT = 7
SDLK_WORLD_20 = 180
SDLK_WORLD_54 = 214
SDL_SYSWMEVENT = 13
SDL_JOYBUTTONUPMASK = 2048
SDLK_WORLD_73 = 233
SDLK_F13 = 294
SDL_GL_BLUE_SIZE = 2
_ISgraph = 32768
__codecvt_ok = 0
SDLK_5 = 53
CD_ERROR = -1
__codecvt_error = 2
SDLK_WORLD_49 = 209
SDLK_WORLD_35 = 195
SDLK_WORLD_87 = 247
SDLK_DOWN = 274
SDLK_WORLD_4 = 164
SDLK_F11 = 292
SDLK_PLUS = 43
SDL_KEYUP = 3
SDLK_1 = 49
SDLK_BACKSLASH = 92
SDLK_KP2 = 258
SDLK_WORLD_63 = 223
SDLK_LEFTPAREN = 40
SDLK_c = 99
SDLK_WORLD_22 = 182
_ISalnum = 8
SDLK_WORLD_39 = 199
SDLK_3 = 51
SDLK_WORLD_25 = 185
_ISalpha = 1024
SDLK_MODE = 313
__GCONV_OK = 0
SDLK_AMPERSAND = 38
_IScntrl = 2
SDLK_WORLD_1 = 161
SDLK_WORLD_85 = 245
_ISblank = 1
SDLK_WORLD_52 = 212
SDLK_RIGHT = 275
SDLK_SPACE = 32
SDL_JOYBALLMOTIONMASK = 256
SDLK_DELETE = 127
SDLK_k = 107
SDL_EVENT_RESERVED3 = 19
SDL_JOYBUTTONDOWN = 10
SDLK_F15 = 296
SDL_MOUSEBUTTONDOWN = 5
SDLK_d = 100
SDLK_WORLD_70 = 230
SDLK_z = 122
SDLK_WORLD_46 = 206
SDLK_PRINT = 316
SDLK_b = 98
SDL_GL_ACCELERATED_VISUAL = 15
SDLK_KP_MULTIPLY = 268
SDLK_KP9 = 265
SDLK_WORLD_47 = 207
_ISlower = 512
_ISxdigit = 4096
SDLK_KP4 = 260
SDLK_LAST = 323
_ISspace = 8192
SDLK_g = 103
SDLK_LESS = 60
SDLK_9 = 57
KMOD_LMETA = 1024
SDLK_NUMLOCK = 300
SDLK_CARET = 94
SDLK_WORLD_77 = 237
SDLK_h = 104
SDLK_INSERT = 277
SDLK_WORLD_79 = 239
SDLK_WORLD_53 = 213
KMOD_LCTRL = 64
SDLK_m = 109
SDL_GL_ACCUM_GREEN_SIZE = 9
KMOD_NONE = 0
SDL_GL_DEPTH_SIZE = 6
SDLK_WORLD_3 = 163
SDLK_WORLD_11 = 171
SDL_GL_ACCUM_RED_SIZE = 8
SDLK_EQUALS = 61
SDLK_BACKSPACE = 8
SDLK_4 = 52
SDLK_F9 = 290
SDLK_WORLD_65 = 225
SDL_JOYHATMOTION = 9
SDLK_WORLD_67 = 227
SDLK_WORLD_12 = 172
SDLK_v = 118
SDL_QUIT = 12
SDLK_WORLD_43 = 203
SDLK_BACKQUOTE = 96
SDLK_u = 117
SDLK_WORLD_81 = 241
SDLK_CAPSLOCK = 301
SDL_ADDEVENT = 0
SDLK_HOME = 278
SDLK_RSHIFT = 303
SDLK_q = 113
SDL_EFWRITE = 2
SDLK_QUESTION = 63
KMOD_LALT = 256
SDLK_y = 121
SDLK_MINUS = 45
KMOD_LSHIFT = 1
SDLK_KP_ENTER = 271
SDLK_PERIOD = 46
SDLK_WORLD_57 = 217
SDL_GRAB_ON = 1
SDL_KEYEVENTMASK = 12
SDLK_WORLD_5 = 165
SDL_TRUE = 1
SDLK_r = 114
SDLK_WORLD_13 = 173
SDLK_ASTERISK = 42
SDL_VIDEOEXPOSE = 17
SDLK_RCTRL = 305
SDLK_WORLD_41 = 201
SDLK_f = 102
SDLK_SCROLLOCK = 302
SDLK_7 = 55
SDLK_WORLD_74 = 234
SDLK_END = 279
SDLK_WORLD_50 = 210
KMOD_RALT = 512
KMOD_RCTRL = 128
__codecvt_noconv = 3
SDLK_i = 105
__GCONV_IS_LAST = 1
SDLK_a = 97
SDL_EVENT_RESERVED7 = 23
SDLK_UNKNOWN = 0
KMOD_RMETA = 2048
SDLK_WORLD_7 = 167
SDLK_KP7 = 263
__GCONV_NOCONV = 1
SDLK_PAUSE = 19
SDLK_WORLD_29 = 189
SDLK_WORLD_15 = 175
SDL_VIDEORESIZE = 16
SDLK_n = 110
SDLK_e = 101
SDLK_WORLD_40 = 200
SDLK_WORLD_26 = 186
SDL_GETEVENT = 2
SDL_USEREVENT = 24
SDLK_WORLD_78 = 238
SDLK_ESCAPE = 27
SDL_ENOMEM = 0
__codecvt_partial = 1
SDLK_F14 = 295
KMOD_NUM = 4096
SDLK_s = 115
SDL_EVENT_RESERVED6 = 22
SDL_MOUSEMOTIONMASK = 16
SDLK_WORLD_9 = 169
KMOD_MODE = 16384
SDL_EVENT_RESERVEDB = 15
SDLK_WORLD_71 = 231
SDL_NOEVENT = 0
SDLK_WORLD_33 = 193
size_t = c_uint
uint8_t = c_ubyte
uint16_t = c_ushort
uint32_t = c_uint
uint64_t = c_ulonglong
int_least8_t = c_byte
int_least16_t = c_short
int_least32_t = c_int
int_least64_t = c_longlong
uint_least8_t = c_ubyte
uint_least16_t = c_ushort
uint_least32_t = c_uint
uint_least64_t = c_ulonglong
int_fast8_t = c_byte
int_fast16_t = c_int
int_fast32_t = c_int
int_fast64_t = c_longlong
uint_fast8_t = c_ubyte
uint_fast16_t = c_uint
uint_fast32_t = c_uint
uint_fast64_t = c_ulonglong
intptr_t = c_int
uintptr_t = c_uint
int32_t = c_int
ulong = c_ulong
ushort = c_ushort
uint = c_uint
int8_t = c_byte
int16_t = c_short
int64_t = c_longlong
u_int8_t = c_ubyte
u_int16_t = c_ushort
u_int32_t = c_uint
u_int64_t = c_ulonglong
Uint32 = uint32_t
SDL_Init = libSDL.SDL_Init
SDL_Init.restype = c_int
SDL_Init.argtypes = [Uint32]
SDL_InitSubSystem = libSDL.SDL_InitSubSystem
SDL_InitSubSystem.restype = c_int
SDL_InitSubSystem.argtypes = [Uint32]
SDL_QuitSubSystem = libSDL.SDL_QuitSubSystem
SDL_QuitSubSystem.restype = None
SDL_QuitSubSystem.argtypes = [Uint32]
SDL_WasInit = libSDL.SDL_WasInit
SDL_WasInit.restype = Uint32
SDL_WasInit.argtypes = [Uint32]
SDL_Quit = libSDL.SDL_Quit
SDL_Quit.restype = None
SDL_Quit.argtypes = []
Uint8 = uint8_t
SDL_GetAppState = libSDL.SDL_GetAppState
SDL_GetAppState.restype = Uint8
SDL_GetAppState.argtypes = []
class SDL_AudioSpec(Structure):
    pass
SDL_AudioSpec._external_ = True
Uint16 = uint16_t
SDL_AudioSpec._fields_ = [
    ('freq', c_int),
    ('format', Uint16),
    ('channels', Uint8),
    ('silence', Uint8),
    ('samples', Uint16),
    ('padding', Uint16),
    ('size', Uint32),
    ('callback', CFUNCTYPE(None, c_void_p, POINTER(Uint8), c_int)),
    ('userdata', c_void_p),
]
class SDL_AudioCVT(Structure):
    pass
SDL_AudioCVT._external_ = True
SDL_AudioCVT._pack_ = 4
SDL_AudioCVT._fields_ = [
    ('needed', c_int),
    ('src_format', Uint16),
    ('dst_format', Uint16),
    ('rate_incr', c_double),
    ('buf', POINTER(Uint8)),
    ('len', c_int),
    ('len_cvt', c_int),
    ('len_mult', c_int),
    ('len_ratio', c_double),
    ('filters', CFUNCTYPE(None, POINTER(SDL_AudioCVT), c_ushort) * 10),
    ('filter_index', c_int),
]
SDL_AudioInit = libSDL.SDL_AudioInit
SDL_AudioInit.restype = c_int
SDL_AudioInit.argtypes = [STRING]
SDL_AudioQuit = libSDL.SDL_AudioQuit
SDL_AudioQuit.restype = None
SDL_AudioQuit.argtypes = []
SDL_AudioDriverName = libSDL.SDL_AudioDriverName
SDL_AudioDriverName.restype = STRING
SDL_AudioDriverName.argtypes = [STRING, c_int]
SDL_OpenAudio = libSDL.SDL_OpenAudio
SDL_OpenAudio.restype = c_int
SDL_OpenAudio.argtypes = [POINTER(SDL_AudioSpec), POINTER(SDL_AudioSpec)]

# values for enumeration 'SDL_audiostatus'
SDL_audiostatus = c_int # enum
SDL_GetAudioStatus = libSDL.SDL_GetAudioStatus
SDL_GetAudioStatus.restype = SDL_audiostatus
SDL_GetAudioStatus.argtypes = []
SDL_PauseAudio = libSDL.SDL_PauseAudio
SDL_PauseAudio.restype = None
SDL_PauseAudio.argtypes = [c_int]
class SDL_RWops(Structure):
    pass
SDL_RWops._external_ = True
SDL_LoadWAV_RW = libSDL.SDL_LoadWAV_RW
SDL_LoadWAV_RW.restype = POINTER(SDL_AudioSpec)
SDL_LoadWAV_RW.argtypes = [POINTER(SDL_RWops), c_int, POINTER(SDL_AudioSpec), POINTER(POINTER(Uint8)), POINTER(Uint32)]
SDL_FreeWAV = libSDL.SDL_FreeWAV
SDL_FreeWAV.restype = None
SDL_FreeWAV.argtypes = [POINTER(Uint8)]
SDL_BuildAudioCVT = libSDL.SDL_BuildAudioCVT
SDL_BuildAudioCVT.restype = c_int
SDL_BuildAudioCVT.argtypes = [POINTER(SDL_AudioCVT), Uint16, Uint8, c_int, Uint16, Uint8, c_int]
SDL_ConvertAudio = libSDL.SDL_ConvertAudio
SDL_ConvertAudio.restype = c_int
SDL_ConvertAudio.argtypes = [POINTER(SDL_AudioCVT)]
SDL_MixAudio = libSDL.SDL_MixAudio
SDL_MixAudio.restype = None
SDL_MixAudio.argtypes = [POINTER(Uint8), POINTER(Uint8), Uint32, c_int]
SDL_LockAudio = libSDL.SDL_LockAudio
SDL_LockAudio.restype = None
SDL_LockAudio.argtypes = []
SDL_UnlockAudio = libSDL.SDL_UnlockAudio
SDL_UnlockAudio.restype = None
SDL_UnlockAudio.argtypes = []
SDL_CloseAudio = libSDL.SDL_CloseAudio
SDL_CloseAudio.restype = None
SDL_CloseAudio.argtypes = []

# values for enumeration 'CDstatus'
CDstatus = c_int # enum
class SDL_CDtrack(Structure):
    pass
SDL_CDtrack._external_ = True
SDL_CDtrack._fields_ = [
    ('id', Uint8),
    ('type', Uint8),
    ('unused', Uint16),
    ('length', Uint32),
    ('offset', Uint32),
]
class SDL_CD(Structure):
    pass
SDL_CD._external_ = True
SDL_CD._fields_ = [
    ('id', c_int),
    ('status', CDstatus),
    ('numtracks', c_int),
    ('cur_track', c_int),
    ('cur_frame', c_int),
    ('track', SDL_CDtrack * 100),
]
SDL_CDNumDrives = libSDL.SDL_CDNumDrives
SDL_CDNumDrives.restype = c_int
SDL_CDNumDrives.argtypes = []
SDL_CDName = libSDL.SDL_CDName
SDL_CDName.restype = STRING
SDL_CDName.argtypes = [c_int]
SDL_CDOpen = libSDL.SDL_CDOpen
SDL_CDOpen.restype = POINTER(SDL_CD)
SDL_CDOpen.argtypes = [c_int]
SDL_CDStatus = libSDL.SDL_CDStatus
SDL_CDStatus.restype = CDstatus
SDL_CDStatus.argtypes = [POINTER(SDL_CD)]
SDL_CDPlayTracks = libSDL.SDL_CDPlayTracks
SDL_CDPlayTracks.restype = c_int
SDL_CDPlayTracks.argtypes = [POINTER(SDL_CD), c_int, c_int, c_int, c_int]
SDL_CDPlay = libSDL.SDL_CDPlay
SDL_CDPlay.restype = c_int
SDL_CDPlay.argtypes = [POINTER(SDL_CD), c_int, c_int]
SDL_CDPause = libSDL.SDL_CDPause
SDL_CDPause.restype = c_int
SDL_CDPause.argtypes = [POINTER(SDL_CD)]
SDL_CDResume = libSDL.SDL_CDResume
SDL_CDResume.restype = c_int
SDL_CDResume.argtypes = [POINTER(SDL_CD)]
SDL_CDStop = libSDL.SDL_CDStop
SDL_CDStop.restype = c_int
SDL_CDStop.argtypes = [POINTER(SDL_CD)]
SDL_CDEject = libSDL.SDL_CDEject
SDL_CDEject.restype = c_int
SDL_CDEject.argtypes = [POINTER(SDL_CD)]
SDL_CDClose = libSDL.SDL_CDClose
SDL_CDClose.restype = None
SDL_CDClose.argtypes = [POINTER(SDL_CD)]

# values for enumeration 'SDL_bool'
SDL_bool = c_int # enum
SDL_HasRDTSC = libSDL.SDL_HasRDTSC
SDL_HasRDTSC.restype = SDL_bool
SDL_HasRDTSC.argtypes = []
SDL_HasMMX = libSDL.SDL_HasMMX
SDL_HasMMX.restype = SDL_bool
SDL_HasMMX.argtypes = []
SDL_HasMMXExt = libSDL.SDL_HasMMXExt
SDL_HasMMXExt.restype = SDL_bool
SDL_HasMMXExt.argtypes = []
SDL_Has3DNow = libSDL.SDL_Has3DNow
SDL_Has3DNow.restype = SDL_bool
SDL_Has3DNow.argtypes = []
SDL_Has3DNowExt = libSDL.SDL_Has3DNowExt
SDL_Has3DNowExt.restype = SDL_bool
SDL_Has3DNowExt.argtypes = []
SDL_HasSSE = libSDL.SDL_HasSSE
SDL_HasSSE.restype = SDL_bool
SDL_HasSSE.argtypes = []
SDL_HasSSE2 = libSDL.SDL_HasSSE2
SDL_HasSSE2.restype = SDL_bool
SDL_HasSSE2.argtypes = []
SDL_HasAltiVec = libSDL.SDL_HasAltiVec
SDL_HasAltiVec.restype = SDL_bool
SDL_HasAltiVec.argtypes = []
SDL_SetError = libSDL.SDL_SetError
SDL_SetError.restype = None
SDL_SetError.argtypes = [STRING]
SDL_GetError = libSDL.SDL_GetError
SDL_GetError.restype = STRING
SDL_GetError.argtypes = []
SDL_ClearError = libSDL.SDL_ClearError
SDL_ClearError.restype = None
SDL_ClearError.argtypes = []

# values for enumeration 'SDL_errorcode'
SDL_errorcode = c_int # enum
SDL_Error = libSDL.SDL_Error
SDL_Error.restype = None
SDL_Error.argtypes = [SDL_errorcode]

# values for enumeration 'SDL_EventType'
SDL_EventType = c_int # enum

# values for enumeration 'SDL_EventMask'
SDL_EventMask = c_int # enum
class SDL_ActiveEvent(Structure):
    pass
SDL_ActiveEvent._external_ = True
SDL_ActiveEvent._fields_ = [
    ('type', Uint8),
    ('gain', Uint8),
    ('state', Uint8),
]
class SDL_KeyboardEvent(Structure):
    pass
SDL_KeyboardEvent._external_ = True
class SDL_keysym(Structure):
    pass
SDL_keysym._external_ = True

# values for enumeration 'SDLKey'
SDLKey = c_int # enum

# values for enumeration 'SDLMod'
SDLMod = c_int # enum
SDL_keysym._fields_ = [
    ('scancode', Uint8),
    ('sym', SDLKey),
    ('mod', SDLMod),
    ('unicode', Uint16),
]
SDL_KeyboardEvent._fields_ = [
    ('type', Uint8),
    ('which', Uint8),
    ('state', Uint8),
    ('keysym', SDL_keysym),
]
class SDL_MouseMotionEvent(Structure):
    pass
SDL_MouseMotionEvent._external_ = True
Sint16 = int16_t
SDL_MouseMotionEvent._fields_ = [
    ('type', Uint8),
    ('which', Uint8),
    ('state', Uint8),
    ('x', Uint16),
    ('y', Uint16),
    ('xrel', Sint16),
    ('yrel', Sint16),
]
class SDL_MouseButtonEvent(Structure):
    pass
SDL_MouseButtonEvent._external_ = True
SDL_MouseButtonEvent._fields_ = [
    ('type', Uint8),
    ('which', Uint8),
    ('button', Uint8),
    ('state', Uint8),
    ('x', Uint16),
    ('y', Uint16),
]
class SDL_JoyAxisEvent(Structure):
    pass
SDL_JoyAxisEvent._external_ = True
SDL_JoyAxisEvent._fields_ = [
    ('type', Uint8),
    ('which', Uint8),
    ('axis', Uint8),
    ('value', Sint16),
]
class SDL_JoyBallEvent(Structure):
    pass
SDL_JoyBallEvent._external_ = True
SDL_JoyBallEvent._fields_ = [
    ('type', Uint8),
    ('which', Uint8),
    ('ball', Uint8),
    ('xrel', Sint16),
    ('yrel', Sint16),
]
class SDL_JoyHatEvent(Structure):
    pass
SDL_JoyHatEvent._external_ = True
SDL_JoyHatEvent._fields_ = [
    ('type', Uint8),
    ('which', Uint8),
    ('hat', Uint8),
    ('value', Uint8),
]
class SDL_JoyButtonEvent(Structure):
    pass
SDL_JoyButtonEvent._external_ = True
SDL_JoyButtonEvent._fields_ = [
    ('type', Uint8),
    ('which', Uint8),
    ('button', Uint8),
    ('state', Uint8),
]
class SDL_ResizeEvent(Structure):
    pass
SDL_ResizeEvent._external_ = True
SDL_ResizeEvent._fields_ = [
    ('type', Uint8),
    ('w', c_int),
    ('h', c_int),
]
class SDL_ExposeEvent(Structure):
    pass
SDL_ExposeEvent._external_ = True
SDL_ExposeEvent._fields_ = [
    ('type', Uint8),
]
class SDL_QuitEvent(Structure):
    pass
SDL_QuitEvent._external_ = True
SDL_QuitEvent._fields_ = [
    ('type', Uint8),
]
class SDL_UserEvent(Structure):
    pass
SDL_UserEvent._external_ = True
SDL_UserEvent._fields_ = [
    ('type', Uint8),
    ('code', c_int),
    ('data1', c_void_p),
    ('data2', c_void_p),
]
#class SDL_SysWMmsg(Structure):
#    pass
#SDL_SysWMmsg._external_ = True
#SDL_SysWMmsg._fields_ = [
#]
#class SDL_SysWMEvent(Structure):
#    pass
#SDL_SysWMEvent._external_ = True
#SDL_SysWMEvent._fields_ = [
#    ('type', Uint8),
#    ('msg', POINTER(SDL_SysWMmsg)),
#]
class SDL_Event(Union):
    pass
SDL_Event._external_ = True
SDL_Event._fields_ = [
    ('type', Uint8),
    ('active', SDL_ActiveEvent),
    ('key', SDL_KeyboardEvent),
    ('motion', SDL_MouseMotionEvent),
    ('button', SDL_MouseButtonEvent),
    ('jaxis', SDL_JoyAxisEvent),
    ('jball', SDL_JoyBallEvent),
    ('jhat', SDL_JoyHatEvent),
    ('jbutton', SDL_JoyButtonEvent),
    ('resize', SDL_ResizeEvent),
    ('expose', SDL_ExposeEvent),
    ('quit', SDL_QuitEvent),
    ('user', SDL_UserEvent),
#    ('syswm', SDL_SysWMEvent),
]
SDL_PumpEvents = libSDL.SDL_PumpEvents
SDL_PumpEvents.restype = None
SDL_PumpEvents.argtypes = []

# values for enumeration 'SDL_eventaction'
SDL_eventaction = c_int # enum
SDL_PeepEvents = libSDL.SDL_PeepEvents
SDL_PeepEvents.restype = c_int
SDL_PeepEvents.argtypes = [POINTER(SDL_Event), c_int, SDL_eventaction, Uint32]
SDL_PollEvent = libSDL.SDL_PollEvent
SDL_PollEvent.restype = c_int
SDL_PollEvent.argtypes = [POINTER(SDL_Event)]
SDL_WaitEvent = libSDL.SDL_WaitEvent
SDL_WaitEvent.restype = c_int
SDL_WaitEvent.argtypes = [POINTER(SDL_Event)]
SDL_PushEvent = libSDL.SDL_PushEvent
SDL_PushEvent.restype = c_int
SDL_PushEvent.argtypes = [POINTER(SDL_Event)]
SDL_EventFilter = CFUNCTYPE(c_int, POINTER(SDL_Event))
SDL_SetEventFilter = libSDL.SDL_SetEventFilter
SDL_SetEventFilter.restype = None
SDL_SetEventFilter.argtypes = [SDL_EventFilter]
SDL_GetEventFilter = libSDL.SDL_GetEventFilter
SDL_GetEventFilter.restype = SDL_EventFilter
SDL_GetEventFilter.argtypes = []
SDL_EventState = libSDL.SDL_EventState
SDL_EventState.restype = Uint8
SDL_EventState.argtypes = [Uint8, c_int]
class _SDL_Joystick(Structure):
    pass
_SDL_Joystick._external_ = True
_SDL_Joystick._fields_ = [
]
SDL_Joystick = _SDL_Joystick
SDL_NumJoysticks = libSDL.SDL_NumJoysticks
SDL_NumJoysticks.restype = c_int
SDL_NumJoysticks.argtypes = []
SDL_JoystickName = libSDL.SDL_JoystickName
SDL_JoystickName.restype = STRING
SDL_JoystickName.argtypes = [c_int]
SDL_JoystickOpen = libSDL.SDL_JoystickOpen
SDL_JoystickOpen.restype = POINTER(SDL_Joystick)
SDL_JoystickOpen.argtypes = [c_int]
SDL_JoystickOpened = libSDL.SDL_JoystickOpened
SDL_JoystickOpened.restype = c_int
SDL_JoystickOpened.argtypes = [c_int]
SDL_JoystickIndex = libSDL.SDL_JoystickIndex
SDL_JoystickIndex.restype = c_int
SDL_JoystickIndex.argtypes = [POINTER(SDL_Joystick)]
SDL_JoystickNumAxes = libSDL.SDL_JoystickNumAxes
SDL_JoystickNumAxes.restype = c_int
SDL_JoystickNumAxes.argtypes = [POINTER(SDL_Joystick)]
SDL_JoystickNumBalls = libSDL.SDL_JoystickNumBalls
SDL_JoystickNumBalls.restype = c_int
SDL_JoystickNumBalls.argtypes = [POINTER(SDL_Joystick)]
SDL_JoystickNumHats = libSDL.SDL_JoystickNumHats
SDL_JoystickNumHats.restype = c_int
SDL_JoystickNumHats.argtypes = [POINTER(SDL_Joystick)]
SDL_JoystickNumButtons = libSDL.SDL_JoystickNumButtons
SDL_JoystickNumButtons.restype = c_int
SDL_JoystickNumButtons.argtypes = [POINTER(SDL_Joystick)]
SDL_JoystickUpdate = libSDL.SDL_JoystickUpdate
SDL_JoystickUpdate.restype = None
SDL_JoystickUpdate.argtypes = []
SDL_JoystickEventState = libSDL.SDL_JoystickEventState
SDL_JoystickEventState.restype = c_int
SDL_JoystickEventState.argtypes = [c_int]
SDL_JoystickGetAxis = libSDL.SDL_JoystickGetAxis
SDL_JoystickGetAxis.restype = Sint16
SDL_JoystickGetAxis.argtypes = [POINTER(SDL_Joystick), c_int]
SDL_JoystickGetHat = libSDL.SDL_JoystickGetHat
SDL_JoystickGetHat.restype = Uint8
SDL_JoystickGetHat.argtypes = [POINTER(SDL_Joystick), c_int]
SDL_JoystickGetBall = libSDL.SDL_JoystickGetBall
SDL_JoystickGetBall.restype = c_int
SDL_JoystickGetBall.argtypes = [POINTER(SDL_Joystick), c_int, POINTER(c_int), POINTER(c_int)]
SDL_JoystickGetButton = libSDL.SDL_JoystickGetButton
SDL_JoystickGetButton.restype = Uint8
SDL_JoystickGetButton.argtypes = [POINTER(SDL_Joystick), c_int]
SDL_JoystickClose = libSDL.SDL_JoystickClose
SDL_JoystickClose.restype = None
SDL_JoystickClose.argtypes = [POINTER(SDL_Joystick)]
SDL_EnableUNICODE = libSDL.SDL_EnableUNICODE
SDL_EnableUNICODE.restype = c_int
SDL_EnableUNICODE.argtypes = [c_int]
SDL_EnableKeyRepeat = libSDL.SDL_EnableKeyRepeat
SDL_EnableKeyRepeat.restype = c_int
SDL_EnableKeyRepeat.argtypes = [c_int, c_int]
#SDL_GetKeyRepeat = libSDL.SDL_GetKeyRepeat
#SDL_GetKeyRepeat.restype = None
#SDL_GetKeyRepeat.argtypes = [POINTER(c_int), POINTER(c_int)]
SDL_GetKeyState = libSDL.SDL_GetKeyState
SDL_GetKeyState.restype = POINTER(Uint8)
SDL_GetKeyState.argtypes = [POINTER(c_int)]
SDL_GetModState = libSDL.SDL_GetModState
SDL_GetModState.restype = SDLMod
SDL_GetModState.argtypes = []
SDL_SetModState = libSDL.SDL_SetModState
SDL_SetModState.restype = None
SDL_SetModState.argtypes = [SDLMod]
SDL_GetKeyName = libSDL.SDL_GetKeyName
SDL_GetKeyName.restype = STRING
SDL_GetKeyName.argtypes = [SDLKey]
SDL_LoadObject = libSDL.SDL_LoadObject
SDL_LoadObject.restype = c_void_p
SDL_LoadObject.argtypes = [STRING]
SDL_LoadFunction = libSDL.SDL_LoadFunction
SDL_LoadFunction.restype = c_void_p
SDL_LoadFunction.argtypes = [c_void_p, STRING]
SDL_UnloadObject = libSDL.SDL_UnloadObject
SDL_UnloadObject.restype = None
SDL_UnloadObject.argtypes = [c_void_p]
class WMcursor(Structure):
    pass
WMcursor._external_ = True
WMcursor._fields_ = [
]
class SDL_Cursor(Structure):
    pass
SDL_Cursor._external_ = True
class SDL_Rect(Structure):
    pass
SDL_Rect._external_ = True
SDL_Rect._fields_ = [
    ('x', Sint16),
    ('y', Sint16),
    ('w', Uint16),
    ('h', Uint16),
]
SDL_Cursor._fields_ = [
    ('area', SDL_Rect),
    ('hot_x', Sint16),
    ('hot_y', Sint16),
    ('data', POINTER(Uint8)),
    ('mask', POINTER(Uint8)),
    ('save', POINTER(Uint8) * 2),
    ('wm_cursor', POINTER(WMcursor)),
]
SDL_GetMouseState = libSDL.SDL_GetMouseState
SDL_GetMouseState.restype = Uint8
SDL_GetMouseState.argtypes = [POINTER(c_int), POINTER(c_int)]
SDL_GetRelativeMouseState = libSDL.SDL_GetRelativeMouseState
SDL_GetRelativeMouseState.restype = Uint8
SDL_GetRelativeMouseState.argtypes = [POINTER(c_int), POINTER(c_int)]
SDL_WarpMouse = libSDL.SDL_WarpMouse
SDL_WarpMouse.restype = None
SDL_WarpMouse.argtypes = [Uint16, Uint16]
SDL_CreateCursor = libSDL.SDL_CreateCursor
SDL_CreateCursor.restype = POINTER(SDL_Cursor)
SDL_CreateCursor.argtypes = [POINTER(Uint8), POINTER(Uint8), c_int, c_int, c_int, c_int]
SDL_SetCursor = libSDL.SDL_SetCursor
SDL_SetCursor.restype = None
SDL_SetCursor.argtypes = [POINTER(SDL_Cursor)]
SDL_GetCursor = libSDL.SDL_GetCursor
SDL_GetCursor.restype = POINTER(SDL_Cursor)
SDL_GetCursor.argtypes = []
SDL_FreeCursor = libSDL.SDL_FreeCursor
SDL_FreeCursor.restype = None
SDL_FreeCursor.argtypes = [POINTER(SDL_Cursor)]
SDL_ShowCursor = libSDL.SDL_ShowCursor
SDL_ShowCursor.restype = c_int
SDL_ShowCursor.argtypes = [c_int]
class SDL_mutex(Structure):
    pass
SDL_mutex._external_ = True
SDL_mutex._fields_ = [
]
SDL_CreateMutex = libSDL.SDL_CreateMutex
SDL_CreateMutex.restype = POINTER(SDL_mutex)
SDL_CreateMutex.argtypes = []
SDL_mutexP = libSDL.SDL_mutexP
SDL_mutexP.restype = c_int
SDL_mutexP.argtypes = [POINTER(SDL_mutex)]
SDL_mutexV = libSDL.SDL_mutexV
SDL_mutexV.restype = c_int
SDL_mutexV.argtypes = [POINTER(SDL_mutex)]
SDL_DestroyMutex = libSDL.SDL_DestroyMutex
SDL_DestroyMutex.restype = None
SDL_DestroyMutex.argtypes = [POINTER(SDL_mutex)]
class SDL_semaphore(Structure):
    pass
SDL_semaphore._external_ = True
SDL_semaphore._fields_ = [
]
SDL_sem = SDL_semaphore
SDL_CreateSemaphore = libSDL.SDL_CreateSemaphore
SDL_CreateSemaphore.restype = POINTER(SDL_sem)
SDL_CreateSemaphore.argtypes = [Uint32]
SDL_DestroySemaphore = libSDL.SDL_DestroySemaphore
SDL_DestroySemaphore.restype = None
SDL_DestroySemaphore.argtypes = [POINTER(SDL_sem)]
SDL_SemWait = libSDL.SDL_SemWait
SDL_SemWait.restype = c_int
SDL_SemWait.argtypes = [POINTER(SDL_sem)]
SDL_SemTryWait = libSDL.SDL_SemTryWait
SDL_SemTryWait.restype = c_int
SDL_SemTryWait.argtypes = [POINTER(SDL_sem)]
SDL_SemWaitTimeout = libSDL.SDL_SemWaitTimeout
SDL_SemWaitTimeout.restype = c_int
SDL_SemWaitTimeout.argtypes = [POINTER(SDL_sem), Uint32]
SDL_SemPost = libSDL.SDL_SemPost
SDL_SemPost.restype = c_int
SDL_SemPost.argtypes = [POINTER(SDL_sem)]
SDL_SemValue = libSDL.SDL_SemValue
SDL_SemValue.restype = Uint32
SDL_SemValue.argtypes = [POINTER(SDL_sem)]
class SDL_cond(Structure):
    pass
SDL_cond._external_ = True
SDL_cond._fields_ = [
]
SDL_CreateCond = libSDL.SDL_CreateCond
SDL_CreateCond.restype = POINTER(SDL_cond)
SDL_CreateCond.argtypes = []
SDL_DestroyCond = libSDL.SDL_DestroyCond
SDL_DestroyCond.restype = None
SDL_DestroyCond.argtypes = [POINTER(SDL_cond)]
SDL_CondSignal = libSDL.SDL_CondSignal
SDL_CondSignal.restype = c_int
SDL_CondSignal.argtypes = [POINTER(SDL_cond)]
SDL_CondBroadcast = libSDL.SDL_CondBroadcast
SDL_CondBroadcast.restype = c_int
SDL_CondBroadcast.argtypes = [POINTER(SDL_cond)]
SDL_CondWait = libSDL.SDL_CondWait
SDL_CondWait.restype = c_int
SDL_CondWait.argtypes = [POINTER(SDL_cond), POINTER(SDL_mutex)]
SDL_CondWaitTimeout = libSDL.SDL_CondWaitTimeout
SDL_CondWaitTimeout.restype = c_int
SDL_CondWaitTimeout.argtypes = [POINTER(SDL_cond), POINTER(SDL_mutex), Uint32]
#class N9SDL_RWops4DOT_30E(Union):
#    pass
#class N9SDL_RWops4DOT_304DOT_31E(Structure):
#    pass
#N9SDL_RWops4DOT_304DOT_31E._fields_ = [
#    ('autoclose', c_int),
#    ('fp', POINTER(FILE)),
#]
#class N9SDL_RWops4DOT_304DOT_32E(Structure):
#    pass
#N9SDL_RWops4DOT_304DOT_32E._fields_ = [
#    ('base', POINTER(Uint8)),
#    ('here', POINTER(Uint8)),
#    ('stop', POINTER(Uint8)),
#]
#class N9SDL_RWops4DOT_304DOT_33E(Structure):
#    pass
#N9SDL_RWops4DOT_304DOT_33E._fields_ = [
#    ('data1', c_void_p),
#]
#N9SDL_RWops4DOT_30E._fields_ = [
#    ('stdio', N9SDL_RWops4DOT_304DOT_31E),
#    ('mem', N9SDL_RWops4DOT_304DOT_32E),
#    ('unknown', N9SDL_RWops4DOT_304DOT_33E),
#]
#SDL_RWops._fields_ = [
#    ('seek', CFUNCTYPE(c_int, POINTER(SDL_RWops), c_int, c_int)),
#    ('read', CFUNCTYPE(c_int, POINTER(SDL_RWops), c_void_p, c_int, c_int)),
#    ('write', CFUNCTYPE(c_int, POINTER(SDL_RWops), c_void_p, c_int, c_int)),
#    ('close', CFUNCTYPE(c_int, POINTER(SDL_RWops))),
#    ('type', Uint32),
#    ('hidden', N9SDL_RWops4DOT_30E),
#]
#SDL_RWFromFile = libSDL.SDL_RWFromFile
#SDL_RWFromFile.restype = POINTER(SDL_RWops)
#SDL_RWFromFile.argtypes = [STRING, STRING]
#SDL_RWFromFP = libSDL.SDL_RWFromFP
#SDL_RWFromFP.restype = POINTER(SDL_RWops)
#SDL_RWFromFP.argtypes = [POINTER(FILE), c_int]
#SDL_RWFromMem = libSDL.SDL_RWFromMem
#SDL_RWFromMem.restype = POINTER(SDL_RWops)
#SDL_RWFromMem.argtypes = [c_void_p, c_int]
#SDL_RWFromConstMem = libSDL.SDL_RWFromConstMem
#SDL_RWFromConstMem.restype = POINTER(SDL_RWops)
#SDL_RWFromConstMem.argtypes = [c_void_p, c_int]
#SDL_AllocRW = libSDL.SDL_AllocRW
#SDL_AllocRW.restype = POINTER(SDL_RWops)
#SDL_AllocRW.argtypes = []
#SDL_FreeRW = libSDL.SDL_FreeRW
#SDL_FreeRW.restype = None
#SDL_FreeRW.argtypes = [POINTER(SDL_RWops)]
#SDL_ReadLE16 = libSDL.SDL_ReadLE16
#SDL_ReadLE16.restype = Uint16
#SDL_ReadLE16.argtypes = [POINTER(SDL_RWops)]
#SDL_ReadBE16 = libSDL.SDL_ReadBE16
#SDL_ReadBE16.restype = Uint16
#SDL_ReadBE16.argtypes = [POINTER(SDL_RWops)]
#SDL_ReadLE32 = libSDL.SDL_ReadLE32
#SDL_ReadLE32.restype = Uint32
#SDL_ReadLE32.argtypes = [POINTER(SDL_RWops)]
#SDL_ReadBE32 = libSDL.SDL_ReadBE32
#SDL_ReadBE32.restype = Uint32
#SDL_ReadBE32.argtypes = [POINTER(SDL_RWops)]
Uint64 = uint64_t
#SDL_ReadLE64 = libSDL.SDL_ReadLE64
#SDL_ReadLE64.restype = Uint64
#SDL_ReadLE64.argtypes = [POINTER(SDL_RWops)]
#SDL_ReadBE64 = libSDL.SDL_ReadBE64
#SDL_ReadBE64.restype = Uint64
#SDL_ReadBE64.argtypes = [POINTER(SDL_RWops)]
#SDL_WriteLE16 = libSDL.SDL_WriteLE16
#SDL_WriteLE16.restype = c_int
#SDL_WriteLE16.argtypes = [POINTER(SDL_RWops), Uint16]
#SDL_WriteBE16 = libSDL.SDL_WriteBE16
#SDL_WriteBE16.restype = c_int
#SDL_WriteBE16.argtypes = [POINTER(SDL_RWops), Uint16]
#SDL_WriteLE32 = libSDL.SDL_WriteLE32
#SDL_WriteLE32.restype = c_int
#SDL_WriteLE32.argtypes = [POINTER(SDL_RWops), Uint32]
#SDL_WriteBE32 = libSDL.SDL_WriteBE32
#SDL_WriteBE32.restype = c_int
#SDL_WriteBE32.argtypes = [POINTER(SDL_RWops), Uint32]
#SDL_WriteLE64 = libSDL.SDL_WriteLE64
#SDL_WriteLE64.restype = c_int
#SDL_WriteLE64.argtypes = [POINTER(SDL_RWops), Uint64]
#SDL_WriteBE64 = libSDL.SDL_WriteBE64
#SDL_WriteBE64.restype = c_int
#SDL_WriteBE64.argtypes = [POINTER(SDL_RWops), Uint64]
Sint8 = int8_t
Sint32 = int32_t
Sint64 = int64_t
SDL_dummy_uint8 = c_int * 1
SDL_dummy_sint8 = c_int * 1
SDL_dummy_uint16 = c_int * 1
SDL_dummy_sint16 = c_int * 1
SDL_dummy_uint32 = c_int * 1
SDL_dummy_sint32 = c_int * 1
SDL_dummy_uint64 = c_int * 1
SDL_dummy_sint64 = c_int * 1

# values for enumeration 'SDL_DUMMY_ENUM'
SDL_DUMMY_ENUM = c_int # enum
SDL_dummy_enum = c_int * 1
#SDL_strlcpy = libSDL.SDL_strlcpy
#SDL_strlcpy.restype = size_t
#SDL_strlcpy.argtypes = [STRING, STRING, size_t]
#SDL_strlcat = libSDL.SDL_strlcat
#SDL_strlcat.restype = size_t
#SDL_strlcat.argtypes = [STRING, STRING, size_t]
#SDL_strrev = libSDL.SDL_strrev
#SDL_strrev.restype = STRING
#SDL_strrev.argtypes = [STRING]
#SDL_strupr = libSDL.SDL_strupr
#SDL_strupr.restype = STRING
#SDL_strupr.argtypes = [STRING]
#SDL_strlwr = libSDL.SDL_strlwr
#SDL_strlwr.restype = STRING
#SDL_strlwr.argtypes = [STRING]
#SDL_ltoa = libSDL.SDL_ltoa
#SDL_ltoa.restype = STRING
#SDL_ltoa.argtypes = [c_long, STRING, c_int]
#SDL_ultoa = libSDL.SDL_ultoa
#SDL_ultoa.restype = STRING
#SDL_ultoa.argtypes = [c_ulong, STRING, c_int]
#SDL_lltoa = libSDL.SDL_lltoa
#SDL_lltoa.restype = STRING
#SDL_lltoa.argtypes = [Sint64, STRING, c_int]
#SDL_ulltoa = libSDL.SDL_ulltoa
#SDL_ulltoa.restype = STRING
#SDL_ulltoa.argtypes = [Uint64, STRING, c_int]
#SDL_iconv = libSDL.SDL_iconv
#SDL_iconv.restype = size_t
#SDL_iconv.argtypes = [iconv_t, POINTER(STRING), POINTER(size_t), POINTER(STRING), POINTER(size_t)]
#SDL_iconv_string = libSDL.SDL_iconv_string
#SDL_iconv_string.restype = STRING
#SDL_iconv_string.argtypes = [STRING, STRING, STRING, size_t]
class SDL_Thread(Structure):
    pass
SDL_Thread._external_ = True
SDL_Thread._fields_ = [
]
SDL_CreateThread = libSDL.SDL_CreateThread
SDL_CreateThread.restype = POINTER(SDL_Thread)
SDL_CreateThread.argtypes = [CFUNCTYPE(c_int, c_void_p), c_void_p]
SDL_ThreadID = libSDL.SDL_ThreadID
SDL_ThreadID.restype = Uint32
SDL_ThreadID.argtypes = []
SDL_GetThreadID = libSDL.SDL_GetThreadID
SDL_GetThreadID.restype = Uint32
SDL_GetThreadID.argtypes = [POINTER(SDL_Thread)]
SDL_WaitThread = libSDL.SDL_WaitThread
SDL_WaitThread.restype = None
SDL_WaitThread.argtypes = [POINTER(SDL_Thread), POINTER(c_int)]
SDL_KillThread = libSDL.SDL_KillThread
SDL_KillThread.restype = None
SDL_KillThread.argtypes = [POINTER(SDL_Thread)]
SDL_GetTicks = libSDL.SDL_GetTicks
SDL_GetTicks.restype = Uint32
SDL_GetTicks.argtypes = []
SDL_Delay = libSDL.SDL_Delay
SDL_Delay.restype = None
SDL_Delay.argtypes = [Uint32]
SDL_TimerCallback = CFUNCTYPE(Uint32, c_uint)
SDL_SetTimer = libSDL.SDL_SetTimer
SDL_SetTimer.restype = c_int
SDL_SetTimer.argtypes = [Uint32, SDL_TimerCallback]
SDL_NewTimerCallback = CFUNCTYPE(Uint32, c_uint, c_void_p)
class _SDL_TimerID(Structure):
    pass
_SDL_TimerID._external_ = True
SDL_TimerID = POINTER(_SDL_TimerID)
_SDL_TimerID._fields_ = [
]
SDL_AddTimer = libSDL.SDL_AddTimer
SDL_AddTimer.restype = SDL_TimerID
SDL_AddTimer.argtypes = [Uint32, SDL_NewTimerCallback, c_void_p]
SDL_RemoveTimer = libSDL.SDL_RemoveTimer
SDL_RemoveTimer.restype = SDL_bool
SDL_RemoveTimer.argtypes = [SDL_TimerID]
class SDL_version(Structure):
    pass
SDL_version._external_ = True
SDL_version._fields_ = [
    ('major', Uint8),
    ('minor', Uint8),
    ('patch', Uint8),
]
SDL_Linked_Version = libSDL.SDL_Linked_Version
SDL_Linked_Version.restype = POINTER(SDL_version)
SDL_Linked_Version.argtypes = []
class SDL_Color(Structure):
    pass
SDL_Color._external_ = True
SDL_Color._fields_ = [
    ('r', Uint8),
    ('g', Uint8),
    ('b', Uint8),
    ('unused', Uint8),
]
class SDL_Palette(Structure):
    pass
SDL_Palette._external_ = True
SDL_Palette._fields_ = [
    ('ncolors', c_int),
    ('colors', POINTER(SDL_Color)),
]
class SDL_PixelFormat(Structure):
    pass
SDL_PixelFormat._external_ = True
SDL_PixelFormat._fields_ = [
    ('palette', POINTER(SDL_Palette)),
    ('BitsPerPixel', Uint8),
    ('BytesPerPixel', Uint8),
    ('Rloss', Uint8),
    ('Gloss', Uint8),
    ('Bloss', Uint8),
    ('Aloss', Uint8),
    ('Rshift', Uint8),
    ('Gshift', Uint8),
    ('Bshift', Uint8),
    ('Ashift', Uint8),
    ('Rmask', Uint32),
    ('Gmask', Uint32),
    ('Bmask', Uint32),
    ('Amask', Uint32),
    ('colorkey', Uint32),
    ('alpha', Uint8),
]
class SDL_Surface(Structure):
    pass
SDL_Surface._external_ = True
#class private_hwdata(Structure):
#    pass
#private_hwdata._external_ = True
#class SDL_BlitMap(Structure):
#    pass
#SDL_BlitMap._external_ = True
SDL_Surface._fields_ = [
    ('flags', Uint32),
    ('format', POINTER(SDL_PixelFormat)),
    ('w', c_int),
    ('h', c_int),
    ('pitch', Uint16),
    ('pixels', c_void_p),
    ('offset', c_int),
#    ('hwdata', POINTER(private_hwdata)),
    ('clip_rect', SDL_Rect),
    ('unused1', Uint32),
    ('locked', Uint32),
#    ('map', POINTER(SDL_BlitMap)),
    ('format_version', c_uint),
    ('refcount', c_int),
]
#private_hwdata._fields_ = [
#]
#SDL_BlitMap._fields_ = [
#]
SDL_blit = CFUNCTYPE(c_int, POINTER(SDL_Surface), POINTER(SDL_Rect), POINTER(SDL_Surface), POINTER(SDL_Rect))
class SDL_VideoInfo(Structure):
    pass
SDL_VideoInfo._external_ = True
SDL_VideoInfo._fields_ = [
    ('hw_available', Uint32, 1),
    ('wm_available', Uint32, 1),
    ('UnusedBits1', Uint32, 6),
    ('UnusedBits2', Uint32, 1),
    ('blit_hw', Uint32, 1),
    ('blit_hw_CC', Uint32, 1),
    ('blit_hw_A', Uint32, 1),
    ('blit_sw', Uint32, 1),
    ('blit_sw_CC', Uint32, 1),
    ('blit_sw_A', Uint32, 1),
    ('blit_fill', Uint32, 1),
    ('UnusedBits3', Uint32, 16),
    ('video_mem', Uint32),
    ('vfmt', POINTER(SDL_PixelFormat)),
    ('current_w', c_int),
    ('current_h', c_int),
]
class SDL_Overlay(Structure):
    pass
SDL_Overlay._external_ = True
#class private_yuvhwfuncs(Structure):
#    pass
#private_yuvhwfuncs._external_ = True
#class private_yuvhwdata(Structure):
#    pass
#private_yuvhwdata._external_ = True
SDL_Overlay._fields_ = [
    ('format', Uint32),
    ('w', c_int),
    ('h', c_int),
    ('planes', c_int),
    ('pitches', POINTER(Uint16)),
    ('pixels', POINTER(POINTER(Uint8))),
#    ('hwfuncs', POINTER(private_yuvhwfuncs)),
#    ('hwdata', POINTER(private_yuvhwdata)),
    ('hw_overlay', Uint32, 1),
    ('UnusedBits', Uint32, 31),
]
#private_yuvhwfuncs._fields_ = [
#]
#private_yuvhwdata._fields_ = [
#]

# values for enumeration 'SDL_GLattr'
SDL_GLattr = c_int # enum
SDL_VideoInit = libSDL.SDL_VideoInit
SDL_VideoInit.restype = c_int
SDL_VideoInit.argtypes = [STRING, Uint32]
SDL_VideoQuit = libSDL.SDL_VideoQuit
SDL_VideoQuit.restype = None
SDL_VideoQuit.argtypes = []
SDL_VideoDriverName = libSDL.SDL_VideoDriverName
SDL_VideoDriverName.restype = STRING
SDL_VideoDriverName.argtypes = [STRING, c_int]
SDL_GetVideoSurface = libSDL.SDL_GetVideoSurface
SDL_GetVideoSurface.restype = POINTER(SDL_Surface)
SDL_GetVideoSurface.argtypes = []
SDL_GetVideoInfo = libSDL.SDL_GetVideoInfo
SDL_GetVideoInfo.restype = POINTER(SDL_VideoInfo)
SDL_GetVideoInfo.argtypes = []
SDL_VideoModeOK = libSDL.SDL_VideoModeOK
SDL_VideoModeOK.restype = c_int
SDL_VideoModeOK.argtypes = [c_int, c_int, c_int, Uint32]
SDL_ListModes = libSDL.SDL_ListModes
SDL_ListModes.restype = POINTER(POINTER(SDL_Rect))
SDL_ListModes.argtypes = [POINTER(SDL_PixelFormat), Uint32]
SDL_SetVideoMode = libSDL.SDL_SetVideoMode
SDL_SetVideoMode.restype = POINTER(SDL_Surface)
SDL_SetVideoMode.argtypes = [c_int, c_int, c_int, Uint32]
SDL_UpdateRects = libSDL.SDL_UpdateRects
SDL_UpdateRects.restype = None
SDL_UpdateRects.argtypes = [POINTER(SDL_Surface), c_int, POINTER(SDL_Rect)]
SDL_UpdateRect = libSDL.SDL_UpdateRect
SDL_UpdateRect.restype = None
SDL_UpdateRect.argtypes = [POINTER(SDL_Surface), Sint32, Sint32, Uint32, Uint32]
SDL_Flip = libSDL.SDL_Flip
SDL_Flip.restype = c_int
SDL_Flip.argtypes = [POINTER(SDL_Surface)]
SDL_SetGamma = libSDL.SDL_SetGamma
SDL_SetGamma.restype = c_int
SDL_SetGamma.argtypes = [c_float, c_float, c_float]
SDL_SetGammaRamp = libSDL.SDL_SetGammaRamp
SDL_SetGammaRamp.restype = c_int
SDL_SetGammaRamp.argtypes = [POINTER(Uint16), POINTER(Uint16), POINTER(Uint16)]
SDL_GetGammaRamp = libSDL.SDL_GetGammaRamp
SDL_GetGammaRamp.restype = c_int
SDL_GetGammaRamp.argtypes = [POINTER(Uint16), POINTER(Uint16), POINTER(Uint16)]
SDL_SetColors = libSDL.SDL_SetColors
SDL_SetColors.restype = c_int
SDL_SetColors.argtypes = [POINTER(SDL_Surface), POINTER(SDL_Color), c_int, c_int]
SDL_SetPalette = libSDL.SDL_SetPalette
SDL_SetPalette.restype = c_int
SDL_SetPalette.argtypes = [POINTER(SDL_Surface), c_int, POINTER(SDL_Color), c_int, c_int]
SDL_MapRGB = libSDL.SDL_MapRGB
SDL_MapRGB.restype = Uint32
SDL_MapRGB.argtypes = [POINTER(SDL_PixelFormat), Uint8, Uint8, Uint8]
SDL_MapRGBA = libSDL.SDL_MapRGBA
SDL_MapRGBA.restype = Uint32
SDL_MapRGBA.argtypes = [POINTER(SDL_PixelFormat), Uint8, Uint8, Uint8, Uint8]
SDL_GetRGB = libSDL.SDL_GetRGB
SDL_GetRGB.restype = None
SDL_GetRGB.argtypes = [Uint32, POINTER(SDL_PixelFormat), POINTER(Uint8), POINTER(Uint8), POINTER(Uint8)]
SDL_GetRGBA = libSDL.SDL_GetRGBA
SDL_GetRGBA.restype = None
SDL_GetRGBA.argtypes = [Uint32, POINTER(SDL_PixelFormat), POINTER(Uint8), POINTER(Uint8), POINTER(Uint8), POINTER(Uint8)]
SDL_CreateRGBSurface = libSDL.SDL_CreateRGBSurface
SDL_CreateRGBSurface.restype = POINTER(SDL_Surface)
SDL_CreateRGBSurface.argtypes = [Uint32, c_int, c_int, c_int, Uint32, Uint32, Uint32, Uint32]
SDL_CreateRGBSurfaceFrom = libSDL.SDL_CreateRGBSurfaceFrom
SDL_CreateRGBSurfaceFrom.restype = POINTER(SDL_Surface)
SDL_CreateRGBSurfaceFrom.argtypes = [c_void_p, c_int, c_int, c_int, c_int, Uint32, Uint32, Uint32, Uint32]
SDL_FreeSurface = libSDL.SDL_FreeSurface
SDL_FreeSurface.restype = None
SDL_FreeSurface.argtypes = [POINTER(SDL_Surface)]
SDL_LockSurface = libSDL.SDL_LockSurface
SDL_LockSurface.restype = c_int
SDL_LockSurface.argtypes = [POINTER(SDL_Surface)]
SDL_UnlockSurface = libSDL.SDL_UnlockSurface
SDL_UnlockSurface.restype = None
SDL_UnlockSurface.argtypes = [POINTER(SDL_Surface)]
SDL_LoadBMP_RW = libSDL.SDL_LoadBMP_RW
SDL_LoadBMP_RW.restype = POINTER(SDL_Surface)
SDL_LoadBMP_RW.argtypes = [POINTER(SDL_RWops), c_int]
SDL_SaveBMP_RW = libSDL.SDL_SaveBMP_RW
SDL_SaveBMP_RW.restype = c_int
SDL_SaveBMP_RW.argtypes = [POINTER(SDL_Surface), POINTER(SDL_RWops), c_int]
SDL_SetColorKey = libSDL.SDL_SetColorKey
SDL_SetColorKey.restype = c_int
SDL_SetColorKey.argtypes = [POINTER(SDL_Surface), Uint32, Uint32]
SDL_SetAlpha = libSDL.SDL_SetAlpha
SDL_SetAlpha.restype = c_int
SDL_SetAlpha.argtypes = [POINTER(SDL_Surface), Uint32, Uint8]
SDL_SetClipRect = libSDL.SDL_SetClipRect
SDL_SetClipRect.restype = SDL_bool
SDL_SetClipRect.argtypes = [POINTER(SDL_Surface), POINTER(SDL_Rect)]
SDL_GetClipRect = libSDL.SDL_GetClipRect
SDL_GetClipRect.restype = None
SDL_GetClipRect.argtypes = [POINTER(SDL_Surface), POINTER(SDL_Rect)]
SDL_ConvertSurface = libSDL.SDL_ConvertSurface
SDL_ConvertSurface.restype = POINTER(SDL_Surface)
SDL_ConvertSurface.argtypes = [POINTER(SDL_Surface), POINTER(SDL_PixelFormat), Uint32]
SDL_UpperBlit = libSDL.SDL_UpperBlit
SDL_UpperBlit.restype = c_int
SDL_UpperBlit.argtypes = [POINTER(SDL_Surface), POINTER(SDL_Rect), POINTER(SDL_Surface), POINTER(SDL_Rect)]
SDL_LowerBlit = libSDL.SDL_LowerBlit
SDL_LowerBlit.restype = c_int
SDL_LowerBlit.argtypes = [POINTER(SDL_Surface), POINTER(SDL_Rect), POINTER(SDL_Surface), POINTER(SDL_Rect)]
SDL_FillRect = libSDL.SDL_FillRect
SDL_FillRect.restype = c_int
SDL_FillRect.argtypes = [POINTER(SDL_Surface), POINTER(SDL_Rect), Uint32]
SDL_DisplayFormat = libSDL.SDL_DisplayFormat
SDL_DisplayFormat.restype = POINTER(SDL_Surface)
SDL_DisplayFormat.argtypes = [POINTER(SDL_Surface)]
SDL_DisplayFormatAlpha = libSDL.SDL_DisplayFormatAlpha
SDL_DisplayFormatAlpha.restype = POINTER(SDL_Surface)
SDL_DisplayFormatAlpha.argtypes = [POINTER(SDL_Surface)]
SDL_CreateYUVOverlay = libSDL.SDL_CreateYUVOverlay
SDL_CreateYUVOverlay.restype = POINTER(SDL_Overlay)
SDL_CreateYUVOverlay.argtypes = [c_int, c_int, Uint32, POINTER(SDL_Surface)]
SDL_LockYUVOverlay = libSDL.SDL_LockYUVOverlay
SDL_LockYUVOverlay.restype = c_int
SDL_LockYUVOverlay.argtypes = [POINTER(SDL_Overlay)]
SDL_UnlockYUVOverlay = libSDL.SDL_UnlockYUVOverlay
SDL_UnlockYUVOverlay.restype = None
SDL_UnlockYUVOverlay.argtypes = [POINTER(SDL_Overlay)]
SDL_DisplayYUVOverlay = libSDL.SDL_DisplayYUVOverlay
SDL_DisplayYUVOverlay.restype = c_int
SDL_DisplayYUVOverlay.argtypes = [POINTER(SDL_Overlay), POINTER(SDL_Rect)]
SDL_FreeYUVOverlay = libSDL.SDL_FreeYUVOverlay
SDL_FreeYUVOverlay.restype = None
SDL_FreeYUVOverlay.argtypes = [POINTER(SDL_Overlay)]
SDL_GL_LoadLibrary = libSDL.SDL_GL_LoadLibrary
SDL_GL_LoadLibrary.restype = c_int
SDL_GL_LoadLibrary.argtypes = [STRING]
SDL_GL_GetProcAddress = libSDL.SDL_GL_GetProcAddress
SDL_GL_GetProcAddress.restype = c_void_p
SDL_GL_GetProcAddress.argtypes = [STRING]
SDL_GL_SetAttribute = libSDL.SDL_GL_SetAttribute
SDL_GL_SetAttribute.restype = c_int
SDL_GL_SetAttribute.argtypes = [SDL_GLattr, c_int]
SDL_GL_GetAttribute = libSDL.SDL_GL_GetAttribute
SDL_GL_GetAttribute.restype = c_int
SDL_GL_GetAttribute.argtypes = [SDL_GLattr, POINTER(c_int)]
SDL_GL_SwapBuffers = libSDL.SDL_GL_SwapBuffers
SDL_GL_SwapBuffers.restype = None
SDL_GL_SwapBuffers.argtypes = []
SDL_GL_UpdateRects = libSDL.SDL_GL_UpdateRects
SDL_GL_UpdateRects.restype = None
SDL_GL_UpdateRects.argtypes = [c_int, POINTER(SDL_Rect)]
SDL_GL_Lock = libSDL.SDL_GL_Lock
SDL_GL_Lock.restype = None
SDL_GL_Lock.argtypes = []
SDL_GL_Unlock = libSDL.SDL_GL_Unlock
SDL_GL_Unlock.restype = None
SDL_GL_Unlock.argtypes = []
SDL_WM_SetCaption = libSDL.SDL_WM_SetCaption
SDL_WM_SetCaption.restype = None
SDL_WM_SetCaption.argtypes = [STRING, STRING]
SDL_WM_GetCaption = libSDL.SDL_WM_GetCaption
SDL_WM_GetCaption.restype = None
SDL_WM_GetCaption.argtypes = [POINTER(STRING), POINTER(STRING)]
SDL_WM_SetIcon = libSDL.SDL_WM_SetIcon
SDL_WM_SetIcon.restype = None
SDL_WM_SetIcon.argtypes = [POINTER(SDL_Surface), POINTER(Uint8)]
SDL_WM_IconifyWindow = libSDL.SDL_WM_IconifyWindow
SDL_WM_IconifyWindow.restype = c_int
SDL_WM_IconifyWindow.argtypes = []
SDL_WM_ToggleFullScreen = libSDL.SDL_WM_ToggleFullScreen
SDL_WM_ToggleFullScreen.restype = c_int
SDL_WM_ToggleFullScreen.argtypes = [POINTER(SDL_Surface)]

# values for enumeration 'SDL_GrabMode'
SDL_GrabMode = c_int # enum
SDL_WM_GrabInput = libSDL.SDL_WM_GrabInput
SDL_WM_GrabInput.restype = SDL_GrabMode
SDL_WM_GrabInput.argtypes = [SDL_GrabMode]
SDL_SoftStretch = libSDL.SDL_SoftStretch
SDL_SoftStretch.restype = c_int
SDL_SoftStretch.argtypes = [POINTER(SDL_Surface), POINTER(SDL_Rect), POINTER(SDL_Surface), POINTER(SDL_Rect)]


SDL_YVYU_OVERLAY =  0x55595659
SDL_BYTEORDER =  1234
SDL_PHYSPAL =  0x02
SDL_CDROM_LINUX =  1
SDL_PATCHLEVEL =  11
SDL_ASYNCBLIT =  0x00000004
SDL_RESIZABLE =  0x00000010
SDL_APPMOUSEFOCUS =  0x01
SDL_MIX_MAXVOLUME =  128
SDL_INIT_NOPARACHUTE =  0x00100000
SDL_BUTTON_LEFT =  1
SDL_VIDEO_DRIVER_X11_DPMS =  1
SDL_VIDEO_DRIVER_X11_XINERAMA =  1
SDL_RLEACCEL =  0x00004000
SDL_PREALLOC =  0x01000000
SDL_QUERY =  -1
SDL_INIT_VIDEO =  0x00000020
SDL_RLEACCELOK =  0x00002000
SDL_HAS_64BIT_TYPE =  1
SDL_AUDIO_DRIVER_OSS =  1
SDL_PRESSED =  1
SDL_JOYSTICK_LINUX =  1
SDL_MAJOR_VERSION =  1
SDL_YUY2_OVERLAY =  0x32595559
SDL_OPENGL =  0x00000002
SDL_DATA_TRACK =  0x04
SDL_UYVY_OVERLAY =  0x59565955
SDL_VIDEO_DRIVER_X11_VIDMODE =  1
SDL_VIDEO_OPENGL_GLX =  1
SDL_ANYFORMAT =  0x10000000
SDL_LOGPAL =  0x01
SDL_INIT_CDROM =  0x00000100
SDL_IYUV_OVERLAY =  0x56555949
SDL_VIDEO_DRIVER_X11 =  1
SDL_HWSURFACE =  0x00000001
SDL_HWPALETTE =  0x20000000
SDL_AUDIO_DRIVER_ALSA =  1
SDL_VIDEO_DRIVER_X11_XRANDR =  1
SDL_VIDEO_DRIVER_X11_DYNAMIC_XRENDER =  "libXrender.so.1"
SDL_APPINPUTFOCUS =  0x02
SDL_VIDEO_DRIVER_X11_DGAMOUSE =  1
SDL_ALPHA_TRANSPARENT =  0
SDL_DISABLE =  0
SDL_AUDIO_DRIVER_ESD =  1
SDL_AUDIO_DRIVER_DUMMY =  1
SDL_INIT_JOYSTICK =  0x00000200
SDL_SRCALPHA =  0x00010000
SDL_YV12_OVERLAY =  0x32315659
SDL_VIDEO_DRIVER_X11_XME =  1
SDL_AUDIO_DRIVER_ESD_DYNAMIC =  "libesd.so.0"
SDL_INIT_EVERYTHING =  0x0000FFFF
SDL_BUTTON_WHEELUP =  4
SDL_AUDIO_DRIVER_ARTS_DYNAMIC =  "libartsc.so.0"
SDL_DEFAULT_REPEAT_DELAY =  500
SDL_VIDEO_DRIVER_X11_DYNAMIC_XEXT =  "libXext.so.6"
SDL_VIDEO_DRIVER_DUMMY =  1
SDL_SRCCOLORKEY =  0x00001000
SDL_HAT_DOWN =  0x04
SDL_THREAD_PTHREAD =  1
SDL_AUDIO_DRIVER_DISK =  1
SDL_MAX_TRACKS =  99
SDL_BUTTON_RIGHT =  3
SDL_ASSEMBLY_ROUTINES =  1
SDL_APPACTIVE =  0x04
SDL_HAT_LEFT =  0x08
SDL_ALLEVENTS =  0xFFFFFFFF
SDL_DOUBLEBUF =  0x40000000
SDL_INIT_TIMER =  0x00000001
SDL_VIDEO_DRIVER_X11_DYNAMIC =  "libX11.so.6"
SDL_BIG_ENDIAN =  4321
SDL_NOFRAME =  0x00000020
SDL_LIL_ENDIAN =  1234
SDL_MINOR_VERSION =  2
SDL_INIT_AUDIO =  0x00000010
SDL_BUTTON_WHEELDOWN =  5
SDL_ENABLE =  1
SDL_BUTTON_MIDDLE =  2
SDL_HAT_UP =  0x01
SDL_SWSURFACE =  0x00000000
SDL_ALL_HOTKEYS =  0xFFFFFFFF
SDL_INIT_EVENTTHREAD =  0x01000000
SDL_VIDEO_DRIVER_X11_XV =  1
SDL_abs =  abs
SDL_HAT_RIGHT =  0x02
SDL_HAT_LEFTUP =  (SDL_HAT_LEFT|SDL_HAT_UP)
SDL_OPENGLBLIT =  0x0000000A
SDL_ALPHA_OPAQUE =  255
SDL_THREAD_PTHREAD_RECURSIVE_MUTEX =  1
SDL_TIMER_UNIX =  1
SDL_TIMESLICE =  10
SDL_HAT_CENTERED =  0x00
SDL_MUTEX_TIMEDOUT =  1
SDL_VIDEO_DRIVER_FBCON =  1
SDL_VIDEO_OPENGL =  1
SDL_IGNORE =  0
SDL_DEFAULT_REPEAT_INTERVAL =  30
SDL_AUDIO_TRACK =  0x00
SDL_VIDEO_DRIVER_X11_DYNAMIC_XRANDR =  "libXrandr.so.2"
SDL_VIDEO_DRIVER_DGA =  1
SDL_FULLSCREEN =  0x80000000
SDL_HWACCEL =  0x00000100
SDL_RELEASED =  0
SDL_AUDIO_DRIVER_ALSA_DYNAMIC =  "libasound.so.2"
SDL_HAT_LEFTDOWN =  (SDL_HAT_LEFT|SDL_HAT_DOWN)
SDL_AUDIO_DRIVER_ARTS =  1
SDL_LOADSO_DLOPEN =  1
