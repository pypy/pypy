from rpython.rlib.rstring import StringBuilder
from rpython.rlib.rutf8 import Utf8StringIterator
from rpython.rlib.rfloat import isfinite, formatd, DTSF_ADD_DOT_0
from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec

HEX = '0123456789abcdef'

ESCAPE_DICT = {
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
ESCAPE_BEFORE_SPACE = [ESCAPE_DICT.get(chr(_i), '\\u%04x' % _i)
                       for _i in range(32)]


def raw_encode_basestring_ascii(space, w_unicode):
    u = space.utf8_w(w_unicode)
    for i in range(len(u)):
        c = ord(u[i])
        if c < 32 or c > 126 or c == ord('\\') or c == ord('"'):
            break
    else:
        # The unicode string 'u' contains only safe characters.
        return w_unicode

    sb = StringBuilder(len(u) + 20)

    for c in Utf8StringIterator(u):
        if c <= ord('~'):
            if c == ord('"') or c == ord('\\'):
                sb.append('\\')
            elif c < ord(' '):
                sb.append(ESCAPE_BEFORE_SPACE[c])
                continue
            sb.append(chr(c))
        else:
            if c <= ord(u'\uffff'):
                sb.append('\\u')
                sb.append(HEX[c >> 12])
                sb.append(HEX[(c >> 8) & 0x0f])
                sb.append(HEX[(c >> 4) & 0x0f])
                sb.append(HEX[c & 0x0f])
            else:
                # surrogate pair
                n = c - 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                sb.append('\\ud')
                sb.append(HEX[(s1 >> 8) & 0x0f])
                sb.append(HEX[(s1 >> 4) & 0x0f])
                sb.append(HEX[s1 & 0x0f])
                s2 = 0xdc00 | (n & 0x3ff)
                sb.append('\\ud')
                sb.append(HEX[(s2 >> 8) & 0x0f])
                sb.append(HEX[(s2 >> 4) & 0x0f])
                sb.append(HEX[s2 & 0x0f])

    res = sb.build()
    return space.newtext(res)


def _append_str_ascii(sb, u):
    """Append a JSON-encoded string (with surrounding quotes) to sb.
    Escapes all non-ASCII and control characters (ensure_ascii=True semantics)."""
    sb.append('"')
    for c in Utf8StringIterator(u):
        if c <= ord('~'):
            if c == ord('"') or c == ord('\\'):
                sb.append('\\')
            elif c < ord(' '):
                sb.append(ESCAPE_BEFORE_SPACE[c])
                continue
            sb.append(chr(c))
        else:
            if c <= ord(u'\uffff'):
                sb.append('\\u')
                sb.append(HEX[c >> 12])
                sb.append(HEX[(c >> 8) & 0x0f])
                sb.append(HEX[(c >> 4) & 0x0f])
                sb.append(HEX[c & 0x0f])
            else:
                # surrogate pair
                n = c - 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                sb.append('\\ud')
                sb.append(HEX[(s1 >> 8) & 0x0f])
                sb.append(HEX[(s1 >> 4) & 0x0f])
                sb.append(HEX[s1 & 0x0f])
                s2 = 0xdc00 | (n & 0x3ff)
                sb.append('\\ud')
                sb.append(HEX[(s2 >> 8) & 0x0f])
                sb.append(HEX[(s2 >> 4) & 0x0f])
                sb.append(HEX[s2 & 0x0f])
    sb.append('"')


class W_Encoder(W_Root):
    """RPython JSON encoder returned by make_encoder().

    Encodes a Python object tree into a single JSON string, building the
    result in a StringBuilder.  Only handles the compact (indent=None) case
    that encoder.py gates on before calling c_make_encoder.

    String encoding always uses ASCII-safe escaping (ensure_ascii=True
    semantics), which is correct for the default JSONEncoder and produces
    valid (over-escaped) output for ensure_ascii=False.
    """

    def __init__(self, space, w_markers, w_default,
                 key_separator, item_separator, sort_keys, skipkeys, allow_nan):
        self.space = space
        self.w_markers = w_markers   # space.w_None, or a dict for circular-ref checking
        self.w_default = w_default   # callable for unknown objects
        self.key_separator = key_separator
        self.item_separator = item_separator
        self.sort_keys = sort_keys
        self.skipkeys = skipkeys
        self.allow_nan = allow_nan

    @unwrap_spec(indent_level=int)
    def descr_call(self, space, w_obj, indent_level=0):
        sb = StringBuilder()
        self._encode(sb, w_obj)
        return space.newlist([space.newtext(sb.build())])

    def _encode_float(self, sb, f):
        if not isfinite(f):
            if f > 0.0:
                text = 'Infinity'
            elif f < 0.0:
                text = '-Infinity'
            else:
                text = 'NaN'
            if not self.allow_nan:
                raise oefmt(self.space.w_ValueError,
                    "Out of range float values are not JSON compliant: %s", text)
            sb.append(text)
        else:
            sb.append(formatd(f, 'r', 0, DTSF_ADD_DOT_0))

    def _encode(self, sb, w_obj):
        space = self.space
        if space.is_w(w_obj, space.w_None):
            sb.append('null')
        elif space.is_w(w_obj, space.w_True):
            sb.append('true')
        elif space.is_w(w_obj, space.w_False):
            sb.append('false')
        elif space.isinstance_w(w_obj, space.w_unicode):
            _append_str_ascii(sb, space.utf8_w(w_obj))
        elif space.isinstance_w(w_obj, space.w_int):
            # bool is a subclass of int but already handled above via is_w checks
            sb.append(space.text_w(space.str(w_obj)))
        elif space.isinstance_w(w_obj, space.w_float):
            self._encode_float(sb, space.float_w(w_obj))
        elif space.isinstance_w(w_obj, space.w_list) or \
                space.isinstance_w(w_obj, space.w_tuple):
            self._encode_list(sb, w_obj)
        elif space.isinstance_w(w_obj, space.w_dict):
            self._encode_dict(sb, w_obj)
        else:
            self._encode_default(sb, w_obj)

    def _encode_default(self, sb, w_obj):
        space = self.space
        w_markers = self.w_markers
        w_id = space.w_None
        check_circular = not space.is_none(w_markers)
        if check_circular:
            w_id = space.id(w_obj)
            if space.contains_w(w_markers, w_id):
                raise oefmt(space.w_ValueError, "Circular reference detected")
            space.setitem(w_markers, w_id, w_obj)
        w_result = space.call_function(self.w_default, w_obj)
        self._encode(sb, w_result)
        if check_circular:
            space.delitem(w_markers, w_id)

    def _encode_list(self, sb, w_list):
        space = self.space
        w_markers = self.w_markers
        w_id = space.w_None
        check_circular = not space.is_none(w_markers)
        if check_circular:
            w_id = space.id(w_list)
            if space.contains_w(w_markers, w_id):
                raise oefmt(space.w_ValueError, "Circular reference detected")
            space.setitem(w_markers, w_id, w_list)
        items_w = space.unpackiterable(w_list)
        sb.append('[')
        first = True
        for w_item in items_w:
            if first:
                first = False
            else:
                sb.append(self.item_separator)
            self._encode(sb, w_item)
        sb.append(']')
        if check_circular:
            space.delitem(w_markers, w_id)

    def _coerce_dict_key(self, w_key):
        """Return (w_str_key, skip) where skip=True means omit this entry."""
        space = self.space
        if space.isinstance_w(w_key, space.w_unicode):
            return w_key, False
        elif space.is_w(w_key, space.w_True):
            return space.newtext('true'), False
        elif space.is_w(w_key, space.w_False):
            return space.newtext('false'), False
        elif space.is_w(w_key, space.w_None):
            return space.newtext('null'), False
        elif space.isinstance_w(w_key, space.w_int):
            return space.str(w_key), False
        elif space.isinstance_w(w_key, space.w_float):
            float_sb = StringBuilder()
            self._encode_float(float_sb, space.float_w(w_key))
            return space.newtext(float_sb.build()), False
        elif self.skipkeys:
            return space.w_None, True
        else:
            raise oefmt(space.w_TypeError,
                'keys must be str, int, float, bool or None, not %T', w_key)

    def _encode_dict(self, sb, w_dict):
        space = self.space
        w_markers = self.w_markers
        w_id = space.w_None
        check_circular = not space.is_none(w_markers)
        if check_circular:
            w_id = space.id(w_dict)
            if space.contains_w(w_markers, w_id):
                raise oefmt(space.w_ValueError, "Circular reference detected")
            space.setitem(w_markers, w_id, w_dict)
        keys_w = space.unpackiterable(w_dict)
        if self.sort_keys:
            # Collect string sort keys in parallel; non-str keys sort first ('')
            str_keys = []
            wkey_list = []
            for w_key in keys_w:
                if space.isinstance_w(w_key, space.w_unicode):
                    str_keys.append(space.utf8_w(w_key))
                else:
                    str_keys.append('')
                wkey_list.append(w_key)
            # insertion sort by str_keys, keeping wkey_list in sync
            n = len(str_keys)
            for i in range(1, n):
                sk = str_keys[i]
                wk = wkey_list[i]
                j = i
                while j > 0 and str_keys[j - 1] > sk:
                    str_keys[j] = str_keys[j - 1]
                    wkey_list[j] = wkey_list[j - 1]
                    j -= 1
                str_keys[j] = sk
                wkey_list[j] = wk
            keys_w = wkey_list
        sb.append('{')
        first = True
        for w_key in keys_w:
            w_key_str, skip = self._coerce_dict_key(w_key)
            if skip:
                continue
            w_val = space.getitem(w_dict, w_key)
            if first:
                first = False
            else:
                sb.append(self.item_separator)
            _append_str_ascii(sb, space.utf8_w(w_key_str))
            sb.append(self.key_separator)
            self._encode(sb, w_val)
        sb.append('}')
        if check_circular:
            space.delitem(w_markers, w_id)


W_Encoder.typedef = TypeDef(
    '_pypyjson.Encoder',
    __call__=interp2app(W_Encoder.descr_call),
)
W_Encoder.typedef.acceptable_as_base_class = False


@unwrap_spec(key_separator='text', item_separator='text',
             sort_keys=bool, skipkeys=bool, allow_nan=bool)
def make_encoder(space, w_markers, w_default, w_str_encoder, w_indent,
                 key_separator, item_separator, sort_keys, skipkeys, allow_nan):
    """Return an encoder callable for use as json.encoder.c_make_encoder.

    w_str_encoder is accepted for API compatibility but not used — string
    encoding is done inline with ASCII-safe escaping.
    """
    return W_Encoder(space, w_markers, w_default,
                     key_separator, item_separator, sort_keys, skipkeys, allow_nan)
