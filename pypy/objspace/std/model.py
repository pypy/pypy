"""
The full list of which Python types and which implementation we want
to provide in this version of PyPy, along with conversion rules.
"""

from pypy.objspace.std.multimethod import MultiMethodTable, FailedToImplement
from pypy.interpreter.baseobjspace import W_Root, ObjSpace


class StdTypeModel:

    def __init__(self):
        """NOT_RPYTHON: inititialization only"""
        # All the Python types that we want to provide in this StdObjSpace
        class result:
            from pypy.objspace.std.objecttype import object_typedef
            from pypy.objspace.std.booltype   import bool_typedef
            from pypy.objspace.std.inttype    import int_typedef
            from pypy.objspace.std.floattype  import float_typedef
            from pypy.objspace.std.tupletype  import tuple_typedef
            from pypy.objspace.std.listtype   import list_typedef
            from pypy.objspace.std.dicttype   import dict_typedef
            from pypy.objspace.std.basestringtype import basestring_typedef
            from pypy.objspace.std.stringtype import str_typedef
            from pypy.objspace.std.typetype   import type_typedef
            from pypy.objspace.std.slicetype  import slice_typedef
            from pypy.objspace.std.longtype   import long_typedef
            from pypy.objspace.std.unicodetype import unicode_typedef
            from pypy.objspace.std.dictproxytype import dictproxy_typedef
        self.pythontypes = [value for key, value in result.__dict__.items()
                            if not key.startswith('_')]   # don't look

        # The object implementations that we want to 'link' into PyPy must be
        # imported here.  This registers them into the multimethod tables,
        # *before* the type objects are built from these multimethod tables.
        from pypy.objspace.std import objectobject
        from pypy.objspace.std import boolobject
        from pypy.objspace.std import intobject
        from pypy.objspace.std import floatobject
        from pypy.objspace.std import tupleobject
        from pypy.objspace.std import listobject
        from pypy.objspace.std import dictobject
        from pypy.objspace.std import stringobject
        from pypy.objspace.std import typeobject
        from pypy.objspace.std import sliceobject
        from pypy.objspace.std import longobject
        from pypy.objspace.std import noneobject
        from pypy.objspace.std import iterobject
        from pypy.objspace.std import unicodeobject
        from pypy.objspace.std import fake
        import pypy.objspace.std.default # register a few catch-all multimethods

        # the set of implementation types
        self.typeorder = {
            objectobject.W_ObjectObject: [],
            boolobject.W_BoolObject: [],
            intobject.W_IntObject: [],
            floatobject.W_FloatObject: [],
            tupleobject.W_TupleObject: [],
            listobject.W_ListObject: [],
            dictobject.W_DictObject: [],
            stringobject.W_StringObject: [],
            typeobject.W_TypeObject: [],
            sliceobject.W_SliceObject: [],
            longobject.W_LongObject: [],
            noneobject.W_NoneObject: [],
            iterobject.W_SeqIterObject: [],
            unicodeobject.W_UnicodeObject: [],
            }
        for type in self.typeorder:
            self.typeorder[type].append((type, None))

        # register the order in which types are converted into each others
        # when trying to dispatch multimethods.
        # XXX build these lists a bit more automatically later
        self.typeorder[boolobject.W_BoolObject] += [
            (intobject.W_IntObject,     boolobject.delegate_Bool2Int),
            (longobject.W_LongObject,   longobject.delegate_Bool2Long),
            (floatobject.W_FloatObject, floatobject.delegate_Bool2Float),
            ]
        self.typeorder[intobject.W_IntObject] += [
            (longobject.W_LongObject,   longobject.delegate_Int2Long),
            (floatobject.W_FloatObject, floatobject.delegate_Int2Float),
            ]
        self.typeorder[longobject.W_LongObject] += [
            (floatobject.W_FloatObject, longobject.delegate_Long2Float),
            ]
        self.typeorder[stringobject.W_StringObject] += [
         (unicodeobject.W_UnicodeObject, unicodeobject.delegate_String2Unicode),
            ]

        # put W_Root everywhere
        self.typeorder[W_Root] = []
        for type in self.typeorder:
            self.typeorder[type].append((W_Root, None))


# ____________________________________________________________

W_ANY = W_Root

class W_Object(W_Root, object):
    "Parent base class for wrapped objects."
    typedef = None

    def __init__(w_self, space):
        w_self.space = space     # XXX not sure this is ever used any more

    def __repr__(self):
        s = '%s(%s)' % (
            self.__class__.__name__,
           #', '.join(['%s=%r' % keyvalue for keyvalue in self.__dict__.items()])
            getattr(self, 'name', '')
            )
        if hasattr(self, 'w__class__'):
            s += ' instance of %s' % self.w__class__
        return '<%s>' % s

    def unwrap(w_self):
        raise UnwrapError, 'cannot unwrap %r' % (w_self,)

class UnwrapError(Exception):
    pass


class MultiMethod(MultiMethodTable):

    def __init__(self, operatorsymbol, arity, specialnames=None, **extras):
        """NOT_RPYTHON: cannot create new multimethods dynamically.
        """
        MultiMethodTable.__init__(self, arity, W_ANY,
                                  argnames_before = ['space'])
        self.operatorsymbol = operatorsymbol
        if specialnames is None:
            specialnames = [operatorsymbol]
        self.specialnames = specialnames  # e.g. ['__xxx__', '__rxxx__']
        self.extras = extras
        self.unbound_versions = {}
        # transform  '+'  =>  'add'  etc.
        for line in ObjSpace.MethodTable:
            realname, symbolname = line[:2]
            if symbolname == operatorsymbol:
                self.name = realname
                break
        else:
            self.name = operatorsymbol

        if extras.get('general__args__', False):
            self.argnames_after = ['__args__']
        if extras.get('w_varargs', False):
            self.argnames_after = ['w_args']
        if extras.get('varargs_w', False):
            self.argnames_after = ['args_w']            

    def install_not_sliced(self, typeorder, baked_perform_call=True):
        return self.install(prefix = '__mm_' + self.name,
                list_of_typeorders = [typeorder]*self.arity,
                baked_perform_call=baked_perform_call)
