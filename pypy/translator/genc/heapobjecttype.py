from __future__ import generators
from pypy.translator.genc.basetype import CType


class CHeapObjectType(CType):
    """The type 'pointer to an object in the heap'.  The object's layout must
    be an extension of another existing object layout (there is an empty
    base object, which in this version contains just a ref counter).
    The extension is by adding a single field to the parent.  This field can
    be a tuple (i.e. a struct), so you can add a bunch of data at once in this
    way.
    """
    error_return  = 'NULL'

    Counter = {}

    def __init__(self, translator, basetype, extensiontype, namehint):
        super(CHeapObjectType, self).__init__(translator)
        self.basetype = basetype
        if basetype is None:
            self.basetypename = 'baseobject'     # from object_include.h
            self.basestructname = 'struct s_baseobject'
        else:
            assert isinstance(basetype, CHeapObjectType)
            self.basetypename = self.basetype.typename
            self.basestructname = self.basetype.structname
        self.extensiontype = extensiontype

        while namehint.find('__') >= 0:
            namehint = namehint.replace('__', '_')
        key = namehint.upper()
        self.typename = 'P%d_%s' % (
            CHeapObjectType.Counter.setdefault(key, 0), namehint)
        self.structname = 'struct s_' + self.typename
        CHeapObjectType.Counter[key] += 1

    def nameof(self, cls, debug=None):
        XXX(Later)

    def init_globals(self, genc):
        yield genc.loadincludefile('heapobject_template.h') % {
            'typename'          : self.typename,
            'TYPENAME'          : self.typename.upper(),
            'basetypename'      : self.basetypename,
            'basestructname'    : self.basestructname,
            'extensiontypename' : self.extensiontype.typename,
            }
