from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import meth, overload, Meth, StaticMethod
from pypy.translator.cli.dotnet import NativeInstance, CliClass, _overloaded_static_meth, _static_meth, CliNamespace


System = CliNamespace('System')
System.Text = CliNamespace('System.Text')
System.Collections = CliNamespace('System.Collections')

OBJECT = NativeInstance('[mscorlib]', 'System', 'Object', ootype.ROOT, {},
                        {'ToString': ootype.meth(ootype.Meth([], ootype.String)),
                         })
System.Object = CliClass(OBJECT, {})


MATH = NativeInstance('[mscorlib]', 'System', 'Math', OBJECT, {}, {})
System.Math = CliClass(MATH,
                       {'Abs': _overloaded_static_meth(_static_meth(StaticMethod([ootype.Signed], ootype.Signed)),
                                                       _static_meth(StaticMethod([ootype.Float], ootype.Float)))
                        })


CONSOLE = NativeInstance('[mscorlib]', 'System', 'Console', OBJECT, {}, {})
System.Console = CliClass(CONSOLE,
                          {'WriteLine': _overloaded_static_meth(_static_meth(StaticMethod([ootype.String], ootype.Void)),
                                                                _static_meth(StaticMethod([ootype.Signed], ootype.Void))),
                           })


STRING_BUILDER = NativeInstance('[mscorlib]', 'System.Text', 'StringBuilder', OBJECT, {}, {})
STRING_BUILDER._add_methods({'Append': meth(Meth([ootype.String], STRING_BUILDER)),
                             'AppendLine': overload(meth(Meth([ootype.String], STRING_BUILDER)),
                                                    meth(Meth([], STRING_BUILDER)))
                             })
System.Text.StringBuilder = CliClass(STRING_BUILDER, {})





ARRAY_LIST = NativeInstance('[mscorlib]', 'System.Collections', 'ArrayList', OBJECT, {},
                            {'Add': meth(Meth([OBJECT], ootype.Signed)),
                             'get_Count': meth(Meth([], ootype.Signed))})
System.Collections.ArrayList = CliClass(ARRAY_LIST, {})
