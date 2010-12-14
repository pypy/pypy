from pypy.rlib.rsdl.eci import check_sdl_installation, SDLNotInstalled
import py

def pytest_ignore_collect(path):
    try:
        check_sdl_installation()
    except SDLNotInstalled, e:
        return True
    else:
        return False
