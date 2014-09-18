class AppTestDecimalModule:
    spaceconfig = dict(usemodules=('_decimal',))

    def test_constants(self):
        import _decimal
        assert _decimal.IEEE_CONTEXT_MAX_BITS > 3

    def test_type(self):
        import _decimal
        assert isinstance(_decimal.Decimal, type)

    def test_versions(self):
        import _decimal
        assert isinstance(_decimal.__version__, str)
        assert isinstance(_decimal.__libmpdec_version__, str)

    def test_context(self):
        import _decimal
        context = _decimal.Context(
            prec=9, rounding=_decimal.ROUND_HALF_EVEN,
            traps=dict.fromkeys(_decimal.getcontext().flags.keys(), 0))
        _decimal.setcontext(context)
        assert _decimal.getcontext() is context

    def test_contextflags(self):
        import _decimal
        from collections.abc import MutableMapping
        flags = _decimal.getcontext().flags
        assert type(flags).__name__ == 'SignalDict'
        bases = type(flags).__bases__
        assert bases[1] is MutableMapping

        assert _decimal.Inexact in flags
        assert _decimal.Inexact in flags.keys()

    def test_context_changes(self):
        import _decimal
        context = _decimal.getcontext()
        context.prec
        context.prec = 30
        context.rounding
        context.rounding = _decimal.ROUND_HALF_UP
        context.Emin
        context.Emin = -100
        context.Emax
        context.Emax = 100
        context.clamp
        context.clamp = 1

    def test_exceptions(self):
        import _decimal
        for name in ('Clamped', 'Rounded', 'Inexact', 'Subnormal',
                     'Underflow', 'Overflow', 'DivisionByZero',
                     'InvalidOperation', 'FloatOperation'):
            ex = getattr(_decimal, name)
            assert issubclass(ex, _decimal.DecimalException)
            assert issubclass(ex, ArithmeticError)
            assert ex.__module__ == 'decimal'

    def test_exception_hierarchy(self):
        import _decimal as decimal
        DecimalException = decimal.DecimalException
        InvalidOperation = decimal.InvalidOperation
        FloatOperation = decimal.FloatOperation
        DivisionByZero = decimal.DivisionByZero
        Overflow = decimal.Overflow
        Underflow = decimal.Underflow
        Subnormal = decimal.Subnormal
        Inexact = decimal.Inexact
        Rounded = decimal.Rounded
        Clamped = decimal.Clamped

        assert issubclass(DecimalException, ArithmeticError)

        assert issubclass(InvalidOperation, DecimalException)
        assert issubclass(FloatOperation, DecimalException)
        assert issubclass(FloatOperation, TypeError)
        assert issubclass(DivisionByZero, DecimalException)
        assert issubclass(DivisionByZero, ZeroDivisionError)
        assert issubclass(Overflow, Rounded)
        assert issubclass(Overflow, Inexact)
        assert issubclass(Overflow, DecimalException)
        assert issubclass(Underflow, Inexact)
        assert issubclass(Underflow, Rounded)
        assert issubclass(Underflow, Subnormal)
        assert issubclass(Underflow, DecimalException)

        assert issubclass(Subnormal, DecimalException)
        assert issubclass(Inexact, DecimalException)
        assert issubclass(Rounded, DecimalException)
        assert issubclass(Clamped, DecimalException)

        assert issubclass(decimal.ConversionSyntax, InvalidOperation)
        assert issubclass(decimal.DivisionImpossible, InvalidOperation)
        assert issubclass(decimal.DivisionUndefined, InvalidOperation)
        assert issubclass(decimal.DivisionUndefined, ZeroDivisionError)
        assert issubclass(decimal.InvalidContext, InvalidOperation)

    def test_threads(self):
        import _decimal
        assert (_decimal.HAVE_THREADS is False or
                _decimal.HAVE_THREADS is True)
