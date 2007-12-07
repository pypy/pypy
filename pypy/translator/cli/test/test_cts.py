from pypy.translator.cli import cts

def test_primitive():
    void = cts.CliPrimitiveType('void')
    assert str(void) == void.typename() == 'void'
    assert void == cts.CliPrimitiveType('void')

def test_class():
    Math = cts.CliClassType('mscorlib', 'System.Math')
    assert str(Math) == Math.typename() == 'class [mscorlib]System.Math'
    assert Math.classname() == '[mscorlib]System.Math'
    assert Math == cts.CliClassType('mscorlib', 'System.Math')

def test_generic():
    Dict = cts.CliGenericType('mscorlib', 'System.Dict', 2)
    assert str(Dict) == Dict.typename() == 'class [mscorlib]System.Dict`2<!0, !1>'
    
    int32 = cts.CliPrimitiveType('int32')
    Math = cts.CliClassType('mscorlib', 'System.Math')
    MyDict = Dict.specialize(int32, Math)
    assert isinstance(MyDict, cts.CliSpecializedType)
    classname = '[mscorlib]System.Dict`2<int32, class [mscorlib]System.Math>'
    assert str(MyDict) == MyDict.typename() == 'class ' + classname
    assert MyDict.classname() == classname
