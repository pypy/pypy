from py.test import raises

# def setup_module(mod):
#     mod.t = rctime.time()
#     mod.tup = (1, 2, 3, 4, 5, 6, 7, 8, 9)
#     mod.st_time = rctime.struct_time(mod.tup)
class AppTestRCTime:
    #def test_time(self):
    #    assert t != None
    #    assert t != 0.0

    # def test_attributes():
    #     assert isinstance(rctime.accept2dyear, int)
    #     assert isinstance(rctime.altzone, int)
    #     assert isinstance(rctime.daylight, int)
    #     assert isinstance(rctime.timezone, int)
    #     assert isinstance(rctime.tzname, tuple)
    # 
    def test_sleep(self):
        import rctime
        raises(TypeError, rctime.sleep, "foo")
        rctime.sleep(1.2345)
        
    def test_clock(self):
        import rctime
        rctime.clock()
        assert isinstance(rctime.clock(), float)

    def test_accept2dyear(self):
        import rctime
        import os
        assert rctime.accept2dyear == 1
    
    def test_time(self):
        import rctime
        rctime.time()
        assert isinstance(rctime.time(), float)

    def test_ctime(self):
        import rctime
        raises(TypeError, rctime.ctime, "foo")
        rctime.ctime(None)
        rctime.ctime()
        res = rctime.ctime(0)
        assert isinstance(res, str)
        rctime.ctime(rctime.time())

    # 
    # def test_gmtime():
    #     py.test.raises(TypeError, rctime.gmtime, "foo")
    #     assert rctime.gmtime() != None
    #     assert rctime.gmtime() != ()
    #     assert rctime.gmtime(None) != None
    #     assert rctime.gmtime(None) != ()
    #     t0 = rctime.mktime(rctime.gmtime())
    #     t1 = rctime.mktime(rctime.gmtime(None))
    #     assert 0 <= (t1 - t0) < 0.2
    #     assert rctime.gmtime(t) == rctime.gmtime(t)
    # 
    # def test_localtime():
    #     py.test.raises(TypeError, rctime.localtime, "foo")
    #     assert rctime.localtime() != None
    #     assert rctime.localtime() != ()
    #     assert rctime.localtime(None) != None
    #     assert rctime.localtime(None) != ()
    #     t0 = rctime.mktime(rctime.gmtime())
    #     t1 = rctime.mktime(rctime.gmtime(None))
    #     assert 0 <= (t1 - t0) < 0.2
    #     assert rctime.localtime(t) == rctime.localtime(t)
    # 
    # def test_mktime():
    #     py.test.raises(TypeError, rctime.mktime, "foo")
    #     py.test.raises(TypeError, rctime.mktime, None)
    #     py.test.raises(TypeError, rctime.mktime, (1, 2))
    # 
    #     arg = rctime.localtime(t)
    # 
    #     assert rctime.mktime(arg) != None
    #     assert rctime.mktime(arg) != 0.0
    # 
    #     rctime.accept2dyear == 0
    #     arg = list(arg)
    #     arg[0] = 1899
    #     arg = tuple(arg)
    #     py.test.raises(ValueError, rctime.mktime, arg)
    #     rctime.accept2dyear == 1
    # 
    #     arg = list(arg)
    #     arg[0] = 67
    #     arg = tuple(arg)
    #     py.test.raises(ValueError, rctime.mktime, arg)
    # 
    #     arg = list(arg)
    #     arg[0] = 100
    #     arg = tuple(arg)
    #     py.test.raises(ValueError, rctime.mktime, arg)
    # 
    #     assert long(rctime.mktime(rctime.localtime(t))) == long(t)
    #     assert long(rctime.mktime(rctime.gmtime(t))) != long(t)
    #     lt = rctime.localtime()
    #     assert rctime.mktime(tuple(lt)) == rctime.mktime(lt)
    # 
    # def test_asrctime():
    #     py.test.raises(TypeError, rctime.asrctime, "foo")
    #     py.test.raises(TypeError, rctime.asrctime, None)
    #     py.test.raises(TypeError, rctime.asrctime, (1, 2))
    #     assert rctime.asrctime() != None
    #     assert rctime.asrctime() != ""
    #     assert rctime.rctime(t) == rctime.asrctime(rctime.localtime(t))
    #     assert rctime.rctime(t) != rctime.asrctime(rctime.gmtime(t))
    #     lt = rctime.localtime()
    #     assert rctime.asrctime(tuple(lt)) == rctime.asrctime(lt)
    # 
    # def test_struct_time():
    #     py.test.raises(TypeError, rctime.struct_time)
    #     py.test.raises(TypeError, rctime.struct_time, "foo")
    #     py.test.raises(TypeError, rctime.struct_time, (1, 2, 3))
    #     assert str(st_time) == str(tup)
    # 
    # def test_tzset():
    #     if not hasattr(rctime, "tzset"):
    #         py.test.skip("available only under Unix")
    # 
    #     # epoch time of midnight Dec 25th 2002. Never DST in northern
    #     # hemisphere.
    #     xmas2002 = 1040774400.0
    # 
    #     # these formats are correct for 2002, and possibly future years
    #     # this format is the 'standard' as documented at:
    #     # http://www.opengroup.org/onlinepubs/007904975/basedefs/xbd_chap08.html
    #     # They are also documented in the tzset(3) man page on most Unix
    #     # systems.
    #     eastern = 'EST+05EDT,M4.1.0,M10.5.0'
    #     victoria = 'AEST-10AEDT-11,M10.5.0,M3.5.0'
    #     utc = 'UTC+0'
    # 
    #     org_TZ = os.environ.get('TZ', None)
    #     try:
    #         # Make sure we can switch to UTC time and results are correct
    #         # Note that unknown timezones default to UTC.
    #         # Note that altzone is undefined in UTC, as there is no DST
    #         os.environ['TZ'] = eastern
    #         rctime.tzset()
    #         os.environ['TZ'] = utc
    #         rctime.tzset()
    #         assert rctime.gmtime(xmas2002) == rctime.localtime(xmas2002)
    #         assert rctime.daylight == 0
    #         assert rctime.timezone == 0
    #         assert rctime.localtime(xmas2002).tm_isdst == 0
    # 
    #         # make sure we can switch to US/Eastern
    #         os.environ['TZ'] = eastern
    #         rctime.tzset()
    #         assert rctime.gmtime(xmas2002) != rctime.localtime(xmas2002)
    #         assert rctime.tzname == ('EST', 'EDT')
    #         assert len(rctime.tzname) == 2
    #         assert rctime.daylight == 1
    #         assert rctime.timezone == 18000
    #         assert rctime.altzone == 14400
    #         assert rctime.localtime(xmas2002).tm_isdst == 0
    # 
    #         # now go to the southern hemisphere.
    #         os.environ['TZ'] = victoria
    #         rctime.tzset()
    #         assert rctime.gmtime(xmas2002) != rctime.localtime(xmas2002)
    #         assert rctime.tzname[0] == 'AEST'
    #         assert rctime.tzname[1] == 'AEDT'
    #         assert len(rctime.tzname) == 2
    #         assert rctime.daylight == 1
    #         assert rctime.timezone == -36000
    #         assert rctime.altzone == -39600
    #         assert rctime.localtime(xmas2002).tm_isdst == 1
    #     finally:
    #         # repair TZ environment variable in case any other tests
    #         # rely on it.
    #         if org_TZ is not None:
    #             os.environ['TZ'] = org_TZ
    #         elif os.environ.has_key('TZ'):
    #             del os.environ['TZ']
    #         rctime.tzset()
    # 
    # def test_strftime():
    #     tt = rctime.gmtime(t)
    #     for directive in ('a', 'A', 'b', 'B', 'c', 'd', 'H', 'I',
    #                       'j', 'm', 'M', 'p', 'S',
    #                       'U', 'w', 'W', 'x', 'X', 'y', 'Y', 'Z', '%'):
    #         format = ' %' + directive
    #         assert rctime.strftime(format, tt) != None
    #         assert rctime.strftime(format, tt) != ""
    # 
    # def test_strftime_bounds_checking():
    #     # make sure that strftime() checks the bounds of the various parts
    #     # of the time tuple.
    # 
    #     raises = py.test.raises
    # 
    #     # check year
    #     raises(ValueError, rctime.strftime, '', (1899, 1, 1, 0, 0, 0, 0, 1, -1))
    #     if rctime.accept2dyear:
    #         raises(ValueError, rctime.strftime, '', (-1, 1, 1, 0, 0, 0, 0, 1, -1))
    #         raises(ValueError, rctime.strftime, '', (100, 1, 1, 0, 0, 0, 0, 1, -1))
    #     # check month
    #     raises(ValueError, rctime.strftime, '', (1900, 0, 1, 0, 0, 0, 0, 1, -1))
    #     raises(ValueError, rctime.strftime, '', (1900, 13, 1, 0, 0, 0, 0, 1, -1))
    #     # check day of month
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 0, 0, 0, 0, 0, 1, -1))
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 32, 0, 0, 0, 0, 1, -1))
    #     # check hour
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, -1, 0, 0, 0, 1, -1))
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 24, 0, 0, 0, 1, -1))
    #     # check minute
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, -1, 0, 0, 1, -1))
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 60, 0, 0, 1, -1))
    #     # check second
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, -1, 0, 1, -1))
    #     # C99 only requires allowing for one leap second, but Python's docs say
    #     # allow two leap seconds (0..61)
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 62, 0, 1, -1))
    #     # no check for upper-bound day of week;
    #     #  value forced into range by a "% 7" calculation.
    #     # start check at -2 since gettmarg() increments value before taking
    #     #  modulo.
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 0, -2, 1, -1))
    #     # check day of the year
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 0, 0, 0, -1))
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 0, 0, 367, -1))
    #     # check daylight savings flag
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 0, 0, 1, -2))
    #     raises(ValueError, rctime.strftime, '', (1900, 1, 1, 0, 0, 0, 0, 1, 2))
    # 
    # def test_strptime():
    #     tt = rctime.gmtime(t)
    #     for directive in ('a', 'A', 'b', 'B', 'c', 'd', 'H', 'I',
    #                       'j', 'm', 'M', 'p', 'S',
    #                       'U', 'w', 'W', 'x', 'X', 'y', 'Y', 'Z', '%'):
    #         format = ' %' + directive
    #         try:
    #             assert rctime.strptime(rctime.strftime(format, tt), format) != None
    #         except ValueError:
    #             raise ValueError, "conversion specifier: %r failed.' % format"
