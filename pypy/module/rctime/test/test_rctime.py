from pypy.conftest import gettestobjspace
import os

class AppTestRCTime:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('rctime',))
        cls.space = space

    def test_attributes(self):
        import time as rctime
        assert isinstance(rctime.accept2dyear, int)
        assert isinstance(rctime.altzone, int)
        assert isinstance(rctime.daylight, int)
        assert isinstance(rctime.timezone, int)
        assert isinstance(rctime.tzname, tuple)
        assert isinstance(rctime.__doc__, str)
    
    def test_sleep(self):
        import time as rctime
        import sys
        import os
        raises(TypeError, rctime.sleep, "foo")
        rctime.sleep(1.2345)
        
    def test_clock(self):
        import time as rctime
        rctime.clock()
        assert isinstance(rctime.clock(), float)

    def test_time(self):
        import time as rctime
        t1 = rctime.time()
        assert isinstance(rctime.time(), float)
        assert rctime.time() != 0.0 # 0.0 means failure
        rctime.sleep(0.02)
        t2 = rctime.time()
        assert t1 != t2       # the resolution should be at least 0.01 secs

    def test_ctime(self):
        import time as rctime
        raises(TypeError, rctime.ctime, "foo")
        rctime.ctime(None)
        rctime.ctime()
        res = rctime.ctime(0)
        assert isinstance(res, str)
        rctime.ctime(rctime.time())
        raises(ValueError, rctime.ctime, 1E200)
    
    def test_gmtime(self):
        import time as rctime
        raises(TypeError, rctime.gmtime, "foo")
        rctime.gmtime()
        rctime.gmtime(None)
        rctime.gmtime(0)
        res = rctime.gmtime(rctime.time())
        assert isinstance(res, rctime.struct_time)
        assert res[-1] == 0 # DST is always zero in gmtime()
        t0 = rctime.mktime(rctime.gmtime())
        t1 = rctime.mktime(rctime.gmtime(None))
        assert 0 <= (t1 - t0) < 1.2
        t = rctime.time()
        assert rctime.gmtime(t) == rctime.gmtime(t)

    def test_localtime(self):
        import time as rctime
        raises(TypeError, rctime.localtime, "foo")
        rctime.localtime()
        rctime.localtime(None)
        rctime.localtime(0)
        res = rctime.localtime(rctime.time())
        assert isinstance(res, rctime.struct_time)
        t0 = rctime.mktime(rctime.localtime())
        t1 = rctime.mktime(rctime.localtime(None))
        assert 0 <= (t1 - t0) < 1.2
        t = rctime.time()
        assert rctime.localtime(t) == rctime.localtime(t)
    
    def test_mktime(self):
        import time as rctime
        import os, sys
        raises(TypeError, rctime.mktime, "foo")
        raises(TypeError, rctime.mktime, None)
        raises(TypeError, rctime.mktime, (1, 2))
        raises(TypeError, rctime.mktime, (1, 2, 3, 4, 5, 6, 'f', 8, 9))
        res = rctime.mktime(rctime.localtime())
        assert isinstance(res, float)
        
        ltime = rctime.localtime()
        rctime.accept2dyear == 0
        ltime = list(ltime)
        ltime[0] = 1899
        raises(ValueError, rctime.mktime, tuple(ltime))
        rctime.accept2dyear == 1
    
        ltime = list(ltime)
        ltime[0] = 67
        ltime = tuple(ltime)
        if os.name != "nt" and sys.maxint < 1<<32:   # time_t may be 64bit
            raises(OverflowError, rctime.mktime, ltime)
    
        ltime = list(ltime)
        ltime[0] = 100
        raises(ValueError, rctime.mktime, tuple(ltime))
    
        t = rctime.time()
        assert long(rctime.mktime(rctime.localtime(t))) == long(t)
        assert long(rctime.mktime(rctime.gmtime(t))) - rctime.timezone == long(t)
        ltime = rctime.localtime()
        assert rctime.mktime(tuple(ltime)) == rctime.mktime(ltime)
    
    def test_asctime(self):
        import time as rctime
        rctime.asctime()
        # raises(TypeError, rctime.asctime, None)
        raises(TypeError, rctime.asctime, ())
        raises(TypeError, rctime.asctime, (1,))
        raises(TypeError, rctime.asctime, range(8))
        raises(TypeError, rctime.asctime, (1, 2))
        raises(TypeError, rctime.asctime, (1, 2, 3, 4, 5, 6, 'f', 8, 9))
        raises(TypeError, rctime.asctime, "foo")
        res = rctime.asctime()
        assert isinstance(res, str)
        rctime.asctime(rctime.localtime())
        t = rctime.time()
        assert rctime.ctime(t) == rctime.asctime(rctime.localtime(t))
        if rctime.timezone:
            assert rctime.ctime(t) != rctime.asctime(rctime.gmtime(t))
        ltime = rctime.localtime()
        assert rctime.asctime(tuple(ltime)) == rctime.asctime(ltime)

    def test_struct_time(self):
        import time as rctime
        raises(TypeError, rctime.struct_time)
        raises(TypeError, rctime.struct_time, "foo")
        raises(TypeError, rctime.struct_time, (1, 2, 3))
        tup = (1, 2, 3, 4, 5, 6, 7, 8, 9)
        st_time = rctime.struct_time(tup)
        assert str(st_time) == str(tup)
        assert len(st_time) == len(tup)
    
    def test_tzset(self):
        import time as rctime
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
            rctime.tzset()
            os.environ['TZ'] = utc
            rctime.tzset()
            assert rctime.gmtime(xmas2002) == rctime.localtime(xmas2002)
            assert rctime.daylight == 0
            assert rctime.timezone == 0
            assert rctime.localtime(xmas2002).tm_isdst == 0
            
            # make sure we can switch to US/Eastern
            os.environ['TZ'] = eastern
            rctime.tzset()
            assert rctime.gmtime(xmas2002) != rctime.localtime(xmas2002)
            assert rctime.tzname == ('EST', 'EDT')
            assert len(rctime.tzname) == 2
            assert rctime.daylight == 1
            assert rctime.timezone == 18000
            assert rctime.altzone == 14400
            assert rctime.localtime(xmas2002).tm_isdst == 0
            
            # now go to the southern hemisphere.
            os.environ['TZ'] = victoria
            rctime.tzset()
            assert rctime.gmtime(xmas2002) != rctime.localtime(xmas2002)
            assert rctime.tzname[0] == 'AEST'
            assert rctime.tzname[1] == 'AEDT'
            assert len(rctime.tzname) == 2
            assert rctime.daylight == 1
            assert rctime.timezone == -36000
            assert rctime.altzone == -39600
            assert rctime.localtime(xmas2002).tm_isdst == 1
        finally:
            # repair TZ environment variable in case any other tests
            # rely on it.
            if org_TZ is not None:
                os.environ['TZ'] = org_TZ
            elif os.environ.has_key('TZ'):
                del os.environ['TZ']
            rctime.tzset()

    def test_strftime(self):
        import time as rctime
        
        t = rctime.time()
        tt = rctime.gmtime(t)
        for directive in ('a', 'A', 'b', 'B', 'c', 'd', 'H', 'I',
                          'j', 'm', 'M', 'p', 'S',
                          'U', 'w', 'W', 'x', 'X', 'y', 'Y', 'Z', '%'):
            format = ' %' + directive
            rctime.strftime(format, tt)
        
        raises(TypeError, rctime.strftime, ())
        raises(TypeError, rctime.strftime, (1,))
        raises(TypeError, rctime.strftime, range(8))
        exp = '2000 01 01 00 00 00 1 001'
        assert rctime.strftime("%Y %m %d %H %M %S %w %j", (0,)*9) == exp

    def test_strftime_bounds_checking(self):
        import time as rctime
        
        # make sure that strftime() checks the bounds of the various parts
        # of the time tuple.
    
        # check year
        raises(ValueError, rctime.strftime, '', (1899, 1, 1, 0, 0, 0, 0, 1, -1))
        if rctime.accept2dyear:
            raises(ValueError, rctime.strftime, '', (-1, 1, 1, 0, 0, 0, 0, 1, -1))
            raises(ValueError, rctime.strftime, '', (100, 1, 1, 0, 0, 0, 0, 1, -1))
        # check month
        raises(ValueError, rctime.strftime, '', (1900, 13, 1, 0, 0, 0, 0, 1, -1))
        # check day of month
        raises(ValueError, rctime.strftime, '', (1900, 1, 32, 0, 0, 0, 0, 1, -1))
        # check hour
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, -1, 0, 0, 0, 1, -1))
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, 24, 0, 0, 0, 1, -1))
        # check minute
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, -1, 0, 0, 1, -1))
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 60, 0, 0, 1, -1))
        # check second
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, -1, 0, 1, -1))
        # C99 only requires allowing for one leap second, but Python's docs say
        # allow two leap seconds (0..61)
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 62, 0, 1, -1))
        # no check for upper-bound day of week;
        #  value forced into range by a "% 7" calculation.
        # start check at -2 since gettmarg() increments value before taking
        #  modulo.
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 0, -2, 1, -1))
        # check day of the year
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 0, 0, 367, -1))
        # check daylight savings flag
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 0, 0, 1, -2))
        raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 0, 0, 1, 2))

    def test_strptime(self):
        import time as rctime
        
        t = rctime.time()
        tt = rctime.gmtime(t)
        for directive in ('a', 'A', 'b', 'B', 'c', 'd', 'H', 'I',
                          'j', 'm', 'M', 'p', 'S',
                          'U', 'w', 'W', 'x', 'X', 'y', 'Y', 'Z', '%'):
            format = ' %' + directive
            print format
            rctime.strptime(rctime.strftime(format, tt), format)

    def test_pickle(self):
        import pickle
        import time as rctime
        now = rctime.localtime()
        new = pickle.loads(pickle.dumps(now))
        assert new == now
        assert type(new) is type(now)
