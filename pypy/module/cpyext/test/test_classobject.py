from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestInstanceMethod(AppTestCpythonExtensionBase):
    def test_instancemethod(self):
        module = self.import_extension('foo', [
            ("instancemethod", "METH_O",
             """
                 return PyInstanceMethod_New(args);
             """)])

        def testfunction(self):
            """some doc"""
            return self

        class InstanceMethod:
            id = module.instancemethod(id)
            testmethod = module.instancemethod(testfunction)

        inst = InstanceMethod()
        assert id(inst) == inst.id()
        assert inst.testmethod() is inst
        assert InstanceMethod.testmethod(inst) is inst
        assert InstanceMethod.__dict__['testmethod'](inst) is inst
        assert inst.testmethod.__doc__ == testfunction.__doc__
        assert InstanceMethod.testmethod.__doc__ == testfunction.__doc__

        InstanceMethod.testmethod.attribute = "test"
        assert testfunction.attribute == "test"
        raises(AttributeError, setattr, inst.testmethod, "attribute", "test")

    def test_pyclass_new_no_bases(self):
        module = self.import_extension('foo', [
            ("new_foo", "METH_O",
             """
                 return PyClass_New(NULL, PyDict_New(), args);
             """)])
        FooClass = module.new_foo("FooClass")
        class Cls1:
            pass
        assert type(FooClass) is type(Cls1)
        assert FooClass.__bases__ == Cls1.__bases__
