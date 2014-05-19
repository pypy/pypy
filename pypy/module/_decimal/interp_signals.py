from collections import OrderedDict
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import rmpdec, rstring
from rpython.rlib.unroll import unrolling_iterable
from pypy.interpreter.error import oefmt, OperationError

SIGNAL_MAP = unrolling_iterable([
    ('InvalidOperation', rmpdec.MPD_IEEE_Invalid_operation),
    ('FloatOperation', rmpdec.MPD_Float_operation),
    ('DivisionByZero', rmpdec.MPD_Division_by_zero),
    ('Overflow', rmpdec.MPD_Overflow),
    ('Underflow', rmpdec.MPD_Underflow),
    ('Subnormal', rmpdec.MPD_Subnormal),
    ('Inexact', rmpdec.MPD_Inexact),
    ('Rounded', rmpdec.MPD_Rounded),
    ('Clamped', rmpdec.MPD_Clamped),
    ])
# Exceptions that inherit from InvalidOperation
COND_MAP = unrolling_iterable([
    ('InvalidOperation', rmpdec.MPD_Invalid_operation),
    ('ConversionSyntax', rmpdec.MPD_Conversion_syntax),
    ('DivisionImpossible', rmpdec.MPD_Division_impossible),
    ('DivisionUndefined', rmpdec.MPD_Division_undefined),
    ('InvalidContext', rmpdec.MPD_Invalid_context),
    ])

SIGNAL_STRINGS = OrderedDict([
    (rmpdec.MPD_Clamped, "Clamped"),
    (rmpdec.MPD_IEEE_Invalid_operation, "InvalidOperation"),
    (rmpdec.MPD_Division_by_zero, "DivisionByZero"),
    (rmpdec.MPD_Inexact, "Inexact"),
    (rmpdec.MPD_Float_operation, "FloatOperation"),
    (rmpdec.MPD_Overflow, "Overflow"),
    (rmpdec.MPD_Rounded, "Rounded"),
    (rmpdec.MPD_Subnormal, "Subnormal"),
    (rmpdec.MPD_Underflow, "Underflow"),
    ])

def flags_as_exception(space, flags):
    w_exc = None
    err_list = []
    for name, flag in SIGNAL_MAP:
        if flags & flag:
            w_exc = getattr(get(space), 'w_' + name)
    if w_exc is None:
        raise oefmt(space.w_RuntimeError,
                    "invalid error flag")
    return OperationError(w_exc, space.w_None)

def exception_as_flag(space, w_exc):
    for name, flag in SIGNAL_MAP:
        if space.is_w(w_exc, getattr(get(space), 'w_' + name)):
            return flag
    raise oefmt(space.w_KeyError,
                "invalid error flag")

def flags_as_string(flags):
    builder = rstring.StringBuilder(30)
    builder.append('[')
    first = True
    flags = rffi.cast(lltype.Signed, flags)
    for (flag, value) in SIGNAL_STRINGS.items():
        if flag & flags:
            if not first:
                builder.append(', ')
                first = False
            builder.append(value)
    builder.append(']')
    return builder.build()


class SignalState:
    def __init__(self, space):
        self.w_DecimalException = space.call_function(
            space.w_type, space.wrap("DecimalException"),
            space.newtuple([space.w_ArithmeticError]),
            space.newdict())
        self.w_Clamped = space.call_function(
            space.w_type, space.wrap("Clamped"),
            space.newtuple([self.w_DecimalException]),
            space.newdict())
        self.w_Rounded = space.call_function(
            space.w_type, space.wrap("Rounded"),
            space.newtuple([self.w_DecimalException]),
            space.newdict())
        self.w_Inexact = space.call_function(
            space.w_type, space.wrap("Inexact"),
            space.newtuple([self.w_DecimalException]),
            space.newdict())
        self.w_Subnormal = space.call_function(
            space.w_type, space.wrap("Subnormal"),
            space.newtuple([self.w_DecimalException]),
            space.newdict())
        self.w_Underflow = space.call_function(
            space.w_type, space.wrap("Underflow"),
            space.newtuple([self.w_Inexact,
                            self.w_Rounded,
                            self.w_Subnormal]),
            space.newdict())
        self.w_Overflow = space.call_function(
            space.w_type, space.wrap("Overflow"),
            space.newtuple([self.w_Inexact,
                            self.w_Rounded]),
            space.newdict())
        self.w_DivisionByZero = space.call_function(
            space.w_type, space.wrap("DivisionByZero"),
            space.newtuple([self.w_DecimalException,
                            space.w_ZeroDivisionError]),
            space.newdict())
        self.w_InvalidOperation = space.call_function(
            space.w_type, space.wrap("InvalidOperation"),
            space.newtuple([self.w_DecimalException]),
            space.newdict())
        self.w_FloatOperation = space.call_function(
            space.w_type, space.wrap("FloatOperation"),
            space.newtuple([self.w_DecimalException,
                            space.w_TypeError]),
            space.newdict())

        self.w_SignalTuple = space.newtuple([
                getattr(self, 'w_' + name)
                for name, flag in SIGNAL_MAP])

def get(space):
    return space.fromcache(SignalState)
