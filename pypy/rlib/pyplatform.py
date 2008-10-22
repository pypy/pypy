
""" This file contains various platform-specific profiles for
pypy's cross compilation

"""

import py

# XXX i think the below belongs somewhere under pypy/translator 

class Platform(object):
    def __init__(self, cc=None):
        self.cc = cc

    def get_compiler(self):
        return self.cc 

    def execute(self, cmd):
        return py.process.cmdexec(cmd)

    # platform objects are immutable

    def __hash__(self):
        return hash(self.__class__.__name__)

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.__dict__ == other.__dict__)

    def __repr__(self):
        return '<Platform %s (%s)>' % (self.__class__.__name__, self.cc)

class Maemo(Platform):
    def __init__(self, cc=None):
        if cc is None:
            for x in (
                '/scratchbox/compilers/cs2007q3-glibc2.5-arm7/bin/arm-none-linux-gnueabi-gcc',
                '/scratchbox/compilers/cs2007q3-glibc2.5-arm6/bin/arm-none-linux-gnueabi-gcc',
                '/scratchbox/compilers/cs2005q3.2-glibc-arm/bin/sbox-arm-linux-gcc',
            ):
                if py.path.local(x).check():
                    cc = x
                    break
            else:
                raise ValueError("could not find scratchbox cross-compiler")
        Platform.__init__(self, cc=cc)
        
    def execute(self, cmd):
        return py.process.cmdexec('/scratchbox/login ' + cmd)

platform = Platform()

