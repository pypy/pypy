
import py

innertest = py.path.local(__file__).dirpath('conftest1_innertest.py')
pytest_plugins = "pytest_pytester"

class TestPyPyTests:
    def test_select_interplevel(self, testdir): 
        sorter = testdir.inline_run("-k", "interplevel", innertest)
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2
        assert not skipped and not failed 
        for repevent in passed: 
            assert repevent.item.name in ('test_something', 'test_method')

    def test_select_applevel(self, testdir): 
        sorter = testdir.inline_run("-k", "applevel", innertest)
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2
        assert not skipped and not failed 
        for repevent in passed: 
            assert repevent.item.name in ('app_test_something', 'test_method_app')

    def test_appdirect(self, testdir):
        sorter = testdir.inline_run(innertest, '-k', 'applevel', '--runappdirect')
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2
        print passed
        names = [x.item.name for x in passed]
        assert 'app_test_something' in names 
        assert 'test_method_app' in names 
        
