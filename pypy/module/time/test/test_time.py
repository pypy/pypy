class AppTestTime:
    spaceconfig = {
        "usemodules": ['time', 'struct', 'binascii'],
    }

    def test_attributes(self):
        import time
        assert isinstance(time.altzone, int)
        assert isinstance(time.daylight, int)
        assert isinstance(time.timezone, int)
        assert isinstance(time.tzname, tuple)
        assert isinstance(time.__doc__, str)
        assert isinstance(time._STRUCT_TM_ITEMS, int)

    def test_sleep(self):
        import sys
        import os
        import time
        raises(TypeError, time.sleep, "foo")
        time.sleep(0.12345)
        raises(ValueError, time.sleep, -1.0)

    def test_clock(self):
        import time
        time.clock()
        assert isinstance(time.clock(), float)

    def test_time(self):
        import time
        t1 = time.time()
        assert isinstance(time.time(), float)
        assert time.time() != 0.0 # 0.0 means failure
        time.sleep(0.02)
        t2 = time.time()
        assert t1 != t2       # the resolution should be at least 0.01 secs

    def test_clock_realtime(self):
        import time
        if not hasattr(time, 'clock_gettime'):
            skip("need time.clock_gettime()")
        t1 = time.clock_gettime(time.CLOCK_REALTIME)
        assert isinstance(t1, float)
        time.sleep(time.clock_getres(time.CLOCK_REALTIME))
        t2 = time.clock_gettime(time.CLOCK_REALTIME)
        assert t1 != t2

    def test_clock_monotonic(self):
        import time
        if not (hasattr(time, 'clock_gettime') and
                hasattr(time, 'CLOCK_MONOTONIC')):
            skip("need time.clock_gettime()/CLOCK_MONOTONIC")
        t1 = time.clock_gettime(time.CLOCK_MONOTONIC)
        assert isinstance(t1, float)
        time.sleep(time.clock_getres(time.CLOCK_MONOTONIC))
        t2 = time.clock_gettime(time.CLOCK_MONOTONIC)
        assert t1 < t2

    def test_ctime(self):
        import time
        raises(TypeError, time.ctime, "foo")
        time.ctime(None)
        time.ctime()
        res = time.ctime(0)
        assert isinstance(res, str)
        time.ctime(time.time())
        raises(OverflowError, time.ctime, 1E200)
        raises(OverflowError, time.ctime, 10**900)
        for year in [-100, 100, 1000, 2000, 10000]:
            try:
                testval = time.mktime((year, 1, 10) + (0,)*6)
            except (ValueError, OverflowError):
                # If mktime fails, ctime will fail too.  This may happen
                # on some platforms.
                pass
            else:
                assert time.ctime(testval)[20:] == str(year)

    def test_gmtime(self):
        import time
        raises(TypeError, time.gmtime, "foo")
        time.gmtime()
        time.gmtime(None)
        time.gmtime(0)
        res = time.gmtime(time.time())
        assert isinstance(res, time.struct_time)
        assert res[-1] == 0 # DST is always zero in gmtime()
        t0 = time.mktime(time.gmtime())
        t1 = time.mktime(time.gmtime(None))
        assert 0 <= (t1 - t0) < 1.2
        t = time.time()
        assert time.gmtime(t) == time.gmtime(t)
        raises(OverflowError, time.gmtime, 2**64)
        raises(OverflowError, time.gmtime, -2**64)

    def test_localtime(self):
        import time
        import os
        raises(TypeError, time.localtime, "foo")
        time.localtime()
        time.localtime(None)
        time.localtime(0)
        res = time.localtime(time.time())
        assert isinstance(res, time.struct_time)
        t0 = time.mktime(time.localtime())
        t1 = time.mktime(time.localtime(None))
        assert 0 <= (t1 - t0) < 1.2
        t = time.time()
        assert time.localtime(t) == time.localtime(t)
        if os.name == 'nt':
            raises(ValueError, time.localtime, -1)
        else:
            time.localtime(-1)

    def test_mktime(self):
        import time
        import os, sys
        raises(TypeError, time.mktime, "foo")
        raises(TypeError, time.mktime, None)
        raises(TypeError, time.mktime, (1, 2))
        raises(TypeError, time.mktime, (1, 2, 3, 4, 5, 6, 'f', 8, 9))
        res = time.mktime(time.localtime())
        assert isinstance(res, float)

        ltime = time.localtime()
        ltime = list(ltime)
        ltime[0] = -1
        time.mktime(tuple(ltime))  # Does not crash anymore
        ltime[0] = 100
        time.mktime(tuple(ltime))  # Does not crash anymore

        t = time.time()
        assert int(time.mktime(time.localtime(t))) == int(t)
        assert int(time.mktime(time.gmtime(t))) - time.timezone == int(t)
        ltime = time.localtime()
        assert time.mktime(tuple(ltime)) == time.mktime(ltime)
        if os.name != 'nt':
            assert time.mktime(time.localtime(-1)) == -1

        res = time.mktime((2000, 1, 1, 0, 0, 0, -1, -1, -1))
        if os.name == 'nt':
            assert time.ctime(res) == 'Sat Jan 01 00:00:00 2000'
        else:
            assert time.ctime(res) == 'Sat Jan  1 00:00:00 2000'

    def test_asctime(self):
        import time
        time.asctime()
        # raises(TypeError, time.asctime, None)
        raises(TypeError, time.asctime, ())
        raises(TypeError, time.asctime, (1,))
        raises(TypeError, time.asctime, range(8))
        raises(TypeError, time.asctime, (1, 2))
        raises(TypeError, time.asctime, (1, 2, 3, 4, 5, 6, 'f', 8, 9))
        raises(TypeError, time.asctime, "foo")
        raises(ValueError, time.asctime, (1900, -1, 1, 0, 0, 0, 0, 1, -1))
        res = time.asctime()
        assert isinstance(res, str)
        time.asctime(time.localtime())
        t = time.time()
        assert time.ctime(t) == time.asctime(time.localtime(t))
        if time.timezone:
            assert time.ctime(t) != time.asctime(time.gmtime(t))
        ltime = time.localtime()
        assert time.asctime(tuple(ltime)) == time.asctime(ltime)
        try:
            time.asctime((12345,) + (0,) * 8)  # assert this doesn't crash
        except ValueError:
            pass  # some OS (ie POSIXes besides Linux) reject year > 9999

    def test_asctime_large_year(self):
        import time
        assert time.asctime((12345,) +
                              (0,) * 8) == 'Mon Jan  1 00:00:00 12345'
        assert time.asctime((123456789,) +
                              (0,) * 8) == 'Mon Jan  1 00:00:00 123456789'
        sizeof_int = 4
        bigyear = (1 << 8 * sizeof_int - 1) - 1
        asc = time.asctime((bigyear, 6, 1) + (0,)*6)
        assert asc[-len(str(bigyear)):] == str(bigyear)
        raises(OverflowError, time.asctime, (bigyear + 1,) + (0,)*8)

    def test_struct_time(self):
        import time
        raises(TypeError, time.struct_time)
        raises(TypeError, time.struct_time, "foo")
        raises(TypeError, time.struct_time, (1, 2, 3))
        tup = (1, 2, 3, 4, 5, 6, 7, 8, 9)
        st_time = time.struct_time(tup)
        assert str(st_time).startswith('time.struct_time(tm_year=1, ')
        assert len(st_time) == len(tup)

    def test_tzset(self):
        import time
        import os

        if not os.name == "posix":
            skip("tzset available only under Unix")

        # epoch time of midnight Dec 25th 2002. Never DST in northern
        # hemisphere.
        xmas2002 = 1040774400.0

        # these formats are correct for 2002, and possibly future years
        # this format is the 'standard' as documented at:
        # http://www.opengroup.org/onlinepubs/007904975/basedefs/xbd_chap08.html
        # They are also documented in the tzset(3) man page on most Unix
        # systems.
        eastern = 'EST+05EDT,M4.1.0,M10.5.0'
        victoria = 'AEST-10AEDT-11,M10.5.0,M3.5.0'
        utc = 'UTC+0'

        org_TZ = os.environ.get('TZ', None)
        try:
            # Make sure we can switch to UTC time and results are correct
            # Note that unknown timezones default to UTC.
            # Note that altzone is undefined in UTC, as there is no DST
            os.environ['TZ'] = eastern
            time.tzset()
            os.environ['TZ'] = utc
            time.tzset()
            assert time.gmtime(xmas2002) == time.localtime(xmas2002)
            assert time.daylight == 0
            assert time.timezone == 0
            assert time.localtime(xmas2002).tm_isdst == 0

            # make sure we can switch to US/Eastern
            os.environ['TZ'] = eastern
            time.tzset()
            assert time.gmtime(xmas2002) != time.localtime(xmas2002)
            assert time.tzname == ('EST', 'EDT')
            assert len(time.tzname) == 2
            assert time.daylight == 1
            assert time.timezone == 18000
            assert time.altzone == 14400
            assert time.localtime(xmas2002).tm_isdst == 0

            # now go to the southern hemisphere.
            os.environ['TZ'] = victoria
            time.tzset()
            assert time.gmtime(xmas2002) != time.localtime(xmas2002)
            assert time.tzname[0] == 'AEST'
            assert time.tzname[1] == 'AEDT'
            assert len(time.tzname) == 2
            assert time.daylight == 1
            assert time.timezone == -36000
            assert time.altzone == -39600
            assert time.localtime(xmas2002).tm_isdst == 1
        finally:
            # repair TZ environment variable in case any other tests
            # rely on it.
            if org_TZ is not None:
                os.environ['TZ'] = org_TZ
            elif 'TZ' in os.environ:
                del os.environ['TZ']
            time.tzset()

    def test_strftime(self):
        import time
        import os, sys

        t = time.time()
        tt = time.gmtime(t)
        for directive in ('a', 'A', 'b', 'B', 'c', 'd', 'H', 'I',
                          'j', 'm', 'M', 'p', 'S',
                          'U', 'w', 'W', 'x', 'X', 'y', 'Y', 'Z', '%'):
            format = ' %' + directive
            time.strftime(format, tt)

        raises(TypeError, time.strftime, ())
        raises(TypeError, time.strftime, (1,))
        raises(TypeError, time.strftime, range(8))

        # Guard against invalid/non-supported format string
        # so that Python don't crash (Windows crashes when the format string
        # input to [w]strftime is not kosher.
        if os.name == 'nt':
            raises(ValueError, time.strftime, '%f')
            return
        elif sys.platform == 'darwin' or 'bsd' in sys.platform:
            # darwin strips % of unknown format codes
            # http://bugs.python.org/issue9811
            assert time.strftime('%f') == 'f'

            # Darwin always use four digits for %Y, Linux uses as many as needed.
            expected_year = '0000'
        else:
            assert time.strftime('%f') == '%f'
            expected_year = '0'

        expected_formatted_date = expected_year + ' 01 01 00 00 00 1 001'
        assert time.strftime("%Y %m %d %H %M %S %w %j", (0,) * 9) == expected_formatted_date

    def test_strftime_ext(self):
        import time

        tt = time.gmtime()
        try:
            result = time.strftime('%D', tt)
        except ValueError:
            pass
        else:
            assert result == time.strftime('%m/%d/%y', tt)

    def test_strftime_bounds_checking(self):
        import time

        # make sure that strftime() checks the bounds of the various parts
        # of the time tuple.

        # check year
        time.strftime('', (1899, 1, 1, 0, 0, 0, 0, 1, -1))
        time.strftime('', (0, 1, 1, 0, 0, 0, 0, 1, -1))

        # check month
        raises(ValueError, time.strftime, '', (1900, 13, 1, 0, 0, 0, 0, 1, -1))
        # check day of month
        raises(ValueError, time.strftime, '', (1900, 1, 32, 0, 0, 0, 0, 1, -1))
        # check hour
        raises(ValueError, time.strftime, '', (1900, 1, 1, -1, 0, 0, 0, 1, -1))
        raises(ValueError, time.strftime, '', (1900, 1, 1, 24, 0, 0, 0, 1, -1))
        # check minute
        raises(ValueError, time.strftime, '', (1900, 1, 1, 0, -1, 0, 0, 1, -1))
        raises(ValueError, time.strftime, '', (1900, 1, 1, 0, 60, 0, 0, 1, -1))
        # check second
        raises(ValueError, time.strftime, '', (1900, 1, 1, 0, 0, -1, 0, 1, -1))
        # C99 only requires allowing for one leap second, but Python's docs say
        # allow two leap seconds (0..61)
        raises(ValueError, time.strftime, '', (1900, 1, 1, 0, 0, 62, 0, 1, -1))
        # no check for upper-bound day of week;
        #  value forced into range by a "% 7" calculation.
        # start check at -2 since gettmarg() increments value before taking
        #  modulo.
        raises(ValueError, time.strftime, '', (1900, 1, 1, 0, 0, 0, -2, 1, -1))
        # check day of the year
        raises(ValueError, time.strftime, '', (1900, 1, 1, 0, 0, 0, 0, 367, -1))
        # check daylight savings flag
        time.strftime('', (1900, 1, 1, 0, 0, 0, 0, 1, -2))
        time.strftime('', (1900, 1, 1, 0, 0, 0, 0, 1, 2))

    def test_strptime(self):
        import time

        t = time.time()
        tt = time.gmtime(t)
        assert isinstance(time.strptime("", ""), type(tt))

        for directive in ('a', 'A', 'b', 'B', 'c', 'd', 'H', 'I',
                          'j', 'm', 'M', 'p', 'S',
                          'U', 'w', 'W', 'x', 'X', 'y', 'Y', 'Z', '%'):
            format = ' %' + directive
            print(format)
            time.strptime(time.strftime(format, tt), format)

    def test_pickle(self):
        import pickle
        import time
        now = time.localtime()
        new = pickle.loads(pickle.dumps(now))
        assert new == now
        assert type(new) is type(now)

    def test_monotonic(self):
        import time
        t1 = time.monotonic()
        assert isinstance(t1, float)
        time.sleep(0.02)
        t2 = time.monotonic()
        assert t1 < t2

    def test_perf_counter(self):
        import time
        assert isinstance(time.perf_counter(), float)

    def test_process_time(self):
        import time
        t1 = time.process_time()
        assert isinstance(t1, float)
        time.sleep(0.1)
        t2 = time.process_time()
        # process_time() should not include time spent during sleep
        assert (t2 - t1) < 0.05

    def test_get_clock_info(self):
        import time
        clocks = ['clock', 'perf_counter', 'process_time', 'time']
        if hasattr(time, 'monotonic'):
            clocks.append('monotonic')
        for name in clocks:
            info = time.get_clock_info(name)
            assert isinstance(info.implementation, str)
            assert info.implementation != ''
            assert isinstance(info.monotonic, bool)
            assert isinstance(info.resolution, float)
            assert info.resolution > 0.0
            assert info.resolution <= 1.0
            assert isinstance(info.adjustable, bool)
