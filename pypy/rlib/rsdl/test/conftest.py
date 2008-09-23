from pypy.rlib.rsdl.eci import check_sdl_installation, SDLNotInstalled
import py

class Directory(py.test.collect.Directory):
    def run(self):
        try:
            check_sdl_installation()
        except SDLNotInstalled, e:
            py.test.skip("SDL not installed(?): %s" % (e,))
        return py.test.collect.Directory.run(self)
