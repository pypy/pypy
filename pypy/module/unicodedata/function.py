"""
Implementation of the interpreter-level functions in the module unicodedata.
"""
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.module.unicodedata import unicodedb
from pypy.interpreter.error import OperationError

def unichr_to_code_w(space, w_unichr):
    if not space.is_true(space.isinstance(w_unichr, space.w_unicode)):
        raise OperationError(space.w_TypeError, space.wrap('argument 1 must be unicode'))
    if not space.int_w(space.len(w_unichr)) == 1:
        raise OperationError(space.w_TypeError, space.wrap('need a single Unicode character as parameter'))
    return space.int_w(space.ord(w_unichr))

def lookup(space, w_name):
    name = space.str_w(w_name)
    try:
        code = unicodedb.lookup(name)
    except KeyError:
        msg = space.mod(space.wrap("undefined character name '%s'"), w_name)
        raise OperationError(space.w_KeyError, msg)
    return space.call_function(space.builtin.get('unichr'),
                               space.wrap(code))

def name(space, w_unichr, w_default=NoneNotWrapped):
    code = unichr_to_code_w(space, w_unichr)
    try:
        name = unicodedb.name(code)
    except KeyError:
        if w_default is not None:
            return w_default
        raise OperationError(space.w_ValueError, space.wrap('no such name'))
    return space.wrap(name)


def decimal(space, w_unichr, w_default=NoneNotWrapped):
    code = unichr_to_code_w(space, w_unichr)
    try:
        return space.wrap(unicodedb.decimal(code))
    except KeyError:
        pass
    if w_default is not None:
        return w_default
    raise OperationError(space.w_ValueError, space.wrap('not a decimal'))

def digit(space, w_unichr, w_default=NoneNotWrapped):
    code = unichr_to_code_w(space, w_unichr)
    try:
        return space.wrap(unicodedb.digit(code))
    except KeyError:
        pass
    if w_default is not None:
        return w_default
    raise OperationError(space.w_ValueError, space.wrap('not a digit'))

def numeric(space, w_unichr, w_default=NoneNotWrapped):
    code = unichr_to_code_w(space, w_unichr)
    try:
        return space.wrap(unicodedb.numeric(code))
    except KeyError:
        pass
    if w_default is not None:
        return w_default
    raise OperationError(space.w_ValueError,
                         space.wrap('not a numeric character'))

def category(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap(unicodedb.category(code))

def bidirectional(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap(unicodedb.bidirectional(code))

def combining(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap(unicodedb.combining(code))

def mirrored(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap(unicodedb.mirrored(code))

def decomposition(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    raise OperationError(space.w_NotImplementedError,
                         space.wrap('Decomposition is not implemented'))

def normalize(space, w_form, w_unistr):
    form = space.str_w(w_form)
    if not space.is_true(space.isinstance(w_unistr, space.w_unicode)):
        raise TypeError, 'argument 2 must be unicode'
    if form == 'NFC':
        raise OperationError(space.w_NotImplementedError,
                             space.wrap('Normalization is not implemented'))
    if form == 'NFD':
        raise OperationError(space.w_NotImplementedError,
                             space.wrap('Normalization is not implemented'))
    if form == 'NFKC':
        raise OperationError(space.w_NotImplementedError,
                             space.wrap('Normalization is not implemented'))
    if form == 'NFKD':
        raise OperationError(space.w_NotImplementedError,
                             space.wrap('Normalization is not implemented'))
    raise OperationError(space.w_ValueError,
                         space.wrap('invalid normalization form'))
