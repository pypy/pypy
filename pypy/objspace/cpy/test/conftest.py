
import py
from pypy.tool.pytest.modcheck import skipimporterror

class Directory(py.test.collect.Directory):
    def run(self):
        skipimporterror("ctypes")
        return super(Directory, self).run()
