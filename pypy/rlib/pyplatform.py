
""" This file contains various platform-specific profiles for
pypy's cross compilation
"""

import py

class Platform(object):
    def get_compiler(self):
        return None

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

class Maemo(Platform):
    def get_compiler(self):
        # XXX how to make this reliable???
        return '/scratchbox/compilers/cs2005q3.2-glibc-arm/bin/sbox-arm-linux-gcc'
    
    def execute(self, cmd):
        return py.process.cmdexec('/scratchbox/login ' + cmd)

class OverloadCompilerPlatform(Platform):
    def __init__(self, previous_platform, cc):
        self.previous_platform = previous_platform
        self.cc = cc

    def get_compiler(self):
        return self.cc

    def execute(self, cmd):
        return self.previous_platform.execute(cmd)

platform = Platform()

