"""Additional tests for datetime."""

from __future__ import absolute_import
import py


class BaseTestDatetime:
    def test_repr(self):
        checks = (
            (datetime.date(2015, 6, 8), "datetime.date(2015, 6, 8)"),
            (datetime.datetime(2015, 6, 8, 12, 34, 56), "datetime.datetime(2015, 6, 8, 12, 34, 56)"),
            (datetime.time(12, 34, 56), "datetime.time(12, 34, 56)"),
            (datetime.timedelta(1), "datetime.timedelta(1)"),
            (datetime.timedelta(1, 2), "datetime.timedelta(1, 2)"),
            (datetime.timedelta(1, 2, 3), "datetime.timedelta(1, 2, 3)"),
        )
        for obj, expected in checks:
            assert repr(obj) == expected

    def test_repr_overridden(self):
        class date_safe(datetime.date):
            pass

        class datetime_safe(datetime.datetime):
            pass

        class time_safe(datetime.time):
            pass

        class timedelta_safe(datetime.timedelta):
            pass

        checks = (
            (date_safe(2015, 6, 8), "date_safe(2015, 6, 8)"),
            (datetime_safe(2015, 6, 8, 12, 34, 56), "datetime_safe(2015, 6, 8, 12, 34, 56)"),
            (time_safe(12, 34, 56), "time_safe(12, 34, 56)"),
            (timedelta_safe(1), "timedelta_safe(1)"),
            (timedelta_safe(1, 2), "timedelta_safe(1, 2)"),
            (timedelta_safe(1, 2, 3), "timedelta_safe(1, 2, 3)"),
        )
        for obj, expected in checks:
            assert repr(obj) == expected

    def test_attributes(self):
        for x in [datetime.date.today(),
                  datetime.time(),
                  datetime.datetime.utcnow(),
                  datetime.timedelta(),
                  datetime.tzinfo()]:
            raises(AttributeError, 'x.abc = 1')

    def test_timedelta_init_long(self):
        td = datetime.timedelta(microseconds=20000000000000000000)
        assert td.days == 231481481
        assert td.seconds == 41600
        td = datetime.timedelta(microseconds=20000000000000000000.)
        assert td.days == 231481481
        assert td.seconds == 41600

    def test_unpickle(self):
        e = raises(TypeError, datetime.date, '123')
        assert e.value.args[0] == 'an integer is required'
        e = raises(TypeError, datetime.time, '123')
        assert e.value.args[0] == 'an integer is required'
        e = raises(TypeError, datetime.datetime, '123')
        assert e.value.args[0] == 'an integer is required'

        datetime.time('\x01' * 6, None)
        with raises(TypeError) as e:
            datetime.time('\x01' * 6, 123)
        assert str(e.value) == "bad tzinfo state arg"

        datetime.datetime('\x01' * 10, None)
        with raises(TypeError) as e:
            datetime.datetime('\x01' * 10, 123)
        assert str(e.value) == "bad tzinfo state arg"

    def test_strptime(self):
        import time, sys
        if sys.version_info < (2, 6):
            py.test.skip("needs the _strptime module")

        string = '2004-12-01 13:02:47'
        format = '%Y-%m-%d %H:%M:%S'
        expected = datetime.datetime(*(time.strptime(string, format)[0:6]))
        got = datetime.datetime.strptime(string, format)
        assert expected == got

    def test_datetime_rounding(self):
        b = 0.0000001
        a = 0.9999994

        assert datetime.datetime.utcfromtimestamp(a).microsecond == 999999
        assert datetime.datetime.utcfromtimestamp(a).second == 0
        a += b
        assert datetime.datetime.utcfromtimestamp(a).microsecond == 999999
        assert datetime.datetime.utcfromtimestamp(a).second == 0
        a += b
        assert datetime.datetime.utcfromtimestamp(a).microsecond == 0
        assert datetime.datetime.utcfromtimestamp(a).second == 1

    def test_more_datetime_rounding(self):
        # this test verified on top of CPython 2.7 (using a plain
        # "import datetime" above)
        expected_results = {
            -1000.0: 'datetime.datetime(1969, 12, 31, 23, 43, 20)',
            -999.9999996: 'datetime.datetime(1969, 12, 31, 23, 43, 20)',
            -999.4: 'datetime.datetime(1969, 12, 31, 23, 43, 20, 600000)',
            -999.0000004: 'datetime.datetime(1969, 12, 31, 23, 43, 21)',
            -1.0: 'datetime.datetime(1969, 12, 31, 23, 59, 59)',
            -0.9999996: 'datetime.datetime(1969, 12, 31, 23, 59, 59)',
            -0.4: 'datetime.datetime(1969, 12, 31, 23, 59, 59, 600000)',
            -0.0000004: 'datetime.datetime(1970, 1, 1, 0, 0)',
            0.0: 'datetime.datetime(1970, 1, 1, 0, 0)',
            0.0000004: 'datetime.datetime(1970, 1, 1, 0, 0)',
            0.4: 'datetime.datetime(1970, 1, 1, 0, 0, 0, 400000)',
            0.9999996: 'datetime.datetime(1970, 1, 1, 0, 0, 1)',
            1000.0: 'datetime.datetime(1970, 1, 1, 0, 16, 40)',
            1000.0000004: 'datetime.datetime(1970, 1, 1, 0, 16, 40)',
            1000.4: 'datetime.datetime(1970, 1, 1, 0, 16, 40, 400000)',
            1000.9999996: 'datetime.datetime(1970, 1, 1, 0, 16, 41)',
            1293843661.191: 'datetime.datetime(2011, 1, 1, 1, 1, 1, 191000)',
            }
        for t in sorted(expected_results):
            dt = datetime.datetime.utcfromtimestamp(t)
            assert repr(dt) == expected_results[t]

    def test_utcfromtimestamp(self):
        """Confirm that utcfromtimestamp and fromtimestamp give consistent results.

        Based on danchr's test script in https://bugs.pypy.org/issue986
        """
        import os
        import time
        if os.name == 'nt':
            skip("setting os.environ['TZ'] ineffective on windows")
        try:
            prev_tz = os.environ.get("TZ")
            os.environ["TZ"] = "GMT"
            time.tzset()
            for unused in xrange(100):
                now = time.time()
                delta = (datetime.datetime.utcfromtimestamp(now) -
                         datetime.datetime.fromtimestamp(now))
                assert delta.days * 86400 + delta.seconds == 0
        finally:
            if prev_tz is None:
                del os.environ["TZ"]
            else:
                os.environ["TZ"] = prev_tz
            time.tzset()

    def test_utcfromtimestamp_microsecond(self):
        dt = datetime.datetime.utcfromtimestamp(0)
        assert isinstance(dt.microsecond, int)

    def test_default_args(self):
        with py.test.raises(TypeError):
            datetime.datetime()
        with py.test.raises(TypeError):
            datetime.datetime(10)
        with py.test.raises(TypeError):
            datetime.datetime(10, 10)
        datetime.datetime(10, 10, 10)

    def test_check_arg_types(self):
        import decimal
        class Number:
            def __init__(self, value):
                self.value = value
            def __int__(self):
                return self.value
        class SubInt(int): pass
        class SubLong(long): pass

        dt10 = datetime.datetime(10, 10, 10, 10, 10, 10, 10)
        for xx in [10L,
                   decimal.Decimal(10),
                   decimal.Decimal('10.9'),
                   Number(10),
                   Number(10L),
                   SubInt(10),
                   SubLong(10),
                   Number(SubInt(10)),
                   Number(SubLong(10))]:
            dtxx = datetime.datetime(xx, xx, xx, xx, xx, xx, xx)
            assert dt10 == dtxx
            assert type(dtxx.month) is int
            assert type(dtxx.second) is int

        with py.test.raises(TypeError) as e:
            datetime.datetime(10, 10, '10')
        assert str(e.value) == 'an integer is required'

        f10 = Number(10.9)
        with py.test.raises(TypeError) as e:
            datetime.datetime(10, 10, f10)
        assert str(e.value) == '__int__ method should return an integer'

        class Float(float):
            pass
        s10 = Float(10.9)
        with py.test.raises(TypeError) as e:
            datetime.datetime(10, 10, s10)
        assert str(e.value) == 'integer argument expected, got float'

        with py.test.raises(TypeError):
            datetime.datetime(10., 10, 10)
        with py.test.raises(TypeError):
            datetime.datetime(10, 10., 10)
        with py.test.raises(TypeError):
            datetime.datetime(10, 10, 10.)
        with py.test.raises(TypeError):
            datetime.datetime(10, 10, 10, 10.)
        with py.test.raises(TypeError):
            datetime.datetime(10, 10, 10, 10, 10.)
        with py.test.raises(TypeError):
            datetime.datetime(10, 10, 10, 10, 10, 10.)
        with py.test.raises(TypeError):
            datetime.datetime(10, 10, 10, 10, 10, 10, 10.)

    def test_utcnow_microsecond(self):
        import copy

        dt = datetime.datetime.utcnow()
        assert type(dt.microsecond) is int

        copy.copy(dt)

    def test_radd(self):
        class X(object):
            def __radd__(self, other):
                return "radd"
        assert datetime.date(10, 10, 10) + X() == "radd"

    def test_raises_if_passed_naive_datetime_and_start_or_end_time_defined(self):
        class Foo(datetime.tzinfo):
            def utcoffset(self, dt):
                return datetime.timedelta(0.1)
        naive = datetime.datetime(2014, 9, 22)
        aware = datetime.datetime(2014, 9, 22, tzinfo=Foo())
        with py.test.raises(TypeError) as e:
            naive == aware
        assert str(e.value) == "can't compare offset-naive and offset-aware datetimes"
        with py.test.raises(TypeError) as e:
            naive - aware
        assert str(e.value) == "can't subtract offset-naive and offset-aware datetimes"
        naive = datetime.time(7, 32, 12)
        aware = datetime.time(7, 32, 12, tzinfo=Foo())
        with py.test.raises(TypeError) as e:
            naive == aware
        assert str(e.value) == "can't compare offset-naive and offset-aware times"

    def test_future_types_newint(self):
        try:
            from future.types.newint import newint
        except ImportError:
            py.test.skip('requires future')

        dt_from_ints = datetime.datetime(2015, 12, 31, 12, 34, 56)
        dt_from_newints = datetime.datetime(newint(2015), newint(12), newint(31), newint(12), newint(34), newint(56))
        dt_from_mixed = datetime.datetime(2015, newint(12), 31, newint(12), 34, newint(56))
        assert dt_from_ints == dt_from_newints
        assert dt_from_newints == dt_from_mixed
        assert dt_from_mixed == dt_from_ints

        d_from_int = datetime.date.fromtimestamp(1431216000)
        d_from_newint = datetime.date.fromtimestamp(newint(1431216000))
        assert d_from_int == d_from_newint

        dt_from_int = datetime.datetime.fromtimestamp(1431216000)
        dt_from_newint = datetime.datetime.fromtimestamp(newint(1431216000))
        assert dt_from_int == dt_from_newint

        dtu_from_int = datetime.datetime.utcfromtimestamp(1431216000)
        dtu_from_newint = datetime.datetime.utcfromtimestamp(newint(1431216000))
        assert dtu_from_int == dtu_from_newint

        td_from_int = datetime.timedelta(16565)
        tds_from_int = datetime.timedelta(seconds=1431216000)
        td_from_newint = datetime.timedelta(newint(16565))
        tds_from_newint = datetime.timedelta(seconds=newint(1431216000))
        assert td_from_int == tds_from_int
        assert td_from_int == td_from_newint
        assert td_from_int == tds_from_newint
        assert tds_from_int == td_from_newint
        assert tds_from_int == tds_from_newint
        assert td_from_newint == tds_from_newint

        td_mul_int_int = td_from_int * 2
        td_mul_int_newint = td_from_int * newint(2)
        td_mul_newint_int = td_from_newint * 2
        td_mul_newint_newint = td_from_newint * newint(2)
        assert td_mul_int_int == td_mul_int_newint
        assert td_mul_int_int == td_mul_newint_int
        assert td_mul_int_int == td_mul_newint_newint
        assert td_mul_int_newint == td_mul_newint_int
        assert td_mul_int_newint == td_mul_newint_newint
        assert td_mul_newint_int == td_mul_newint_newint

        td_div_int_int = td_from_int / 3600
        td_div_int_newint = td_from_int / newint(3600)
        td_div_newint_int = td_from_newint / 3600
        td_div_newint_newint = td_from_newint / newint(3600)
        assert td_div_int_int == td_div_int_newint
        assert td_div_int_int == td_div_newint_int
        assert td_div_int_int == td_div_newint_newint
        assert td_div_int_newint == td_div_newint_int
        assert td_div_int_newint == td_div_newint_newint
        assert td_div_newint_int == td_div_newint_newint

    def test_return_types(self):
        td = datetime.timedelta(5)
        assert type(td.total_seconds()) is float
        class sub(datetime.timedelta): pass
        assert type(+sub()) is datetime.timedelta

    def test_subclass_date(self):
        # replace() should return a subclass but not call __new__ or __init__.
        class MyDate(datetime.date):
            forbidden = False
            def __new__(cls):
                if cls.forbidden: FAIL
                return datetime.date.__new__(cls, 2016, 2, 3)
            def __init__(self, *args):
                if self.forbidden: FAIL
        d = MyDate()
        d.forbidden = True
        d2 = d.replace(day=5)
        assert type(d2) is MyDate
        assert d2 == datetime.date(2016, 2, 5)

    def test_subclass_time(self):
        # replace() should return a subclass but not call __new__ or __init__.
        class MyTime(datetime.time):
            forbidden = False
            def __new__(cls):
                if cls.forbidden: FAIL
                return datetime.time.__new__(cls, 1, 2, 3)
            def __init__(self, *args):
                if self.forbidden: FAIL
        d = MyTime()
        d.forbidden = True
        d2 = d.replace(hour=5)
        assert type(d2) is MyTime
        assert d2 == datetime.time(5, 2, 3)

    def test_subclass_datetime(self):
        # replace() should return a subclass but not call __new__ or __init__.
        class MyDatetime(datetime.datetime):
            forbidden = False
            def __new__(cls):
                if cls.forbidden: FAIL
                return datetime.datetime.__new__(cls, 2016, 4, 5, 1, 2, 3)
            def __init__(self, *args):
                if self.forbidden: FAIL
        d = MyDatetime()
        d.forbidden = True
        d2 = d.replace(hour=7)
        assert type(d2) is MyDatetime
        assert d2 == datetime.datetime(2016, 4, 5, 7, 2, 3)


class TestDatetimeHost(BaseTestDatetime):
    def setup_class(cls):
        global datetime
        import datetime


class TestDatetimePyPy(BaseTestDatetime):
    def setup_class(cls):
        global datetime
        from lib_pypy import datetime
