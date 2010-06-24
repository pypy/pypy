from pypy.lib.ctypes_config_cache import rebuild
rebuild.rebuild_one('resource.ctc.py')

from pypy.lib import resource

def test_resource():
    x = resource.getrusage(resource.RUSAGE_SELF)
    assert len(x) == 16
    assert x[0] == x[-16] == x.ru_utime
    assert x[1] == x[-15] == x.ru_stime
    assert x[2] == x[-14] == x.ru_maxrss
    assert x[3] == x[-13] == x.ru_ixrss
    assert x[4] == x[-12] == x.ru_idrss
    assert x[5] == x[-11] == x.ru_isrss
    assert x[6] == x[-10] == x.ru_minflt
    assert x[7] == x[-9] == x.ru_majflt
    assert x[8] == x[-8] == x.ru_nswap
    assert x[9] == x[-7] == x.ru_inblock
    assert x[10] == x[-6] == x.ru_oublock
    assert x[11] == x[-5] == x.ru_msgsnd
    assert x[12] == x[-4] == x.ru_msgrcv
    assert x[13] == x[-3] == x.ru_nsignals
    assert x[14] == x[-2] == x.ru_nvcsw
    assert x[15] == x[-1] == x.ru_nivcsw
    for i in range(16):
        if i < 2:
            expected_type = float
        else:
            expected_type = (int, long)
        assert isinstance(x[i], expected_type)
