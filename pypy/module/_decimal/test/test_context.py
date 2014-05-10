class AppTestContext:
    spaceconfig = dict(usemodules=('_decimal',))

    def setup_class(cls):
        space = cls.space
        cls.w_decimal = space.call_function(space.builtin.get('__import__'),
                                            space.wrap("_decimal"))
        cls.w_Decimal = space.getattr(cls.w_decimal, space.wrap("Decimal"))

    def test_context_repr(self):
        c = self.decimal.DefaultContext.copy()

        c.prec = 425000000
        c.Emax = 425000000
        c.Emin = -425000000
        c.rounding = self.decimal.ROUND_HALF_DOWN
        c.capitals = 0
        c.clamp = 1

        d = self.decimal
        OrderedSignals = [d.Clamped, d.Rounded, d.Inexact, d.Subnormal,
                          d.Underflow, d.Overflow, d.DivisionByZero,
                          d.InvalidOperation, d.FloatOperation]
        for sig in OrderedSignals:
            c.flags[sig] = False
            c.traps[sig] = False

        s = c.__repr__()
        t = "Context(prec=425000000, rounding=ROUND_HALF_DOWN, " \
            "Emin=-425000000, Emax=425000000, capitals=0, clamp=1, " \
            "flags=[], traps=[])"
        assert s == t

