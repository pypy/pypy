import types
from ctypes import *

STRING = c_char_p

def log(msg):
    print msg
    pass


class T(object):
    def __init__(self, item):
        self.item = item
class Inst(T):  pass
class Ref(T):   pass
#class Ptr(T):   pass


class Cast(object):
    def __init__(self, cppfunc, item):
        self.cppfunc = cppfunc
        self.item    = item
class CppCast(Cast):    pass
#class PyCast(Cast):     pass


class _CTypesInfo(object):
    def __init__(self, ctypesname, cppname):
        self.ctypesname = ctypesname
        self.cppname    = cppname

_ctypesinfo = {
    None            : _CTypesInfo('None'       , 'void'),
    c_char          : _CTypesInfo('c_char'     , 'char'),
    c_byte          : _CTypesInfo('c_byte'     , 'char'),
    c_ubyte         : _CTypesInfo('c_ubyte'    , 'unsigned char'),
    c_short         : _CTypesInfo('c_short'    , 'short'),
    c_ushort        : _CTypesInfo('c_ushort'   , 'unsigned short'),
    c_int           : _CTypesInfo('c_int'      , 'int'),
    c_uint          : _CTypesInfo('c_uint'     , 'unsigned int'),
    c_long          : _CTypesInfo('c_long'     , 'long'),
    c_ulong         : _CTypesInfo('c_ulong'    , 'unsigned long'),
    c_longlong      : _CTypesInfo('c_longlong' , 'long long'),
    c_ulonglong     : _CTypesInfo('c_ulonglong', 'unsigned long long'),
    c_float         : _CTypesInfo('c_float'    , 'float'),
    c_double        : _CTypesInfo('c_double'   , 'double'),
    c_char_p        : _CTypesInfo('STRING'     , 'char*'),
    c_wchar_p       : _CTypesInfo('c_wchar_p'  , 'wchar_t*'),
    c_void_p        : _CTypesInfo('c_void_p'   , 'void*'),
    }

def _ctypes_type(t):
    if isinstance(t, Cast):
        t = t.item
    if t in _ctypesinfo:
        return _ctypesinfo[t].ctypesname
    if isinstance(t, Wclass):
        return t.name
    if isinstance(t, (Inst, Ref)) and isinstance(t.item, Wclass):
        return t.item.name
    raise TypeError('unknown type %s' % t)


def _cpp_type(t):
    if isinstance(t, Cast):
        t = t.item
    if t in _ctypesinfo:
        return _ctypesinfo[t].cppname
    if isinstance(t, Wclass):
        return t.name + '*'
    if isinstance(t, Inst):
        return t.item.name
    if isinstance(t, Ref) and isinstance(t.item, Wclass):
        return t.item.name + '&'
    raise TypeError('unknown type %s' % t)
h_type = _cpp_type


class _Witem(object):
    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)
        return self

    def header(self):
        pass

    def cpp(self):
        pass

    def py(self):
        pass

    def finish_declaration(self, parent_item):
        for item in self.items:
            item.finish_declaration(self)


class Wfunction(_Witem):
    def __init__(self, ret, name, param):
        super(Wfunction, self).__init__()
        self.ret   = ret
        self.name  = name
        self.param = param


class Wmethod(_Witem):
    def __init__(self, ret, name, param, defaults=[]):
        super(Wmethod, self).__init__()
        self.ret   = ret
        self.name  = name
        self.param = param
        self.defaults = defaults
        self._self_was_added = False

    def finish_declaration(self, parent_item):
        super(Wmethod, self).finish_declaration(parent_item)
        if not self._self_was_added and not isinstance(self, Wstaticmethod):
            self.param.insert(0, parent_item)
            self._self_was_added = True

    def _is_pyfunc(self):
        return '.' in self.name

    def _plain_name(self):
        if self._is_pyfunc():
            return self.name.split('.',1)[1]
        return self.name

    def _callee_name(self, namespace, funcname):
        if self._is_pyfunc():
            return self.name
        return '%s.%s_%s' % (namespace, funcname, self.name)


class Wstaticmethod(Wmethod):
    pass


class Wctor(Wmethod):    #Wrapped constructor
    #XXX I don't like the fact that the returntype needs to be specified.
    #    We need to somehow keep a link to the parent!
    #    (maybe set a parent attribute in the .add methods?)
    def __init__(self, ret, param, defaults=[], name='__init__'):
        #note: The order is different from Wmethod because name would seldomly be supplied.
        #      Probably this will only happen when a Python function should be called instead.
        super(Wctor, self).__init__(ret, name, param, defaults)


class Wclass(_Witem):
    def __init__(self, name, parents=[]):
        super(Wclass, self).__init__()
        self.name     = name
        self.parents  = parents
Enum = Wclass #XXX temporary hack


class Wglobal(_Witem):
    pass


class Wroot(_Witem):    #root wrapable object

    header_template = '''#ifndef __%(name)s_H__
#define __%(name)s_H__

%(includes)s
using namespace %(namespace)s;
#define TypeID int

#ifdef __cplusplus
extern "C" {
#endif

%(code)s

#ifdef __cplusplus
};
#endif

#endif  // __%(name)s_H__
'''

    cpp_template = '''// %(name)s.cpp

#include "lib%(name)s.h"

// Helper functions (mostly for casting returnvalues and parameters)
char* as_c_string(std::string str) {
    return (char*)str.c_str();
}

std::string as_std_string(char* p) {
    return std::string(p);
}

std::vector<GenericValue>   as_vector_GenericValue(GenericValue* gv) {
    std::vector<GenericValue>   gvv;
    gvv.push_back(*gv);
    return gvv;
}

%(code)s

// end of %(name)s.cpp
'''

    py_template = '''# %(name)s.py

from wrapper import Wrapper
from ctypes import *
%(includes)s

%(name)s = cdll.load('lib%(name)s.so')
STRING = c_char_p

%(code)s

# end of %(name)s.py
'''

    def __init__(self, name):
        super(Wroot, self).__init__()
        self.name     = name
        self.includes = []
        log('Creating %s module' % name)

    def include(self, include):
        self.includes.append(include)
        return self #to allow chaining

    def header(self):
        name = self.name
        code = ''

        includes = ''
        for include in self.includes:
            if include.endswith('.h'):
                includes += '#include "%s"\n' % include

        namespace = self.name   #XXX

        for item in self.items:
            if isinstance(item, Wglobal):
                continue
            code += '// %s\n' % item.name
            for method in item.items:
                if method._is_pyfunc():
                    continue
                restype  = h_type(method.ret)
                argtypes = [h_type(p) for p in method.param]
                if isinstance(method, Wctor):
                    del argtypes[0]
                code += '%s %s_%s(%s);\n' % (restype, item.name, method.name, ','.join(argtypes))
            code += '\n'

        return self.header_template % locals()

    def _casted_arg(self, i, arg):
        if isinstance(arg, CppCast):
            return '%s(P%d)' % (arg.cppfunc, i)
        return 'P%d' % i

    def cpp(self):
        name = self.name
        code = ''
        for item in self.items:
            if isinstance(item, Wglobal):
                continue
            code += '// %s\n' % item.name
            for method in item.items:
                if method._is_pyfunc():
                    continue
                restype  = _cpp_type(method.ret)
                param    = method.param[isinstance(method, Wctor):]
                argtypes = ['%s P%d' % (_cpp_type(p),i) for i,p in enumerate(param)]
                code += '%s %s_%s(%s) {\n' % (restype, item.name, method.name, ','.join(argtypes))
                #for i,p in enumerate(method.param):
                #    code += '    %s p%d = (%s)P%d;\n' % (_cpp_type(p), i, _cpp_type(p), i)
                retcast = '(%s)' % restype
                if isinstance(method.ret, CppCast):
                    retcast_pre  = '%s(' % method.ret.cppfunc
                    retcast_post = ')'
                else:
                    retcast_pre  = ''
                    retcast_post = ''
                if isinstance(method, Wstaticmethod):
                    args  = [self._casted_arg(i,p) for i,p in enumerate(method.param)]
                    code += '    return %s%s%s::%s(%s)%s;\n}\n\n' % \
                        (retcast, retcast_pre, item.name, method.name,
                         ','.join(args), retcast_post)
                elif isinstance(method, Wctor):
                    #args = [self._casted_arg(i+1,p) for i,p in enumerate(method.param[1:])]
                    args = [self._casted_arg(i,p) for i,p in enumerate(param)]
                    code += '    return %snew %s(%s)%s;\n}\n\n' % \
                        (retcast_pre, item.name, ','.join(args), retcast_post)
                else:
                    args = [self._casted_arg(i+1,p) for i,p in enumerate(method.param[1:])]
                    code += '    return %s%sP0->%s(%s)%s;\n}\n\n' % \
                        (retcast, retcast_pre, method.name,
                         ','.join(args), retcast_post)
            code += '\n'
        return self.cpp_template % locals()

    def py(self):
        name = self.name
        code = ''

        includes = ''
        for include in self.includes:
            if include.endswith('.py'):
                includes += 'import %s\n' % include[:-3]

        # output classes, methods, etc.
        for item in self.items:
            if isinstance(item, Wglobal):
                continue
            code += 'class %s(Wrapper):\n' % item.name
            for method in item.items:
                param = ['P%d' % i for i,p in enumerate(method.param)]
                plain_name  = method._plain_name()
                callee_name = method._callee_name(self.name, item.name)
                params = ''
                for i, p in enumerate(param):
                    if params:
                        params += ','
                    params += p
                    n = len(method.defaults) - len(param) + i
                    if n >= 0:
                        params += '=' + repr(method.defaults[n])
                if isinstance(method, Wctor):
                    #We made sure the header and cpp file constructors don't get the python 'self'.
                    #Now we have to make sure we only pass 'self' to python helpers.
                    code += '    def __init__(%s):\n' % params
                    code += '       P0.instance = %s(%s)\n' % (
                        callee_name, ','.join(param[not method._is_pyfunc():]))
                else:
                    code += '    def %s(%s):\n' % (plain_name, params)
                    code += '        return %s(%s)\n' % (
                        callee_name, ','.join(param))
                if isinstance(method, Wstaticmethod):
                    code += '    %s = staticmethod(%s)\n' % (plain_name, plain_name)
                code += '\n'
            if not item.items:
                code += '    pass\n\n'

        # output return and parameter (c)types
        for item in self.items:
            if isinstance(item, Wglobal):
                continue
            for method in item.items:
                if method._is_pyfunc():
                    continue
                n = int(isinstance(method, Wctor))
                restype  = _ctypes_type(method.ret)
                argtypes = ','.join([_ctypes_type(p) for p in method.param[n:]])
                if isinstance(method, Wstaticmethod):
                    im_func = ''
                else:
                    im_func = 'im_func.'
                code += 'llvm.%s_%s.restype  = %s\n'     % (
                    item.name, method.name, restype)
                code += 'llvm.%s_%s.argtypes = [%s]\n\n' % (
                    item.name, method.name, argtypes)

        return self.py_template % locals()

    def create_files(self):
        log('Creating ' + self.name + '.py')
        f = open(self.name + '.py', 'w')
        code = self.py()
        f.write(code)
        f.close()

        log('Creating lib' + self.name + '.h')
        f = open('lib' + self.name + '.h', 'w')
        code = self.header()
        f.write(code)
        f.close()

        log('Creating lib' + self.name + '.cpp')
        f = open('lib' + self.name + '.cpp', 'w')
        code = self.cpp()
        f.write(code)
        f.close()

    def create_library(self):
        from os import system
        system('python setup.py lib%s build_ext -i' % self.name)

    def create(self):
        self.finish_declaration(None)
        self.create_files()
        self.create_library()
