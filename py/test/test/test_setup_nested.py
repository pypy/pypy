
#
# test correct setup/teardowns at 
# module, class, and instance level 

modlevel = []
def setup_module(module):
    module.modlevel.append(42) 

def teardown_module(module):
    modlevel.pop()

def test_modlevel():
    assert modlevel[0] == 42

class TestSimpleClassSetup: 
    clslevel = []
    def setup_class(cls):
        cls.clslevel.append(23) 

    def teardown_class(cls):
        cls.clslevel.pop()

    def test_classlevel(self):
        assert self.clslevel[0] == 23

    def test_modulelevel(self):
        assert modlevel == [42] 

class TestInheritedClassSetupStillWorks(TestSimpleClassSetup):
    def test_classlevel_anothertime(self):
        assert self.clslevel == [23]

class SetupTeardownOnInstance(TestSimpleClassSetup):
    def setup_method(self, method):
        self.clslevel.append(17)

    def teardown_method(self, method):
        x = self.clslevel.pop()
        assert x == 17 

    def test_setup(self):
        assert self.clslevel[-1] == 17 
        
