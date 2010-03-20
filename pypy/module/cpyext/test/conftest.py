import py
from pypy.conftest import option

class Directory(py.test.collect.Directory):
    def collect(self):
        if option.runappdirect:
            py.test.skip("cannot be run by py.test -A")
        return super(Directory, self).collect()
