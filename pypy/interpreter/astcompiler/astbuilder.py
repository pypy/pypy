from pypy.interpreter.astcompiler import ast, consts, misc
from pypy.interpreter.astcompiler.ast import build
from pypy.interpreter.astcompiler import asthelpers # Side effects
from pypy.interpreter.astcompiler import fstring
from pypy.interpreter import error
from pypy.interpreter.pyparser.pygram import syms, tokens
from pypy.interpreter.pyparser.error import SyntaxError
from rpython.rlib.objectmodel import always_inline, we_are_translated, specialize


def parse_number(space, raw):
    base = 10
    if raw.startswith("-"):
        negative = True
        raw = raw.lstrip("-")
    else:
        negative = False
    if raw.startswith("0"):
        if len(raw) > 2 and raw[1] in "Xx":
            base = 16
        elif len(raw) > 2 and raw[1] in "Bb":
            base = 2
        ## elif len(raw) > 2 and raw[1] in "Oo": # Fallback below is enough
        ##     base = 8
        elif len(raw) > 1:
            base = 8
        # strip leading characters
        i = 0
        limit = len(raw) - 1
        while i < limit:
            if base == 16 and raw[i] not in "0xX":
                break
            if base == 8 and raw[i] not in "0oO":
                break
            if base == 2 and raw[i] not in "0bB":
                break
            i += 1
        raw = raw[i:]
        if not raw[0].isdigit():
            raw = "0" + raw
    if negative:
        raw = "-" + raw
    w_num_str = space.newtext(raw)
    w_base = space.newint(base)
    if raw[-1] in "jJ":
        tp = space.w_complex
        return space.call_function(tp, w_num_str)
    try:
        return space.call_function(space.w_int, w_num_str, w_base)
    except error.OperationError as e:
        if not e.match(space, space.w_ValueError):
            raise
        return space.call_function(space.w_float, w_num_str)
