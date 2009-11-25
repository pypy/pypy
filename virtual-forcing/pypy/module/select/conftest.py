import py

class Directory(py.test.collect.Directory):

    def run(self):
        try:
            import ctypes
        except ImportError:
            py.test.skip("these tests need ctypes installed")
        return super(Directory, self).run()
