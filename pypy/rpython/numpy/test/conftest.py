import py

class Directory(py.test.collect.Directory):

    def run(self):
        try:
            import numpy
        except ImportError:
            py.test.skip("these tests need numpy installed")
        return super(Directory, self).run()
