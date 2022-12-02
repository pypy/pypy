from pypy.interpreter import error
from rpython.rlib import rutf8, objectmodel

def parse_number(space, raw):
    from pypy.objspace.std.intobject import _string_to_int_or_long
    from pypy.objspace.std.floatobject import _string_to_float
    base = 10
    dot_in_raw = '.' in raw
    if raw.startswith("-"):
        negative = True
        raw = raw.lstrip("-")
    else:
        negative = False
    if not dot_in_raw and raw.startswith("0"):
        # find first non-zero, usually a base specifier
        i = 0
        #string must end with at least one digit after the base
        limit = len(raw) - 1
        # if no base specifier, assume 8 (like CPython)
        base = 8
        while i < limit:
            if raw[i] == "0":
                pass
            elif raw[i] in "Xx":
                base = 16
                i += 1
                if raw[i] == '_':
                    i += 1
                break
            elif raw[i] in "Bb":
                base = 2
                i += 1
                if raw[i] == '_':
                    i += 1
                break
            elif raw[i] in "Ee":
                base = 10
                # leave the leading 0
                i -= 1
                break
            elif raw[i] in "Oo":
                base = 8
                i += 1
                if raw[i] == '_':
                    i += 1
                break
            else:
                # something like 077e0, which is a float
                # or 0_0_0
                base = 10
                if raw[i] == '_':
                    i += 1
                break
            i += 1
        else:
            # for 00j, do not trim the last 0
            i -= 1
        if i > 0:
            raw = raw[i:]
    if negative:
        raw = "-" + raw
    # by construction this should not be able to fail: the tokenizer only
    # recognizes ascii characters as parts of a number
    if not objectmodel.we_are_translated():
        rutf8.check_ascii(raw)
    w_num_str = space.newtext(raw, len(raw))
    # CPython uses the fact that strtol(raw, end) will successfully reach
    # the end of raw if it is a proper int string. We use the next two
    # checks instead
    if raw[-1] in "jJ":
        tp = space.w_complex
        return space.call_function(tp, w_num_str)
    if base == 10 and (dot_in_raw or 'e' in raw or 'E' in raw):
        return space.call_function(space.w_float, w_num_str)
    # OK, not a complex and not a float
    return _string_to_int_or_long(space, w_num_str, raw, base)
