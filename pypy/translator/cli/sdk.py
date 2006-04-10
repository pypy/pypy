import platform
import py

class AbstractSDK(object):
    @classmethod
    def _check_helper(cls, helper):
        try:
            py.path.local.sysfind(helper)
            return helper
        except py.error.ENOENT:
            py.test.skip("%s is not on your path." % helper)

    @classmethod
    def runtime(cls):
        for item in cls.RUNTIME:
            cls._check_helper(item)
        return cls.RUNTIME

    @classmethod
    def ilasm(cls):
        return cls._check_helper(cls.ILASM)

    @classmethod
    def csc(cls):
        return cls._check_helper(cls.CSC)

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
