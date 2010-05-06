from pypy.rlib.rsdl.eci import check_sdl_installation, SDLNotInstalled
import py

def pytest_collect_directory():
    try:
        check_sdl_installation()
    except SDLNotInstalled, e:
        py.test.skip("SDL not installed(?): %s" % (e,))
