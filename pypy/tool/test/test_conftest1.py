
import py

innertest = py.magic.autopath().dirpath('conftest1_innertest.py')
from py.__.test.testing import suptest 

class TestPyPyTests(suptest.InlineSession): 
    def test_select_interplevel(self): 
        sorter = self.parse_and_run("-k", "interplevel", innertest)
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2
        assert not skipped and not failed 
        for repevent in passed: 
            assert repevent.colitem.name in ('test_something', 'test_method')

    def test_select_applevel(self): 
        sorter = self.parse_and_run("-k", "applevel", innertest)
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2
        assert not skipped and not failed 
        for repevent in passed: 
            assert repevent.colitem.name in ('app_test_something', 'test_method_app')

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
        
