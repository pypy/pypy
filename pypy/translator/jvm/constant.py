from pypy.translator.jvm.generator import \
     Field, Method, ACONST_NULL, ICONST, LDC, DCONST_0, DCONST_1, LDC2
from pypy.translator.oosupport.constant import \
     RecordConst, InstanceConst, ClassConst
from pypy.translator.jvm.typesystem import jPyPyConst

# ___________________________________________________________________________
# Simple Constants
#
# We create simple dummy constant objects that follow the same
# inteface as the complex constants from oosupport/constant.py.  None
# of these requires initialization, so they only support push() and
# they should never find their way into the database's constant list.

class Const(object):
    def push(self, gen):
        """ Emits code required to reference a constant.  Usually invoked
        by generator.emit() """
        raise NotImplementedError

class VoidConst(object):
    def push(self, gen):
        pass

class NullConst(object):
    def push(self, gen):
        gen.emit(ACONST_NULL)

class DoubleConst(Const):
    def __init__(self, value):
        self.value = value
    def push(self, gen):
        if value == 0.0:
            gen.emit(DCONST_0)
        elif value == 1.0:
            gen.emit(DCONST_1)
        else:
            gen.emit(LDC2, self.value)

class UnicodeConst(Const):
    def __init__(self, value):
        self.value = value
    def push(self, gen):
        assert isinstance(self.value, unicode)
        gen.emit(LDC, res)

# ___________________________________________________________________________
# Complex Constants

class JVMFieldStorage(object):
    """ A mix-in for the oosupport constant classes that stores the
    pointer for the constant into a field on a class.  It implements
    the push() and store() methods used by the oosupport classes and
    elsewhere."""
    def __init__(self):
        # Note that self.name and self.value are set by the oosupport
        # constance class:
        fieldty = self.db.lltype_to_cts(self.value._TYPE)
        self.fieldobj = Field(jPyPyConst.name, self.name, fieldty, True)
        
    def push(self, gen):
        self.fieldobj.load(gen)

    def store(self, gen):
        self.fieldobj.store(gen)

class JVMRecordConst(RecordConst, JVMFieldStorage):
    def __init__(self, db, record, count):
        RecordConst.__init__(self, db, record, count)
        JVMFieldStorage.__init__(self)

class JVMInstanceConst(InstanceConst, JVMFieldStorage):
    def __init__(self, db, obj, record, count):
        InstanceConst.__init__(self, db, obj, record, count)
        JVMFieldStorage.__init__(self)

class JVMClassConst(ClassConst, JVMFieldStorage):
    def __init__(self, db, class_, count):
        ClassConst.__init__(self, db, class_, count)
        JVMFieldStorage.__init__(self)

