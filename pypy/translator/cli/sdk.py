import os.path
import platform
import py

class AbstractSDK(object):
    def _check_helper(cls, helper):
        if py.path.local.sysfind(helper) is None:
            py.test.skip("%s is not on your path." % helper)
        else:
            return helper
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

    def peverify(cls):
        return cls._check_helper(cls.PEVERIFY)
    peverify = classmethod(peverify)

class MicrosoftSDK(AbstractSDK):
    RUNTIME = []
    ILASM = 'ilasm'    
    CSC = 'csc'
    PEVERIFY = 'peverify'

class MonoSDK(AbstractSDK):
    RUNTIME = ['mono']
    ILASM = 'ilasm2'
    CSC = 'gmcs'
    PEVERIFY = 'peverify' # it's not part of mono, but we get a meaningful skip message

def key_as_dict(handle):
    import _winreg
    i = 0
    res = {}
    while True:
        try:
            name, value, type_ = _winreg.EnumValue(handle, i)
            res[name] = value
            i += 1
        except WindowsError:
            break
    return res

def find_mono_on_windows():
    if platform.system() != 'Windows':
        return None
    import _winreg
    try:
        hMono = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "Software\\Novell\\Mono")
    except WindowsError: # mono seems not installed
        return None

    mono = key_as_dict(hMono)
    mono_version = mono.get('DefaultCLR', None)
    if mono_version is None:
        return None
    hMono.Close()

    hMono_data = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "Software\\Novell\\Mono\\%s" % mono_version)
    mono_data = key_as_dict(hMono_data)
    mono_dir = str(mono_data['SdkInstallRoot'])
    return os.path.join(mono_dir, 'bin')

def get_default_SDK():
    if platform.system() == 'Windows':
        SDK = MicrosoftSDK
        # if present, use mono ilasm2 instead of MS ilasm
        mono_bin = find_mono_on_windows()
        if mono_bin is not None:
            SDK.ILASM = os.path.join(mono_bin, 'ilasm2.bat')
    else:
        SDK = MonoSDK
    return SDK

SDK = get_default_SDK()
