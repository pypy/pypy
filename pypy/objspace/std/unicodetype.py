from pypy.interpreter import gateway
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.interpreter.error import OperationError

from sys import maxint

unicode_capitalize = StdObjSpaceMultiMethod('capitalize', 1)
unicode_center     = StdObjSpaceMultiMethod('center', 3, defaults=(' ',))
unicode_count      = StdObjSpaceMultiMethod('count', 4, defaults=(0, maxint))      
unicode_encode     = StdObjSpaceMultiMethod('encode', 3, defaults=(None, None))
unicode_endswith   = StdObjSpaceMultiMethod('endswith', 4, defaults=(0,maxint))
unicode_expandtabs = StdObjSpaceMultiMethod('expandtabs', 2, defaults=(8,))
unicode_find       = StdObjSpaceMultiMethod('find', 4, defaults=(0, maxint))
unicode_index      = StdObjSpaceMultiMethod('index', 4, defaults=(0, maxint))
unicode_isalnum    = StdObjSpaceMultiMethod('isalnum', 1)
unicode_isalpha    = StdObjSpaceMultiMethod('isalpha', 1)
unicode_isdecimal  = StdObjSpaceMultiMethod('isdecimal', 1)
unicode_isdigit    = StdObjSpaceMultiMethod('isdigit', 1)
unicode_islower    = StdObjSpaceMultiMethod('islower', 1)
unicode_isnumeric  = StdObjSpaceMultiMethod('isnumeric', 1)
unicode_isspace    = StdObjSpaceMultiMethod('isspace', 1)
unicode_istitle    = StdObjSpaceMultiMethod('istitle', 1)
unicode_isupper    = StdObjSpaceMultiMethod('isupper', 1)
unicode_join       = StdObjSpaceMultiMethod('join', 2)
unicode_ljust      = StdObjSpaceMultiMethod('ljust', 3, defaults=(' ',))
unicode_lower      = StdObjSpaceMultiMethod('lower', 1)
unicode_lstrip     = StdObjSpaceMultiMethod('lstrip', 2, defaults=(None,))
unicode_replace    = StdObjSpaceMultiMethod('replace', 4, defaults=(-1,))
unicode_rfind      = StdObjSpaceMultiMethod('rfind', 4, defaults=(0, maxint))
unicode_rindex     = StdObjSpaceMultiMethod('rindex', 4, defaults=(0, maxint))
unicode_rjust      = StdObjSpaceMultiMethod('rjust', 3, defaults=(' ',))
unicode_rstrip     = StdObjSpaceMultiMethod('rstrip', 2, defaults=(None,))
unicode_rsplit     = StdObjSpaceMultiMethod('rsplit', 3, defaults=(None,-1))
unicode_split      = StdObjSpaceMultiMethod('split', 3, defaults=(None,-1))
unicode_splitlines = StdObjSpaceMultiMethod('splitlines', 2, defaults=(0,))
unicode_startswith = StdObjSpaceMultiMethod('startswith', 4, defaults=(0,maxint))
unicode_strip      = StdObjSpaceMultiMethod('strip',  2, defaults=(None,))
unicode_swapcase   = StdObjSpaceMultiMethod('swapcase', 1)
unicode_title      = StdObjSpaceMultiMethod('title', 1)
unicode_translate  = StdObjSpaceMultiMethod('translate', 2)
unicode_upper      = StdObjSpaceMultiMethod('upper', 1)
unicode_zfill      = StdObjSpaceMultiMethod('zfill', 2)

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
    return W_UnicodeObject(codelist)


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
        w_value = W_UnicodeObject([])
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
    W_UnicodeObject.__init__(w_newobj, w_value._value)
    return w_newobj

# ____________________________________________________________

unicode_typedef = StdTypeDef("unicode", basestring_typedef,
    __new__ = newmethod(descr__new__),
    __doc__ = '''unicode(string [, encoding[, errors]]) -> object

Create a new Unicode object from the given encoded string.
encoding defaults to the current default string encoding.
errors can be 'strict', 'replace' or 'ignore' and defaults to 'strict'.'''
    )

unicode_typedef.custom_hash = True
unicode_typedef.registermethods(globals())
