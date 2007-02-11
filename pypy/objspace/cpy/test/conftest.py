
import py

try:
    import ctypes
except ImportError:
    ctypes = None

class Directory(py.test.collect.Directory):
    def run(self):
        if ctypes is None:
            py.test.skip("no ctypes module available")
        return super(Directory, self).run()
