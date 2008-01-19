from pypy.tool.pairtype import extendabletype
from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.boolobject import W_BoolObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.translator.cli.dotnet import box

class __extend__(W_Root):
    __metaclass__ = extendabletype

    def tocli(self):
        return box(self)

class __extend__(W_IntObject):
    __metaclass__ = extendabletype

    def tocli(self):
        return box(self.intval)

class __extend__(W_FloatObject):
    __metaclass__ = extendabletype

    def tocli(self):
        return box(self.floatval)

class __extend__(W_NoneObject):
    __metaclass__ = extendabletype

    def tocli(self):
        return None

class __extend__(W_BoolObject):
    __metaclass__ = extendabletype

    def tocli(self):
        return box(self.boolval)

class __extend__(W_StringObject):
    __metaclass__ = extendabletype

    def tocli(self):
        return box(self._value)

from pypy.objspace.fake.objspace import W_Object as W_Object_Fake
from pypy.rlib.nonconst import NonConstant

class __extend__(W_Object_Fake):
    __metaclass__ = extendabletype

    def tocli(self):
        return NonConstant(None)
