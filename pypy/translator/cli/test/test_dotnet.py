import py
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.annotation import model as annmodel
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import meth, Meth, Char, Signed, Float, String,\
     ROOT, overload, Instance, new
from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.cli.dotnet import SomeCliClass, SomeCliStaticMethod,\
     NativeInstance, CLR, box, unbox, OverloadingResolver, NativeException,\
     native_exc, new_array, init_array, typeof, eventhandler, clidowncast,\
     fieldinfo_for_const, classof, cast_record_to_object, cast_object_to_record

System = CLR.System
ArrayList = CLR.System.Collections.ArrayList
OpCodes = System.Reflection.Emit.OpCodes
DynamicMethod = System.Reflection.Emit.DynamicMethod
Utils = CLR.pypy.runtime.Utils
FUNCTYPE = ootype.StaticMethod([ootype.Signed, ootype.Signed], ootype.Signed)

class TestDotnetAnnotation(object):

    def test_overloaded_meth_string(self):
        C = Instance("test", ROOT, {},
                     {'foo': overload(meth(Meth([Char], Signed)),
                                      meth(Meth([String], Float)),
                                      resolver=OverloadingResolver),
                      'bar': overload(meth(Meth([Signed], Char)),
                                      meth(Meth([Float], String)),
                                      resolver=OverloadingResolver)})
        def fn1():
            return new(C).foo('a')
        def fn2():
            return new(C).foo('aa')
        def fn3(x):
            return new(C).bar(x)
        a = RPythonAnnotator()
        assert isinstance(a.build_types(fn1, []), annmodel.SomeInteger)
        assert isinstance(a.build_types(fn2, []), annmodel.SomeFloat)
        assert isinstance(a.build_types(fn3, [int]), annmodel.SomeChar)
        assert isinstance(a.build_types(fn3, [float]), annmodel.SomeString)

    def test_class(self):
        def fn():
            return System.Math
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, SomeCliClass)
        assert s.const is System.Math

    def test_fullname(self):
        def fn():
            return CLR.System.Math
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, SomeCliClass)
        assert s.const is System.Math

    def test_staticmeth(self):
        def fn():
            return System.Math.Abs
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, SomeCliStaticMethod)
        assert s.cli_class is System.Math
        assert s.meth_name == 'Abs'

    def test_staticmeth_call(self):
        def fn1():
            return System.Math.Abs(42)
        def fn2():
            return System.Math.Abs(42.5)
        a = RPythonAnnotator()
        assert type(a.build_types(fn1, [])) is annmodel.SomeInteger
        assert type(a.build_types(fn2, [])) is annmodel.SomeFloat

    def test_new_instance(self):
        def fn():
            return ArrayList()
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert isinstance(s.ootype, NativeInstance)
        assert s.ootype._name == '[mscorlib]System.Collections.ArrayList'

    def test_box(self):
        def fn():
            return box(42)
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert s.ootype._name == '[mscorlib]System.Object'
        assert not s.can_be_None

    def test_box_can_be_None(self):
        def fn(flag):
            if flag:
                return box(42)
            else:
                return box(None)
        a = RPythonAnnotator()
        s = a.build_types(fn, [bool])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert s.ootype._name == '[mscorlib]System.Object'
        assert s.can_be_None

    def test_unbox(self):
        def fn():
            x = box(42)
            return unbox(x, ootype.Signed)
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeInteger)

    def test_unbox_can_be_None(self):
        class Foo:
            pass
        def fn():
            x = box(42)
            return unbox(x, Foo)
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeInstance)
        assert s.can_be_None

    def test_array(self):
        def fn():
            x = ArrayList()
            return x.ToArray()
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert s.ootype._isArray
        assert s.ootype._ELEMENT._name == '[mscorlib]System.Object'

    def test_array_getitem(self):
        def fn():
            x = ArrayList().ToArray()
            return x[0]
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert s.ootype._name == '[mscorlib]System.Object'

    def test_mix_None_and_instance(self):
        def fn(x):
            if x:
                return None
            else:
                return box(42)
        a = RPythonAnnotator()
        s = a.build_types(fn, [bool])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert s.can_be_None == True

    def test_box_instance(self):
        class Foo:
            pass
        def fn():
            return box(Foo())
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert s.ootype._name == '[mscorlib]System.Object'

    def test_unbox_instance(self):
        class Foo:
            pass
        def fn():
            boxed = box(Foo())
            return unbox(boxed, Foo)
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeInstance)
        assert s.classdef.name.endswith('Foo')

    def test_can_be_None(self):
        def fn():
            ttype = System.Type.GetType('foo')
            return ttype.get_Namespace()
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeString)
        assert s.can_be_None


class TestDotnetRtyping(CliTest):
    def _skip_pythonnet(self, msg):
        pass

    def test_staticmeth_call(self):
        def fn(x):
            return System.Math.Abs(x)
        assert self.interpret(fn, [-42]) == 42

    def test_staticmeth_overload(self):
        self._skip_pythonnet('Pythonnet bug!')
        def fn(x, y):
            return System.Math.Abs(x), System.Math.Abs(y)
        res = self.interpret(fn, [-42, -42.5])
        item0, item1 = self.ll_to_tuple(res)
        assert item0 == 42
        assert item1 == 42.5

    def test_tostring(self):
        StringBuilder = CLR.System.Text.StringBuilder
        def fn():
            x = StringBuilder()
            x.Append(box("foo")).Append(box("bar"))
            return x.ToString()
        res = self.ll_to_string(self.interpret(fn, []))
        assert res == 'foobar'
    
    def test_box(self):
        def fn():
            x = ArrayList()
            x.Add(box(42))
            x.Add(box('Foo'))
            return x.get_Count()
        assert self.interpret(fn, []) == 2

    def test_whitout_box(self):
        def fn():
            x = ArrayList()
            x.Add(42) # note we have forgot box()
        py.test.raises(TypeError, self.interpret, fn, [])

    def test_unbox(self):
        def fn():
            x = ArrayList()
            x.Add(box(42))
            return unbox(x.get_Item(0), ootype.Signed)
        assert self.interpret(fn, []) == 42

    def test_unbox_string(self):
        def fn():
            x = ArrayList()
            x.Add(box('foo'))
            return unbox(x.get_Item(0), ootype.String)
        assert self.interpret(fn, []) == 'foo'

    def test_box_method(self):
        def fn():
            x = box(42)
            t = x.GetType()
            return t.get_Name()
        res = self.interpret(fn, [])
        assert res == 'Int32'

    def test_box_object(self):
        def fn():
            return box(System.Object()).ToString()
        res = self.interpret(fn, [])
        assert res == 'System.Object'

    def test_array(self):
        def fn():
            x = ArrayList()
            x.Add(box(42))
            array = x.ToArray()
            return unbox(array[0], ootype.Signed)
        assert self.interpret(fn, []) == 42

    def test_new_array(self):
        def fn():
            x = new_array(System.Object, 2)
            x[0] = box(42)
            x[1] = box(43)
            return unbox(x[0], ootype.Signed) + unbox(x[1], ootype.Signed)
        assert self.interpret(fn, []) == 42+43

    def test_init_array(self):
        def fn():
            x = init_array(System.Object, box(42), box(43))
            return unbox(x[0], ootype.Signed) + unbox(x[1], ootype.Signed)
        assert self.interpret(fn, []) == 42+43

    def test_array_setitem_None(self):
        py.test.skip('Mono bug :-(')
        def fn():
            x = init_array(System.Object, box(42), box(43))
            x[0] = None
            return x[0]
        assert self.interpret(fn, []) is None

    def test_array_length(self):
        def fn():
            x = init_array(System.Object, box(42), box(43))
            return len(x)
        assert self.interpret(fn, []) == 2

    def test_null(self):
        def fn():
            return System.Object.Equals(None, None)
        assert self.interpret(fn, []) == True

    def test_null_bound_method(self):
        def fn():
            x = ArrayList()
            x.Add(None)
            return x.get_Item(0)
        assert self.interpret(fn, []) is None

    def test_native_exception_precise(self):
        ArgumentOutOfRangeException = NativeException(CLR.System.ArgumentOutOfRangeException)
        def fn():
            x = ArrayList()
            try:
                x.get_Item(0)
                return False
            except ArgumentOutOfRangeException:
                return True
        assert self.interpret(fn, []) == True

    def test_native_exception_superclass(self):
        SystemException = NativeException(CLR.System.Exception)
        def fn():
            x = ArrayList()
            try:
                x.get_Item(0)
                return False
            except SystemException:
                return True
        assert self.interpret(fn, []) == True

    def test_native_exception_object(self):
        SystemException = NativeException(CLR.System.Exception)
        def fn():
            x = ArrayList()
            try:
                x.get_Item(0)
                return "Impossible!"
            except SystemException, e:
                ex = native_exc(e)
                return ex.get_Message()
        res = self.ll_to_string(self.interpret(fn, []))
        assert res.startswith("Index is less than 0")

    def test_native_exception_invoke(self):
        TargetInvocationException = NativeException(CLR.System.Reflection.TargetInvocationException)
        def fn():
            x = ArrayList()
            t = x.GetType()
            meth = t.GetMethod('get_Item')
            args = init_array(System.Object, box(0))
            try:
                meth.Invoke(x, args)
                return "Impossible!"
            except TargetInvocationException, e:
                inner = native_exc(e).get_InnerException()
                message = str(inner.get_Message())
                return message
        res = self.ll_to_string(self.interpret(fn, []))
        assert res.startswith("Index is less than 0")

    def test_typeof(self):
        def fn():
            x = box(42)
            return x.GetType() ==  typeof(System.Int32)
        res = self.interpret(fn, [])
        assert res is True

    def test_typeof_pypylib(self):
        DelegateType = CLR.pypy.test.DelegateType_int__int_2
        def fn():
            return typeof(DelegateType) is not None
        res = self.interpret(fn, [])
        assert res is True

    def test_typeof_functype(self):
        # this test is overridden in TestPythonnet
        def fn():
            t = typeof(FUNCTYPE)
            return t.get_Name()
        res = self.interpret(fn, [])
        assert res.startswith('StaticMethod__')

    def test_clidowncast(self):
        def fn():
            a = ArrayList()
            b = ArrayList()
            a.Add(b)
            c = a.get_Item(0) # type of c is Object
            c = clidowncast(c, ArrayList)
            c.Add(None)
            return c.get_Item(0)
        res = self.interpret(fn, [])
        assert res is None

    def test_clidowncast_lltype(self):
        ARRAY_LIST = ArrayList._INSTANCE
        def fn():
            a = ArrayList()
            b = ArrayList()
            a.Add(b)
            c = a.get_Item(0) # type of c is Object
            c = clidowncast(c, ARRAY_LIST)
            c.Add(None)
            return c.get_Item(0)
        res = self.interpret(fn, [])
        assert res is None

    def test_mix_None_and_instance(self):
        def g(x):
            return x
        def fn(flag):
            if flag:
                x = None
            else:
                x = box(42)
            return g(x)
        res = self.interpret(fn, [1])
        assert res is None

    def test_box_unbox_instance(self):
        class Foo:
            pass
        def fn():
            obj = Foo()
            b_obj = box(obj)
            obj2 = unbox(b_obj, Foo)
            return obj is obj2
        res = self.interpret(fn, [])
        assert res is True

    def test_unbox_instance_fail(self):
        class Foo:
            pass
        def fn():
            b_obj = box(42)
            return unbox(b_obj, Foo)
        res = self.interpret(fn, [])
        assert res is None

    def test_box_unbox_ooinstance(self):
        A = ootype.Instance('A', ootype.ROOT, {'xx': ootype.Signed})
        def fn(flag):
            a = ootype.new(A)
            a.xx = 42
            b_obj = box(a)
            a2 = unbox(b_obj, A)
            return a2.xx
        res = self.interpret(fn, [True])
        assert res == 42

    def test_box_unbox_ooinstance_fail(self):
        A = ootype.Instance('A', ootype.ROOT, {'xx': ootype.Signed})
        def fn(flag):
            b_obj = System.Object()
            a2 = unbox(b_obj, A)
            return a2
        res = self.interpret(fn, [True])
        assert res is None

    def test_box_unbox_oorecord(self):
        A = ootype.Record({'xx': ootype.Signed})
        def fn(flag):
            a = ootype.new(A)
            a.xx = 42
            b_obj = box(a)
            a2 = unbox(b_obj, A)
            return a2.xx
        res = self.interpret(fn, [True])
        assert res == 42

    def test_instance_wrapping(self):
        class Foo:
            pass
        def fn():
            obj = Foo()
            x = ArrayList()
            x.Add(box(obj))
            obj2 = unbox(x.get_Item(0), Foo)
            return obj is obj2
        res = self.interpret(fn, [])
        assert res is True

    def test_compare_string_None(self):
        from pypy.rlib.nonconst import NonConstant
        def null():
            if NonConstant(True):
                return None
            else:
                return ""
        
        def fn():
            ttype = System.Type.GetType('Consts, mscorlib, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089')
            namespace = ttype.get_Namespace()
            if namespace is not None:
                return False
            else:
                return True
        res = self.interpret(fn, [], backendopt=False)
        assert res is True

    def test_delegate(self):
        class Foo:
            def __init__(self):
                self.x = 0
            def m(self, sender, args):
                self.x = 42

        def fn(flag):
            f = Foo()
            if flag:
                f.m(None, None)
            delegate = eventhandler(f.m)
            delegate.Invoke(None, None)
            return f.x
        res = self.interpret(fn, [False])
        assert res == 42

    def test_static_fields(self):
        DummyClass = CLR.pypy.test.DummyClass
        def fn():
            obj = System.Object()
            DummyClass.myfield = obj
            return DummyClass.myfield is obj
        res = self.interpret(fn, [])
        assert res

    def test_pypylib(self):
        def fn():
            return CLR.pypy.runtime.Utils.OOString(42, -1)
        res = self.interpret(fn, [])
        assert self.ll_to_string(res) == '42'

    def test_call_delegate(self):
        def build_fn():
            tInt = typeof(System.Int32)
            args = init_array(System.Type, tInt, tInt)
            meth = Utils.CreateDynamicMethod("add", tInt, args)
            il = meth.GetILGenerator()
            il.Emit(OpCodes.Ldarg_0)
            il.Emit(OpCodes.Ldarg_1)
            il.Emit(OpCodes.Add)
            il.Emit(OpCodes.Ret)
            myfunc = meth.CreateDelegate(typeof(FUNCTYPE))
            return myfunc

        def fn(x, y):
            myfunc = unbox(build_fn(), FUNCTYPE)
            a = myfunc(x, y)
            mytuple = (x, y)
            b = myfunc(*mytuple)
            return a+b
        res = self.interpret(fn, [10, 11])
        assert res == 42

    def test_bound_delegate(self):
        def build_fn():
            tObjArray = System.Type.GetType("System.Object[]")
            tInt = typeof(System.Int32)
            args = init_array(System.Type, tObjArray, tInt, tInt)
            meth = Utils.CreateDynamicMethod("add", tInt, args)
            il = meth.GetILGenerator()
            il.Emit(OpCodes.Ldarg_1)
            il.Emit(OpCodes.Ldarg_2)
            il.Emit(OpCodes.Add)
            il.Emit(OpCodes.Ret)
            array = new_array(System.Object, 0)
            myfunc = meth.CreateDelegate(typeof(FUNCTYPE), array)
            return myfunc

        def fn():
            myfunc = unbox(build_fn(), FUNCTYPE)
            return myfunc(30, 12)
        res = self.interpret(fn, [])
        assert res == 42

    def test_valuetype_field(self):
        class Foo:
            def __init__(self, x):
                self.x = x

        def fn():
            f = Foo(OpCodes.Add)
            return f
        self.interpret(fn, [])

    def test_fieldinfo_for_const(self):
        A = ootype.Instance('A', ootype.ROOT, {'xx': ootype.Signed})
        const = ootype.new(A)
        const.xx = 42
        def fn():
            fieldinfo = fieldinfo_for_const(const)
            obj = fieldinfo.GetValue(None)
            # get the 'xx' field by using reflection
            t = obj.GetType()
            x_info = t.GetField('xx')
            x_value = x_info.GetValue(obj)
            return unbox(x_value, ootype.Signed)
        res = self.interpret(fn, [])
        assert res == 42

    def test_fieldinfo_for_const_pbc(self):
        A = ootype.Instance('A', ootype.ROOT, {'xx': ootype.Signed})
        const = ootype.new(A)
        fieldinfo = fieldinfo_for_const(const)
        def fn():
            const.xx = 42
            obj = fieldinfo.GetValue(None)
            # get the 'xx' field by using reflection
            t = obj.GetType()
            x_info = t.GetField('xx')
            x_value = x_info.GetValue(obj)
            return unbox(x_value, ootype.Signed)
        res = self.interpret(fn, [])
        assert res == 42

    def test_classof(self):
        int32_class = classof(System.Int32)
        def fn():
            int32_obj = box(int32_class)
            int32_type = clidowncast(int32_obj, System.Type)
            return int32_type.get_Name()
        assert self.interpret(fn, []) == 'Int32'

    def test_classof_compare(self):
        int32_a = classof(System.Int32)
        int32_b = classof(System.Int32)
        def fn():
            return int32_a is int32_b
        assert self.interpret(fn, [])

    def test_classof_functype(self):
        # this test is overridden in TestPythonnet
        c = classof(FUNCTYPE)
        def fn():
            obj = box(c)
            t = clidowncast(obj, System.Type)
            return t.get_Name()
        res = self.interpret(fn, [])
        assert res.startswith('StaticMethod__')

    def test_mix_classof(self):
        a = classof(System.Int32)
        b = classof(FUNCTYPE)
        def fn(flag):
            if flag:
                x = a
            else:
                x = b
            return clidowncast(box(x), System.Type).get_Name()
        res = self.interpret(fn, [True])
        assert res == 'Int32'

    def test_cast_record(self):
        T = ootype.Record({'x': ootype.Signed})
        record = ootype.new(T)
        def fn(flag):
            if flag:
                obj = cast_record_to_object(record)
            else:
                obj = System.Object()
            record2 = cast_object_to_record(T, obj)
            return record is record2
        res = self.interpret(fn, [True])
        assert res

    def test_cast_record_pbc(self):
        T = ootype.Record({'x': ootype.Signed})
        record = ootype.new(T)
        record.x = 42
        obj = cast_record_to_object(record)
        def fn():
            record2 = cast_object_to_record(T, obj)
            return record is record2
        res = self.interpret(fn, [])
        assert res

    def test_cast_record_mix_object(self):
        T = ootype.Record({'x': ootype.Signed})
        NULL = ootype.null(System.Object._INSTANCE)
        record = cast_record_to_object(ootype.new(T))
        assert record != NULL
        assert NULL != record
        

class TestPythonnet(TestDotnetRtyping):
    # don't interpreter functions but execute them directly through pythonnet
    def interpret(self, f, args, backendopt='ignored'):
        return f(*args)

    def _skip_pythonnet(self, msg):
        py.test.skip(msg)

    def test_whitout_box(self):
        pass # it makes sense only during translation
        
    def test_typeof_functype(self):
        def fn():
            t = typeof(FUNCTYPE)
            return t.get_Name()
        res = self.interpret(fn, [])
        assert res == 'DelegateType_int__int_2'

    def test_classof_functype(self):
        # this test is overridden in TestPythonnet
        c = classof(FUNCTYPE)
        def fn():
            obj = box(c)
            t = clidowncast(obj, System.Type)
            return t.get_Name()
        res = self.interpret(fn, [])
        assert res == 'DelegateType_int__int_2'

    def test_fieldinfo_for_const(self):
        pass # it makes sense only during translation

    def test_fieldinfo_for_const_pbc(self):
        pass # it makes sense only during translation
