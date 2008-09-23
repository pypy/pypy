import py
from pypy.rlib.rsdl import RSDL
from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import rffi


def test_sdl_init():
    assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
    RSDL.Quit()

def test_surface_basic():
    assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
    surface = RSDL.CreateRGBSurface(0, 150, 50, 32,
                                    r_uint(0x000000FF),
                                    r_uint(0x0000FF00),
                                    r_uint(0x00FF0000),
                                    r_uint(0xFF000000))
    assert surface
    assert rffi.getintfield(surface, 'c_w') == 150
    assert rffi.getintfield(surface, 'c_h') == 50
    RSDL.FreeSurface(surface)
    RSDL.Quit()
    
    
def test_get_keyname():
    assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
    assert RSDL.GetKeyName(RSDL.K_PLUS)[0] == '+'
    assert RSDL.GetKeyName(RSDL.K_RIGHTPAREN)[0] == ')'
    assert RSDL.GetKeyName(RSDL.K_z)[0] == 'z'
    
