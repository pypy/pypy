from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.interpreter.error import OperationError

from sys import maxint

unicode_capitalize = MultiMethod('capitalize', 1)
unicode_center     = MultiMethod('center', 3, defaults=(' ',))
unicode_count      = MultiMethod('count', 4, defaults=(0, maxint))      
unicode_encode     = MultiMethod('encode', 3, defaults=(None, None))
unicode_endswith   = MultiMethod('endswith', 4, defaults=(0,maxint))
unicode_expandtabs = MultiMethod('expandtabs', 2, defaults=(8,))
unicode_find       = MultiMethod('find', 4, defaults=(0, maxint))
unicode_index      = MultiMethod('index', 4, defaults=(0, maxint))
unicode_isalnum    = MultiMethod('isalnum', 1)
unicode_isalpha    = MultiMethod('isalpha', 1)
unicode_isdecimal  = MultiMethod('isdecimal', 1)
unicode_isdigit    = MultiMethod('isdigit', 1)
unicode_islower    = MultiMethod('islower', 1)
unicode_isnumeric  = MultiMethod('isnumeric', 1)
unicode_isspace    = MultiMethod('isspace', 1)
unicode_istitle    = MultiMethod('istitle', 1)
unicode_isupper    = MultiMethod('isupper', 1)
unicode_join       = MultiMethod('join', 2)
unicode_ljust      = MultiMethod('ljust', 3, defaults=(' ',))
unicode_lower      = MultiMethod('lower', 1)
unicode_lstrip     = MultiMethod('lstrip', 2, defaults=(None,))
unicode_replace    = MultiMethod('replace', 4, defaults=(-1,))
unicode_rfind      = MultiMethod('rfind', 4, defaults=(0, maxint))
unicode_rindex     = MultiMethod('rindex', 4, defaults=(0, maxint))
unicode_rjust      = MultiMethod('rjust', 3, defaults=(' ',))
unicode_rstrip     = MultiMethod('rstrip', 2, defaults=(None,))
unicode_rsplit     = MultiMethod('rsplit', 3, defaults=(None,-1))
unicode_split      = MultiMethod('split', 3, defaults=(None,-1))
unicode_splitlines = MultiMethod('splitlines', 2, defaults=(0,))
unicode_startswith = MultiMethod('startswith', 4, defaults=(0,maxint))
unicode_strip      = MultiMethod('strip',  2, defaults=(None,))
unicode_swapcase   = MultiMethod('swapcase', 1)
unicode_title      = MultiMethod('title', 1)
unicode_translate  = MultiMethod('translate', 2)
unicode_upper      = MultiMethod('upper', 1)
unicode_zfill      = MultiMethod('zfill', 2)
unicode_getslice   = MultiMethod('__getslice__', 3)
# ____________________________________________________________

app = gateway.applevel('''
import codecs, sys

def unicode_from_encoded_object(obj, encoding, errors):
    if encoding is None:
        encoding = sys.getdefaultencoding()
    decoder = codecs.getdecoder(encoding)
    if errors is None:
        retval, length = decoder(obj)
    else:
        retval, length = decoder(obj, errors)
    if not isinstance(retval, unicode):
        raise TypeError("decoder did not return an unicode object (type=%s)" %
                        type(retval).__name__)
    return retval

def unicode_from_object(obj):
    if isinstance(obj, str):
        res = obj
    else:
        try:
            unicode_method = obj.__unicode__
        except AttributeError:
            res = str(obj)
        else:
            res = unicode_method()
    if isinstance(res, unicode):
        return res
    return unicode_from_encoded_object(res, None, "strict")
    
''')
unicode_from_object = app.interphook('unicode_from_object')
unicode_from_encoded_object = app.interphook('unicode_from_encoded_object')


def descr__new__(space, w_unicodetype, w_obj=None, w_encoding=None, w_errors=None):
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    w_obj_type = space.type(w_obj)
    
    if space.is_w(w_obj_type, space.w_unicode):
        if (not space.is_w(w_encoding, space.w_None) or
            not space.is_w(w_errors, space.w_None)):
            raise OperationError(space.w_TypeError,
                                 space.wrap('decoding Unicode is not supported'))
        if space.is_w(w_unicodetype, space.w_unicode):
            return w_obj
        w_value = w_obj
    elif space.is_w(w_obj, space.w_None):
        w_value = W_UnicodeObject(space, [])
    elif (space.is_w(w_encoding, space.w_None) and
          space.is_w(w_errors, space.w_None)):
        if space.is_true(space.isinstance(w_obj, space.w_unicode)):
            w_value = w_obj
        else:
            w_value = unicode_from_object(space, w_obj)
    else:
        w_value = unicode_from_encoded_object(space, w_obj, w_encoding, w_errors)
    # help the annotator! also the ._value depends on W_UnicodeObject layout
    assert isinstance(w_value, W_UnicodeObject)
    w_newobj = space.allocate_instance(W_UnicodeObject, w_unicodetype)
    W_UnicodeObject.__init__(w_newobj, space, w_value._value)
    return w_newobj

# ____________________________________________________________

unicode_typedef = StdTypeDef("unicode", basestring_typedef,
    __new__ = newmethod(descr__new__),
    __doc__ = '''unicode(string [, encoding[, errors]]) -> object

Create a new Unicode object from the given encoded string.
encoding defaults to the current default string encoding.
errors can be 'strict', 'replace' or 'ignore' and defaults to 'strict'.'''
    )
unicode_typedef.registermethods(globals())
