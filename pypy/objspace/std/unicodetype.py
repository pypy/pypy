from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.interpreter.error import OperationError

from sys import maxint

unicode_capitalize = StdObjspaceMultiMethod('capitalize', 1)
unicode_center     = StdObjspaceMultiMethod('center', 3, defaults=(' ',))
unicode_count      = StdObjspaceMultiMethod('count', 4, defaults=(0, maxint))      
unicode_encode     = StdObjspaceMultiMethod('encode', 3, defaults=(None, None))
unicode_endswith   = StdObjspaceMultiMethod('endswith', 4, defaults=(0,maxint))
unicode_expandtabs = StdObjspaceMultiMethod('expandtabs', 2, defaults=(8,))
unicode_find       = StdObjspaceMultiMethod('find', 4, defaults=(0, maxint))
unicode_index      = StdObjspaceMultiMethod('index', 4, defaults=(0, maxint))
unicode_isalnum    = StdObjspaceMultiMethod('isalnum', 1)
unicode_isalpha    = StdObjspaceMultiMethod('isalpha', 1)
unicode_isdecimal  = StdObjspaceMultiMethod('isdecimal', 1)
unicode_isdigit    = StdObjspaceMultiMethod('isdigit', 1)
unicode_islower    = StdObjspaceMultiMethod('islower', 1)
unicode_isnumeric  = StdObjspaceMultiMethod('isnumeric', 1)
unicode_isspace    = StdObjspaceMultiMethod('isspace', 1)
unicode_istitle    = StdObjspaceMultiMethod('istitle', 1)
unicode_isupper    = StdObjspaceMultiMethod('isupper', 1)
unicode_join       = StdObjspaceMultiMethod('join', 2)
unicode_ljust      = StdObjspaceMultiMethod('ljust', 3, defaults=(' ',))
unicode_lower      = StdObjspaceMultiMethod('lower', 1)
unicode_lstrip     = StdObjspaceMultiMethod('lstrip', 2, defaults=(None,))
unicode_replace    = StdObjspaceMultiMethod('replace', 4, defaults=(-1,))
unicode_rfind      = StdObjspaceMultiMethod('rfind', 4, defaults=(0, maxint))
unicode_rindex     = StdObjspaceMultiMethod('rindex', 4, defaults=(0, maxint))
unicode_rjust      = StdObjspaceMultiMethod('rjust', 3, defaults=(' ',))
unicode_rstrip     = StdObjspaceMultiMethod('rstrip', 2, defaults=(None,))
unicode_rsplit     = StdObjspaceMultiMethod('rsplit', 3, defaults=(None,-1))
unicode_split      = StdObjspaceMultiMethod('split', 3, defaults=(None,-1))
unicode_splitlines = StdObjspaceMultiMethod('splitlines', 2, defaults=(0,))
unicode_startswith = StdObjspaceMultiMethod('startswith', 4, defaults=(0,maxint))
unicode_strip      = StdObjspaceMultiMethod('strip',  2, defaults=(None,))
unicode_swapcase   = StdObjspaceMultiMethod('swapcase', 1)
unicode_title      = StdObjspaceMultiMethod('title', 1)
unicode_translate  = StdObjspaceMultiMethod('translate', 2)
unicode_upper      = StdObjspaceMultiMethod('upper', 1)
unicode_zfill      = StdObjspaceMultiMethod('zfill', 2)

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

def unicode_from_string(space, w_str):
    # this is a performance and bootstrapping hack
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    w_encoding = space.call_function(space.sys.get('getdefaultencoding'))
    if not space.eq_w(w_encoding, space.wrap('ascii')):
        return unicode_from_object(space, w_str)
    s = space.str_w(w_str)
    codelist = []
    for i in range(len(s)):
        code = ord(s[i])
        if code >= 128:
            # raising UnicodeDecodeError is messy, so "please crash for me"
            return unicode_from_object(space, w_str)
        codelist.append(unichr(code))
    return W_UnicodeObject(space, codelist)


def descr__new__(space, w_unicodetype, w_string=None, w_encoding=None, w_errors=None):
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    w_obj = w_string
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
        if space.is_true(space.isinstance(w_obj, space.w_str)):
            w_value = unicode_from_string(space, w_obj)
        elif space.is_true(space.isinstance(w_obj, space.w_unicode)):
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
