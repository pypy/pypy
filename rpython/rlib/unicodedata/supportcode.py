from rpython.rlib.rarithmetic import r_longlong, r_int32, r_uint32, intmask
from rpython.rtyper.lltypesystem.rffi import r_ushort, r_short

# XXX move to rarithmetic?
def signed_ord(c):
    x = ord(c)
    if x > 0x80:
        x -= 0x100
    return x

def _all_uint32(l):
    return [r_uint32(x) for x in l]
def _all_int32(l):
    return [r_int32(x) for x in l]
def _all_ushort(l):
    return [r_ushort(x) for x in l]
def _all_short(l):
    return [r_short(x) for x in l]

_cjk_prefix = "CJK UNIFIED IDEOGRAPH-"
_hangul_prefix = 'HANGUL SYLLABLE '

_hangul_L = ['G', 'GG', 'N', 'D', 'DD', 'R', 'M', 'B', 'BB',
            'S', 'SS', '', 'J', 'JJ', 'C', 'K', 'T', 'P', 'H']
_hangul_V = ['A', 'AE', 'YA', 'YAE', 'EO', 'E', 'YEO', 'YE', 'O', 'WA', 'WAE',
            'OE', 'YO', 'U', 'WEO', 'WE', 'WI', 'YU', 'EU', 'YI', 'I']
_hangul_T = ['', 'G', 'GG', 'GS', 'N', 'NJ', 'NH', 'D', 'L', 'LG', 'LM',
            'LB', 'LS', 'LT', 'LP', 'LH', 'M', 'B', 'BS', 'S', 'SS',
            'NG', 'J', 'C', 'K', 'T', 'P', 'H']

def _lookup_hangul(syllables):
    from rpython.rlib.rstring import startswith
    l_code = v_code = t_code = -1
    for i in range(len(_hangul_L)):
        jamo = _hangul_L[i]
        if (startswith(syllables, jamo) and
            (l_code < 0 or len(jamo) > len(_hangul_L[l_code]))):
            l_code = i
    if l_code < 0:
        raise KeyError
    start = len(_hangul_L[l_code])

    for i in range(len(_hangul_V)):
        jamo = _hangul_V[i]
        if (syllables[start:start + len(jamo)] == jamo and
            (v_code < 0 or len(jamo) > len(_hangul_V[v_code]))):
            v_code = i
    if v_code < 0:
        raise KeyError
    start += len(_hangul_V[v_code])

    for i in range(len(_hangul_T)):
        jamo = _hangul_T[i]
        if (syllables[start:start + len(jamo)] == jamo and
            (t_code < 0 or len(jamo) > len(_hangul_T[t_code]))):
            t_code = i
    if t_code < 0:
        raise KeyError
    start += len(_hangul_T[t_code])

    if len(syllables[start:]):
        raise KeyError
    return 0xAC00 + (l_code * 21 + v_code) * 28 + t_code

