from pypy.module.clr.interp_clr import split_fullname

def test_split_fullname():
    split = split_fullname
    assert split('Foo') == ('', 'Foo')
    assert split('System.Foo') == ('System', 'Foo')
    assert split('System.Foo.Bar') == ('System.Foo', 'Bar')
    assert split('System.Foo.A+B') == ('System.Foo', 'A+B')
    assert split('System.') == ('System', '')
    
