
import jpype
import atexit


class CallWrapper(object):    
    
    def wrap_item(self, item):
        if isinstance(item, jpype.java.lang.Object):
            return JavaInstanceWrapper(item)
        elif isinstance(item, jpype._jclass._JavaClass):
            return JavaInstanceWrapper(item.__javaclass__)
        elif isinstance(item, tuple) or isinstance(item, list):
            return self.wrap_list(item)
        return item

    def wrap_list(self, lst):
        return [self.wrap_item(x) for x in lst]

    def __call__(self, *args, **kwargs):
        result =  self.__wrapped__(*args, **kwargs)
        return self.wrap_item(result)


class JavaWrapper(CallWrapper):
    def __init__(self, name):
        self.__javaname__ = name
        all_names = name.split(".")
        temp_module = jpype
        for n in all_names:
            temp_module = getattr(temp_module, n)
        self.__wrapped__ = temp_module
    def __getattr__(self, attr):
        if isinstance(getattr(self.__wrapped__, attr), type):
            return JavaClassWrapper(getattr(self.__wrapped__, attr))
        elif isinstance(getattr(self.__wrapped__, attr), jpype.JPackage):
            return JavaWrapper(self.__javaname__ + '.' + attr)

class JavaInstanceWrapper(object):
    def __init__(self, obj):
        self.__wrapped__ = obj

    def __getattr__(self, attr):
        return JavaMethodWrapper(getattr(self.__wrapped__, attr))

class JavaClassWrapper(CallWrapper):
    def __init__(self, cls):
        self.__wrapped__ = cls

    def __getattr__(self, attr):
        result = None
        try:
            result = JavaStaticMethodWrapper(getattr(self.__wrapped__, attr))
        except AttributeError:
            result = JavaStaticMethodWrapper(getattr(self.__wrapped__.__javaclass__, attr))
        return result

class JavaMethodWrapper(CallWrapper):

    def __init__(self, meth):
        self.__wrapped__ = meth

class JavaStaticMethodWrapper(CallWrapper):
    def __init__(self, static_meth):
        self.__wrapped__ = static_meth
    


jpype.startJVM(jpype.getDefaultJVMPath(), "-ea")
java = JavaWrapper("java")
JavaMethod = type(jpype.java.lang.Math.abs)


def cleanup():
    jpype.shutdownJVM()

atexit.register(cleanup)


