from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform as platform
from pypy.rlib.rsdl.constants import _constants
from pypy.rlib.rsdl.eci import get_rsdl_compilation_info
from pypy.rlib.objectmodel import we_are_translated
import py
import sys

# ------------------------------------------------------------------------------

eci = get_rsdl_compilation_info()

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

# ------------------------------------------------------------------------------

RectPtr             = lltype.Ptr(lltype.ForwardReference())
SurfacePtr          = lltype.Ptr(lltype.ForwardReference())
PixelFormatPtr      = lltype.Ptr(lltype.ForwardReference())
EventPtr            = lltype.Ptr(lltype.ForwardReference())
KeyboardEventPtr    = lltype.Ptr(lltype.ForwardReference())
MouseButtonEventPtr = lltype.Ptr(lltype.ForwardReference())
MouseMotionEventPtr = lltype.Ptr(lltype.ForwardReference())
KeyPtr              = lltype.Ptr(lltype.ForwardReference())
RWopsPtr            = lltype.Ptr(lltype.ForwardReference())

# ------------------------------------------------------------------------------

class CConfig:
    _compilation_info_ = eci

    Uint8  = platform.SimpleType('Uint8',  rffi.INT)
    Uint16 = platform.SimpleType('Uint16', rffi.INT)
    Sint16 = platform.SimpleType('Sint16', rffi.INT)
    Uint32 = platform.SimpleType('Uint32', rffi.INT)

    Rect             = platform.Struct('SDL_Rect', 
                                    [('x', rffi.INT),
                                     ('y', rffi.INT),
                                     ('w', rffi.INT),
                                     ('h', rffi.INT)])
    
    Surface          = platform.Struct('SDL_Surface', 
                                    [('w', rffi.INT),
                                     ('h', rffi.INT),
                                     ('format', PixelFormatPtr),
                                     ('pitch', rffi.INT),
                                     ('pixels', rffi.UCHARP)])
    
    PixelFormat      = platform.Struct('SDL_PixelFormat',
                                    [('BitsPerPixel', rffi.INT),
                                     ('BytesPerPixel', rffi.INT),
                                     ('Rmask', rffi.INT),
                                     ('Gmask', rffi.INT),
                                     ('Bmask', rffi.INT),
                                     ('Amask', rffi.INT)])

    Event            = platform.Struct('SDL_Event',
                                    [('type', rffi.INT)])
    
    keysym           = platform.Struct('SDL_keysym', 
                                    [('scancode', rffi.INT),
                                     ('sym', rffi.INT),
                                     ('mod', rffi.INT),
                                     ('unicode', rffi.INT)])
    
    KeyboardEvent    = platform.Struct('SDL_KeyboardEvent',
                                    [('type', rffi.INT),
                                     ('state', rffi.INT),
                                     ('keysym', keysym)])
    
    MouseButtonEvent = platform.Struct('SDL_MouseButtonEvent',
                                    [('type', rffi.INT),
                                     ('button', rffi.INT),
                                     ('state', rffi.INT),
                                     ('x', rffi.INT),
                                     ('y', rffi.INT)])
    
    MouseMotionEvent = platform.Struct('SDL_MouseMotionEvent',
                                    [('type', rffi.INT),
                                     ('state', rffi.INT),
                                     ('x', rffi.INT),
                                     ('y', rffi.INT),
                                     ('xrel', rffi.INT),
                                     ('yrel', rffi.INT)])
    
    RWops = platform.Struct('SDL_RWops', [])

# ------------------------------------------------------------------------------

for _prefix, _list in _constants.items():
    for _name in _list:
        setattr(CConfig, _name, platform.ConstantInteger(_prefix+_name))

# ------------------------------------------------------------------------------

globals().update(platform.configure(CConfig))

# ------------------------------------------------------------------------------

RectPtr.TO.become(Rect)
SurfacePtr.TO.become(Surface)
PixelFormatPtr.TO.become(PixelFormat)
EventPtr.TO.become(Event)
KeyboardEventPtr.TO.become(KeyboardEvent)
MouseButtonEventPtr.TO.become(MouseButtonEvent)
MouseMotionEventPtr.TO.become(MouseMotionEvent)
RWopsPtr.TO.become(RWops)

# ------------------------------------------------------------------------------

Uint8P  = lltype.Ptr(lltype.Array(Uint8, hints={'nolength': True}))
Uint16P = lltype.Ptr(lltype.Array(Uint16, hints={'nolength': True}))
# need to add signed hint here
Sint16P = lltype.Ptr(lltype.Array(Sint16, hints={'nolength': True}))
Uint32P = lltype.Ptr(lltype.Array(Uint32, hints={'nolength': True}))


# ------------------------------------------------------------------------------

_Init            = external('SDL_Init', 
                             [Uint32], 
                             rffi.INT)
                                  
Mac_Init        = external('SDL_Init', 
                             [Uint32], 
                             rffi.INT)

Quit             = external('SDL_Quit', [], 
                            lltype.Void)

SetVideoMode     = external('SDL_SetVideoMode', 
                             [rffi.INT, rffi.INT, rffi.INT, Uint32],
                             SurfacePtr)

WM_SetCaption    = external('SDL_WM_SetCaption', 
                             [rffi.CCHARP, rffi.CCHARP],
                             lltype.Void)

EnableUNICODE    = external('SDL_EnableUNICODE', 
                             [rffi.INT], 
                             rffi.INT)

WaitEvent        = external('SDL_WaitEvent', 
                             [EventPtr], 
                             rffi.INT)

PollEvent        = external('SDL_PollEvent',
                             [EventPtr], 
                             rffi.INT)

Flip             = external('SDL_Flip', 
                             [SurfacePtr], 
                             rffi.INT)

CreateRGBSurface = external('SDL_CreateRGBSurface', 
                             [Uint32, rffi.INT, rffi.INT, rffi.INT,
                              Uint32, Uint32, Uint32, Uint32],
                             SurfacePtr)

LockSurface      = external('SDL_LockSurface', 
                             [SurfacePtr], 
                             rffi.INT)

UnlockSurface    = external('SDL_UnlockSurface', 
                             [SurfacePtr],
                             lltype.Void)

FreeSurface      = external('SDL_FreeSurface', 
                             [SurfacePtr],
                             lltype.Void)

MapRGB           = external('SDL_MapRGB', 
                             [PixelFormatPtr, Uint8, Uint8,  Uint8], 
                             Uint32)

GetRGB           = external('SDL_GetRGB',
                             [Uint32, PixelFormatPtr, Uint8P, Uint8P, Uint8P], 
                             lltype.Void)

GetRGBA          = external('SDL_GetRGBA', 
                             [Uint32, PixelFormatPtr, Uint8P, Uint8P, 
                             Uint8P, Uint8P], 
                             lltype.Void)

FillRect         = external('SDL_FillRect', 
                             [SurfacePtr, RectPtr, Uint32], 
                             rffi.INT)

BlitSurface      = external('SDL_UpperBlit', 
                             [SurfacePtr, RectPtr, SurfacePtr,  RectPtr], 
                             rffi.INT)

SetAlpha         = external('SDL_SetAlpha', 
                             [SurfacePtr, Uint32, Uint8], 
                             rffi.INT)

SetColorKey      = external('SDL_SetColorKey',
                            [SurfacePtr, Uint32, Uint32],
                            rffi.INT)

ShowCursor       = external('SDL_ShowCursor',
                            [rffi.INT],
                            rffi.INT)

Delay            = external('SDL_Delay',
                            [Uint32],
                            lltype.Void)

UpdateRect       = external('SDL_UpdateRect',
                            [SurfacePtr, rffi.INT, rffi.INT, rffi.INT],
                            lltype.Void)

GetKeyName       = external('SDL_GetKeyName',
                            [rffi.INT], 
                            rffi.CCHARP)

GetError         = external('SDL_GetError',
                            [],
                            rffi.CCHARP)

RWFromFile       = external('SDL_RWFromFile',
                            [rffi.CCHARP, rffi.CCHARP],
                            RWopsPtr)

# ------------------------------------------------------------------------------


if sys.platform == 'darwin':
    def Init(flags):
        if not we_are_translated():
            from AppKit import NSApplication
            NSApplication.sharedApplication()
        #CustomApplicationMain(0, " ")
        return _Init(flags)
        #Mac_Init()
else:
    Init = _Init
    
    
    
