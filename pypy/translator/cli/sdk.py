import platform
import py

class AbstractSDK(object):
    def _check_helper(cls, helper):
        try:
            py.path.local.sysfind(helper)
            return helper
        except py.error.ENOENT:
            py.test.skip("%s is not on your path." % helper)
    _check_helper = classmethod(_check_helper)

    def runtime(cls):
        for item in cls.RUNTIME:
            cls._check_helper(item)
        return cls.RUNTIME
    runtime = classmethod(runtime)

    def ilasm(cls):
        return cls._check_helper(cls.ILASM)
    ilasm = classmethod(ilasm)

    def csc(cls):
        return cls._check_helper(cls.CSC)
    csc = classmethod(csc)

class MicrosoftSDK(AbstractSDK):
    RUNTIME = []
    ILASM = 'ilasm'    
    CSC = 'csc'

class MonoSDK(AbstractSDK):
    RUNTIME = ['mono']
    ILASM = 'ilasm2'
    CSC = 'gmcs'

if platform.system() == 'Windows':
    SDK = MicrosoftSDK
else:
    SDK = MonoSDK
