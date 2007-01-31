from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.translator.cli.dotnet import box

def tocli(self):
    return None
W_Root.tocli = tocli

def tocli(self):
    return box(self.intval)
W_IntObject.tocli = tocli

def tocli(self):
    return box(self.floatval)
W_FloatObject.tocli = tocli


from pypy.objspace.fake.objspace import W_Object as W_Object_Fake
from pypy.rlib.nonconst import NonConstant

def tocli(self):
    return NonConstant(None)
W_Object_Fake.tocli = tocli
