
import py

innertest = py.magic.autopath().dirpath('conftest1_innertest.py')

class TestPyPyTests: 
    def test_select_interplevel(self): 
        config, args = py.test.Config.parse(['-k', 'interplevel'])
        session = config.getsessionclass()(config, py.std.sys.stdout)
        session.main([innertest])
        l = session.getitemoutcomepairs(py.test.Item.Passed)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('test_something', 'test_method')
        #item = l[0][0]
        #assert item.name == 'test_one'
        l = session.getitemoutcomepairs(py.test.Item.Skipped)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('app_test_something', 'test_method_app')

    def test_select_applevel(self): 
        config, args = py.test.Config.parse(['-k', 'applevel'])
        session = config.getsessionclass()(config, py.std.sys.stdout)
        session.main([innertest])
        l = session.getitemoutcomepairs(py.test.Item.Passed)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('app_test_something', 'test_method_app')
        #item = l[0][0]
        #assert item.name == 'test_one'
        l = session.getitemoutcomepairs(py.test.Item.Skipped)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('test_something', 'test_method')

    def XXX_test_appdirect(self):
        config, args = py.test.Config.parse(['-k', 'applevel', '--appdirect', str(innertest)])
        session = config.getsessionclass()(config, py.std.sys.stdout)
        session.main([innertest])
        l = session.getitemoutcomepairs(py.test.Item.Passed)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('app_test_something', 'test_method_app')
        #item = l[0][0]
        #assert item.name == 'test_one'
        l = session.getitemoutcomepairs(py.test.Item.Skipped)
        assert len(l) == 2 
        for item in l:
            assert item[0].name in ('test_something', 'test_method')
        
