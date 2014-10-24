from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module._vmprof import interp_vmprof
from pypy.module._vmprof.interp_vmprof import do_get_virtual_ip, _vmprof

class FakePyFrame(object):

    def __init__(self, pycode):
        self.pycode = pycode

class FakePyCode(object):

    _vmprof_setup_maybe = interp_vmprof.PyCode._vmprof_setup_maybe.im_func

    def __init__(self, co_name):
        self.co_name = co_name
        self._vmprof_setup_maybe()

def test_get_virtual_ip(monkeypatch):
    functions = []
    def register_virtual_function(name, start, end):
        name = rffi.charp2str(name)
        start = rffi.cast(lltype.Signed, start)
        end = rffi.cast(lltype.Signed, end)
        functions.append((name, start, end))
    monkeypatch.setattr(interp_vmprof, 'vmprof_register_virtual_function', register_virtual_function)
    #
    mycode = FakePyCode('foo')
    assert mycode._vmprof_virtual_ip < 0
    myframe = FakePyFrame(mycode)

    _vmprof.counter = 42
    ip = do_get_virtual_ip(myframe)
    assert ip == mycode._vmprof_virtual_ip
    assert functions == [('py:foo', ip, ip)]

    # the second time, we don't register it again
    functions = []
    ip = do_get_virtual_ip(myframe)
    assert ip == mycode._vmprof_virtual_ip
    assert functions == []

    # now, let's try with a long name
    mycode = FakePyCode('abcde' * 200)
    myframe = FakePyFrame(mycode)
    functions = []
    ip2 = do_get_virtual_ip(myframe)
    assert ip2 == mycode._vmprof_virtual_ip
    assert ip2 < ip # because it was generated later
    assert len(functions) == 1
    name, start, end = functions[0]
    assert len(name) == 127
    assert name == 'py:' + ('abcde'*200)[:124]
    
