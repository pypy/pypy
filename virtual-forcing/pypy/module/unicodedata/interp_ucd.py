"""
Implementation of the interpreter-level functions in the module unicodedata.
"""
from pypy.interpreter.gateway import W_Root, ObjSpace, NoneNotWrapped
from pypy.interpreter.gateway import  interp2app
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, interp_attrproperty

from pypy.module.unicodedata import unicodedb_5_0_0, unicodedb_4_1_0, unicodedb_3_2_0

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

def unichr_to_code_w(space, w_unichr):
    if not space.is_true(space.isinstance(w_unichr, space.w_unicode)):
        raise OperationError(space.w_TypeError, space.wrap('argument 1 must be unicode'))
    if not space.int_w(space.len(w_unichr)) == 1:
        raise OperationError(space.w_TypeError, space.wrap('need a single Unicode character as parameter'))
    return space.int_w(space.ord(w_unichr))

class UCD(Wrappable):
    def __init__(self, unicodedb):
        self._lookup = unicodedb.lookup
        self._name = unicodedb.name
        self._decimal = unicodedb.decimal
        self._digit = unicodedb.digit
        self._numeric = unicodedb.numeric
        self._category = unicodedb.category
        self._east_asian_width = unicodedb.east_asian_width
        self._bidirectional = unicodedb.bidirectional
        self._combining = unicodedb.combining
        self._mirrored = unicodedb.mirrored
        self._decomposition = unicodedb.decomposition
        self._canon_decomposition = unicodedb.canon_decomposition
        self._compat_decomposition = unicodedb.compat_decomposition
        self._composition_max = unicodedb._composition_max
        self._composition_shift = unicodedb._composition_shift
        self._composition = unicodedb._composition
        
        self.version = unicodedb.version
        
    def _get_code(self, space, name):
        try:
            code = self._lookup(name.upper())
        except KeyError:
            msg = space.mod(space.wrap("undefined character name '%s'"), space.wrap(name))
            raise OperationError(space.w_KeyError, msg)
        return space.wrap(code)
    _get_code.unwrap_spec = ['self', ObjSpace, str]
    
    def lookup(self, space, name):
        w_code = self._get_code(space, name)
        try:
            return space.call_function(space.builtin.get('unichr'), w_code)
        except OperationError, ex:
            if not ex.match(space, space.w_ValueError):
                raise
            msg = space.mod(space.wrap("result %d larger than sys.maxunicode"), w_code)
            raise OperationError(space.w_KeyError, msg)

    lookup.unwrap_spec = ['self', ObjSpace, str]

    def name(self, space, w_unichr, w_default=NoneNotWrapped):
        code = unichr_to_code_w(space, w_unichr)
        try:
            name = self._name(code)
        except KeyError:
            if w_default is not None:
                return w_default
            raise OperationError(space.w_ValueError, space.wrap('no such name'))
        return space.wrap(name)
    name.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]


    def decimal(self, space, w_unichr, w_default=NoneNotWrapped):
        code = unichr_to_code_w(space, w_unichr)
        try:
            return space.wrap(self._decimal(code))
        except KeyError:
            pass
        if w_default is not None:
            return w_default
        raise OperationError(space.w_ValueError, space.wrap('not a decimal'))
    decimal.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def digit(self, space, w_unichr, w_default=NoneNotWrapped):
        code = unichr_to_code_w(space, w_unichr)
        try:
            return space.wrap(self._digit(code))
        except KeyError:
            pass
        if w_default is not None:
            return w_default
        raise OperationError(space.w_ValueError, space.wrap('not a digit'))
    digit.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def numeric(self, space, w_unichr, w_default=NoneNotWrapped):
        code = unichr_to_code_w(space, w_unichr)
        try:
            return space.wrap(self._numeric(code))
        except KeyError:
            pass
        if w_default is not None:
            return w_default
        raise OperationError(space.w_ValueError,
                             space.wrap('not a numeric character'))
    numeric.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def category(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._category(code))
    category.unwrap_spec = ['self', ObjSpace, W_Root]

    def east_asian_width(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._east_asian_width(code))
    east_asian_width.unwrap_spec = ['self', ObjSpace, W_Root]

    def bidirectional(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._bidirectional(code))
    bidirectional.unwrap_spec = ['self', ObjSpace, W_Root]

    def combining(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._combining(code))
    combining.unwrap_spec = ['self', ObjSpace, W_Root]

    def mirrored(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._mirrored(code))
    mirrored.unwrap_spec = ['self', ObjSpace, W_Root]

    def decomposition(self, space, w_unichr):
        code = unichr_to_code_w(space, w_unichr)
        return space.wrap(self._decomposition(code))
    decomposition.unwrap_spec = ['self', ObjSpace, W_Root]

    def normalize(self, space, form, w_unistr):
        if not space.is_true(space.isinstance(w_unistr, space.w_unicode)):
            raise OperationError(space.w_TypeError, space.wrap('argument 2 must be unicode'))
        if form == 'NFC':
            composed = True
            decomposition = self._canon_decomposition
        elif form == 'NFD':
            composed = False
            decomposition = self._canon_decomposition
        elif form == 'NFKC': 
            composed = True
            decomposition = self._compat_decomposition
        elif form == 'NFKD':
            composed = False
            decomposition = self._compat_decomposition
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
            decomp = decomposition(ch)
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
            comb = self._combining(ch)
            if comb == 0:
                continue
            for k in range(i, 0, -1):
                if self._combining(result[k - 1]) <= comb:
                    result[k] = ch
                    break

                result[k] = result[k - 1]
            else:
                result[0] = ch

        if not composed: # If decomposed normalization we are done
            return space.wrap(u''.join([unichr(i) for i in result[:j]]))

        if j <= 1:
            return space.wrap(u''.join([unichr(i) for i in result[:j]]))

        current = result[0]
        starter_pos = 0
        next_insert = 1
        prev_combining = 0
        if self._combining(current):
            prev_combining = 256
        for k in range(1, j):
            next = result[k]
            next_combining = self._combining(next)
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
                if (current <= self._composition_max and
                       next <= self._composition_max):
                    key = current << self._composition_shift | next
                    try:
                        current = self._composition[key]
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

        return space.wrap(u''.join([unichr(i) for i in result[:next_insert]]))
    normalize.unwrap_spec = ['self', ObjSpace, str, W_Root]
    

methods = {}
for methodname in UCD.__dict__:
    method = getattr(UCD, methodname)
    if not hasattr(method,'unwrap_spec'):
        continue
    assert method.im_func.func_code.co_argcount == len(method.unwrap_spec), methodname
    methods[methodname] = interp2app(method, unwrap_spec=method.unwrap_spec)
    

UCD.typedef = TypeDef("unicodedata.UCD",
                      __doc__ = "",
                      unidata_version = interp_attrproperty('version', UCD),
                      **methods)

ucd_3_2_0 = UCD(unicodedb_3_2_0)
ucd_4_1_0 = UCD(unicodedb_4_1_0)
ucd_5_0_0 = UCD(unicodedb_5_0_0)
ucd = ucd_4_1_0

