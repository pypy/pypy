from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.boolobject import W_BoolObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.translator.cli.dotnet import box

def tocli(self):
    return box(self)
W_Root.tocli = tocli

def tocli(self):
    return box(self.intval)
W_IntObject.tocli = tocli

def tocli(self):
    return box(self.floatval)
W_FloatObject.tocli = tocli

def tocli(self):
    return None
W_NoneObject.tocli = tocli

def tocli(self):
    return box(self.boolval)
W_BoolObject.tocli = tocli

def tocli(self):
    return box(self._value)
W_StringObject.tocli = tocli

from pypy.objspace.fake.objspace import W_Object as W_Object_Fake
from pypy.rlib.nonconst import NonConstant

def tocli(self):
    return NonConstant(None)
W_Object_Fake.tocli = tocli
