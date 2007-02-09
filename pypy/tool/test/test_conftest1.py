
import py

innertest = py.magic.autopath().dirpath('conftest1_innertest.py')
from py.__.test.terminal.terminal import TerminalSession
from py.__.test.outcome import Passed, Failed, Skipped

class TestPyPyTests: 
    def test_select_interplevel(self): 
        config = py.test.config._reparse([innertest, '-k', 'interplevel'])
        session = TerminalSession(config, py.std.sys.stdout)
        session.main()
        l = session.getitemoutcomepairs(Passed)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('test_something', 'test_method')
        #item = l[0][0]
        #assert item.name == 'test_one'
        l = session.getitemoutcomepairs(Skipped)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('app_test_something', 'test_method_app')

    def test_select_applevel(self): 
        config = py.test.config._reparse([innertest, '-k', 'applevel'])
        session = TerminalSession(config, py.std.sys.stdout)
        session.main()
        l = session.getitemoutcomepairs(Passed)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('app_test_something', 'test_method_app')
        #item = l[0][0]
        #assert item.name == 'test_one'
        l = session.getitemoutcomepairs(Skipped)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('test_something', 'test_method')

    def XXX_test_appdirect(self):
        config = py.test.config._reparse([innertest, 
                                          '-k', 'applevel', '--appdirect'])
        session = TerminalSession(config, py.std.sys.stdout)
        session.main()
        l = session.getitemoutcomepairs(Passed)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('app_test_something', 'test_method_app')
        #item = l[0][0]
        #assert item.name == 'test_one'
        l = session.getitemoutcomepairs(Skipped)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('test_something', 'test_method')
        
