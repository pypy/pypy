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

def get(space):
    return space.fromcache(SignalState)
