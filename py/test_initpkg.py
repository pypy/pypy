import py
import types

def test_dir():
    for name in dir(py):
        if not name.startswith('_'):
            obj = getattr(py, name)
            if isinstance(obj, types.ModuleType):
                keys = dir(obj) 
                assert len(keys) > 0 
                assert getattr(obj, '__map__')  == {}

def test_virtual_module_identity():
    from py import path as path1
    from py import path as path2
    assert path1 is path2 
    from py.path import local as local1
    from py.path import local as local2
    assert local1 is local2

def test_importing_all_implementations():
    base = py.path.local(py.__file__).dirpath()
    for p in base.visit('*.py', py.path.checker(dotfile=0)):
        relpath = p.new(ext='').relto(base) 
        if base.sep in relpath: # not std/*.py itself 
            if relpath.find('test/data') != -1: 
                continue
            if relpath.find('bin/') != -1: 
                continue
            relpath = relpath.replace(base.sep, '.') 
            modpath = 'py.__impl__.%s' % relpath 
            assert __import__(modpath) 

def test_shahexdigest(): 
    hex = py.__package__.shahexdigest() 
    assert len(hex) == 40

def test_getzipdata():
    s = py.__package__.getzipdata()
    
# the following test should abasically work in the future 
def XXXtest_virtual_on_the_fly():
    py.initpkg('my', {
        'x.abspath' : 'os.path.abspath', 
        'x.local'   : 'py.path.local',
        'y'   : 'smtplib', 
        'z.cmdexec'   : 'py.process.cmdexec', 
    })
    from my.x import abspath
    from my.x import local 
    import smtplib 
    from my import y
    assert y is smtplib 
    from my.z import cmdexec
    from py.process import cmdexec as cmdexec2
    assert cmdexec is cmdexec2

##def test_help():
#    help(std.path) 
#    #assert False
