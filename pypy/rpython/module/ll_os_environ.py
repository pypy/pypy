import os, sys
from pypy.annotation import model as annmodel
from pypy.rpython.controllerentry import Controller
from pypy.rpython.extfunc import register_external
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import rposix

# ____________________________________________________________
#
# Annotation support to control access to 'os.environ' in the RPython program

class OsEnvironController(Controller):
    knowntype = os.environ.__class__

    def convert(self, obj):
        return None     # 'None' is good enough, there is only one os.environ

    def getitem(self, obj, key):
        # in the RPython program reads of 'os.environ[key]' are redirected here
        result = r_getenv(key)
        if result is None:
            raise KeyError
        return result

    def setitem(self, obj, key, value):
        # in the RPython program, 'os.environ[key] = value' is redirected here
        r_putenv(key, value)

    def delitem(self, obj, key):
        # in the RPython program, 'del os.environ[key]' is redirected here
        if r_getenv(key) is None:
            raise KeyError
        r_unsetenv(key)

    def get_keys(self, obj):
        # 'os.environ.keys' is redirected here - note that it's the getattr
        # that arrives here, not the actual method call!
        return r_envkeys

    def get_items(self, obj):
        # 'os.environ.items' is redirected here (not the actual method call!)
        return r_envitems

    def get_get(self, obj):
        # 'os.environ.get' is redirected here (not the actual method call!)
        return r_getenv

# ____________________________________________________________
#
# Lower-level interface: dummy placeholders and external registations

def r_getenv(name):
    just_a_placeholder     # should return None if name not found

os_getenv = rffi.llexternal('getenv', [rffi.CCHARP], rffi.CCHARP)

def getenv_llimpl(name):
    l_name = rffi.str2charp(name)
    l_result = os_getenv(l_name)
    if l_result:
        result = rffi.charp2str(l_result)
    else:
        result = None
    rffi.free_charp(l_name)
    return result

register_external(r_getenv, [str], annmodel.SomeString(can_be_None=True),
                  export_name='ll_os.ll_os_getenv',
                  llimpl=getenv_llimpl)

# ____________________________________________________________

def r_putenv(name, value):
    just_a_placeholder

class EnvKeepalive:
    pass
envkeepalive = EnvKeepalive()
envkeepalive.byname = {}

os_putenv = rffi.llexternal('putenv', [rffi.CCHARP], rffi.INT)

def putenv_llimpl(name, value):
    l_string = rffi.str2charp('%s=%s' % (name, value))
    error = rffi.cast(lltype.Signed, os_putenv(l_string))
    if error:
        rffi.free_charp(l_string)
        raise OSError(rposix.get_errno(), "os_putenv failed")
    # keep 'l_string' alive - we know that the C library needs it
    # until the next call to putenv() with the same 'name'.
    l_oldstring = envkeepalive.byname.get(name, lltype.nullptr(rffi.CCHARP.TO))
    envkeepalive.byname[name] = l_string
    if l_oldstring:
        rffi.free_charp(l_oldstring)

register_external(r_putenv, [str, str], annmodel.s_None,
                  export_name='ll_os.ll_os_putenv',
                  llimpl=putenv_llimpl)

# ____________________________________________________________

def r_unsetenv(name):
    # default implementation for platforms without a real unsetenv()
    r_putenv(name, '')

if hasattr(__import__(os.name), 'unsetenv'):

    if sys.platform.startswith('darwin'):
        RETTYPE = lltype.Void
        os_unsetenv = rffi.llexternal('unsetenv', [rffi.CCHARP], RETTYPE)
    else:
        RETTYPE = rffi.INT
        _os_unsetenv = rffi.llexternal('unsetenv', [rffi.CCHARP], RETTYPE)
        def os_unsetenv(l_name):
            return rffi.cast(lltype.Signed, _os_unsetenv(l_name))

    def unsetenv_llimpl(name):
        l_name = rffi.str2charp(name)
        error = os_unsetenv(l_name)     # 'error' is None on OS/X
        rffi.free_charp(l_name)
        if error:
            raise OSError(rposix.get_errno(), "os_unsetenv failed")
        try:
            l_oldstring = envkeepalive.byname[name]
        except KeyError:
            pass
        else:
            del envkeepalive.byname[name]
            rffi.free_charp(l_oldstring)

    register_external(r_unsetenv, [str], annmodel.s_None,
                      export_name='ll_os.ll_os_unsetenv',
                      llimpl=unsetenv_llimpl)

# ____________________________________________________________
# Access to the 'environ' external variable

from pypy.translator.tool.cbuild import ExternalCompilationInfo

if sys.platform.startswith('darwin'):
    CCHARPPP = rffi.CArrayPtr(rffi.CCHARPP)
    _os_NSGetEnviron = rffi.llexternal(
        '_NSGetEnviron', [], CCHARPPP,
        compilation_info=ExternalCompilationInfo(includes=['crt_externs.h'])
        )
    def os_get_environ():
        return _os_NSGetEnviron()[0]
elif sys.platform.startswith('win'):
    os_get_environ, _os_set_environ = rffi.CExternVariable(
        rffi.CCHARPP,
        '_environ',
        ExternalCompilationInfo(includes=['stdlib.h']))
else:
    os_get_environ, _os_set_environ = rffi.CExternVariable(rffi.CCHARPP,
                                                           'environ',
                                                           ExternalCompilationInfo())

# ____________________________________________________________

def r_envkeys():
    just_a_placeholder

def envkeys_llimpl():
    environ = os_get_environ()
    result = []
    i = 0
    while environ[i]:
        name_value = rffi.charp2str(environ[i])
        p = name_value.find('=')
        if p >= 0:
            result.append(name_value[:p])
        i += 1
    return result

register_external(r_envkeys, [], [str],   # returns a list of strings
                  export_name='ll_os.ll_os_envkeys',
                  llimpl=envkeys_llimpl)

# ____________________________________________________________

def r_envitems():
    just_a_placeholder

def envitems_llimpl():
    environ = os_get_environ()
    result = []
    i = 0
    while environ[i]:
        name_value = rffi.charp2str(environ[i])
        p = name_value.find('=')
        if p >= 0:
            result.append((name_value[:p], name_value[p+1:]))
        i += 1
    return result

register_external(r_envitems, [], [(str, str)],
                  export_name='ll_os.ll_os_envitems',
                  llimpl=envitems_llimpl)
