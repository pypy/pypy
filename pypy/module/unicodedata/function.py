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

def east_asian_width(space, w_unichr):
    code = unichr_to_code_w(space, w_unichr)
    return space.wrap(unicodedb.east_asian_width(code))

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
    return space.wrap(unicodedb.decomposition(code))


# Contants for Hangul characters
SBase = 0xAC00
LBase = 0x1100
VBase = 0x1161
TBase = 0x11A7
LCount = 19
VCount = 21
TCount = 28
NCount = (VCount*TCount)
SCount = (LCount*NCount)


def normalize(space, w_form, w_unistr):
    form = space.str_w(w_form)
    if not space.is_true(space.isinstance(w_unistr, space.w_unicode)):
        raise TypeError, 'argument 2 must be unicode'
    if form == 'NFC':
        composed = True
        decomposition = unicodedb._canon_decomposition
    elif form == 'NFD':
        composed = False
        decomposition = unicodedb._canon_decomposition
    elif form == 'NFKC': 
        composed = True
        decomposition = unicodedb._compat_decomposition
    elif form == 'NFKD':
        composed = False
        decomposition = unicodedb._compat_decomposition
    else:
        raise OperationError(space.w_ValueError,
                             space.wrap('invalid normalization form'))

    strlen = space.int_w(space.len(w_unistr))
    result = [0] * (strlen + strlen / 10 + 10)
    j = 0
    resultlen = len(result)
    # Expand the character
    for i in range(strlen):
        ch = space.int_w(space.ord(space.getitem(w_unistr, space.wrap(i))))
        # Do Hangul decomposition
        if SBase <= ch < SBase + SCount:
            SIndex = ch - SBase;
            L = LBase + SIndex / NCount;
            V = VBase + (SIndex % NCount) / TCount;
            T = TBase + SIndex % TCount;
            if T == TBase:
                if j + 2 > resultlen:
                    result.extend([0] * (j + 2 - resultlen + 10))
                    resultlen = len(result)
                result[j] = L
                result[j + 1] = V
                j += 2
            else:
                if j + 3 > resultlen:
                    result.extend([0] * (j + 3 - resultlen + 10))
                    resultlen = len(result)
                result[j] = L
                result[j + 1] = V
                result[j + 2] = T
                j += 3
            continue
        decomp = decomposition.get(ch, [])
        if decomp:
            decomplen = len(decomp)
            if j + decomplen > resultlen:
                result.extend([0] * (j + decomplen - resultlen + 10))
                resultlen = len(result)
            for ch in decomp:
                result[j] = ch
                j += 1
        else:
            if j + 1 > resultlen:
                result.extend([0] * (j + 1 - resultlen + 10))
                resultlen = len(result)
            result[j] = ch
            j += 1

    # Sort all combining marks
    for i in range(j):
        ch = result[i]
        comb = unicodedb.combining(ch)
        if comb == 0:
            continue
        for k in range(i, 0, -1):
            if unicodedb.combining(result[k - 1]) <= comb:
                result[k] = ch
                break
            
            result[k] = result[k - 1]
        else:
            result[0] = ch

    if not composed: # If decomposed normalization we are done
        return space.newunicode(result[:j])

    if j <= 1:
        return space.newunicode(result[:j])

    current = result[0]
    starter_pos = 0
    next_insert = 1
    prev_combining = 0
    if unicodedb.combining(current):
        prev_combining = 256
    for k in range(1, j):
        next = result[k]
        next_combining = unicodedb.combining(next)
        if next_insert == starter_pos + 1 or prev_combining < next_combining:
            # Combine if not blocked
            if (LBase <= current < LBase + LCount and
                VBase <= next < VBase + VCount):
                # If L, V -> LV
                current = SBase + ((current - LBase)*VCount + (next - VBase)) * TCount
                continue
            if (SBase <= current < SBase + SCount and
                TBase <= next < TBase + TCount and
                (current - SBase) % TCount == 0):
                # If LV, T -> LVT
                current = current + (next - TBase)
                continue
            try:
                current = unicodedb._composition[(current, next)]
                continue
            except KeyError:
                pass

        if next_combining == 0:
            # New starter symbol
            result[starter_pos] = current
            starter_pos = next_insert
            next_insert += 1
            prev_combining = 0
            current = next
            continue

        
        result[next_insert] = next
        next_insert += 1
        if next_combining > prev_combining:
            prev_combining = next_combining
        
    result[starter_pos] = current
    
    return space.newunicode(result[:next_insert])
    
