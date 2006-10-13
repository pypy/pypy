"""
Translation between PyPy ootypesystem and JVM type system.

Here are some tentative non-obvious decisions:

Signed scalar types mostly map as is.  

Unsigned scalar types are a problem; the basic idea is to store them
as signed values, but execute special code when working with them.  Another
option would be to use classes, or to use the "next larger" type and remember to use appropriate modulos.  The jury is out on
this.  Another idea would be to add a variant type system that does
not have unsigned values, and write the required helper and conversion
methods in RPython --- then it could be used for multiple backends.

Python strings are mapped to byte arrays, not Java Strings, since
Python strings are really sets of bytes, not unicode code points.
Jury is out on this as well; this is not the approach taken by cli,
for example.

Python Unicode strings, on the other hand, map directly to Java Strings.

WeakRefs can hopefully map to Java Weak References in a straight
forward fashion.

Collections can hopefully map to Java collections instances.  Note
that JVM does not have an idea of generic typing at its lowest level
(well, they do have signature attributes, but those don't really count
for much).

"""


_lltype_to_cts = {
    ootype.Void: 'void',
    ootype.Signed: 'I',    
    ootype.Unsigned: 'I',    
    SignedLongLong: 'int64',
    UnsignedLongLong: 'unsigned int64',
    ootype.Bool: 'bool',
    ootype.Float: 'float64',
    ootype.Char: 'char',
    ootype.UniChar: 'char',
    ootype.Class: 'class [mscorlib]System.Type',
    ootype.String: 'string',
    ootype.StringBuilder: 'class ' + PYPY_STRING_BUILDER,
    WeakGcAddress: 'class ' + WEAKREF,

    # maps generic types to their ordinal
    ootype.List.SELFTYPE_T: 'class ' + (PYPY_LIST % '!0'),
    ootype.List.ITEMTYPE_T: '!0',
    ootype.Dict.SELFTYPE_T: 'class ' + (PYPY_DICT % ('!0', '!1')),
    ootype.Dict.KEYTYPE_T: '!0',
    ootype.Dict.VALUETYPE_T: '!1',
    ootype.DictItemsIterator.SELFTYPE_T: 'class ' + (PYPY_DICT_ITEMS_ITERATOR % ('!0', '!1')),
    ootype.DictItemsIterator.KEYTYPE_T: '!0',
    ootype.DictItemsIterator.VALUETYPE_T: '!1',
    }
