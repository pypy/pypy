"""These are the original ctypes tests.
You can try to run them with 'pypy-c runtests.py'."""

import py

class Directory(py.test.collect.Directory):
    def run(self):
        py.test.skip(__doc__)
