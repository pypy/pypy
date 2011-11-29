import py, os

if os.name <> 'nt':
    NULLPATHNAME = '/dev/null'
else:
    NULLPATHNAME = 'NUL'

class NullPyPathLocal(py.path.local):

    def join(self, *args):
        return self.__class__(py.path.local.join(self, *args))

    def open(self, mode):
        return open(NULLPATHNAME, mode)

    def __repr__(self):
        return py.path.local.__repr__(self) + ' [fake]'
