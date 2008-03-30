import os
import platform

import py
from py.compat import subprocess
from pypy.tool.udir import udir
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.rpython.ootypesystem import ootype
from pypy.annotation.model import lltype_to_annotation
from pypy.translator.translator import TranslationContext
from pypy.translator.oosupport.support import patch_os, unpatch_os
from pypy.translator.jvm.genjvm import \
     generate_source_for_function, JvmError, detect_missing_support_programs
from pypy.translator.jvm.option import getoption

class StructTuple(tuple):
    def __getattr__(self, name):
        if name.startswith('item'):
            i = int(name[len('item'):])
            return self[i]
        else:
            raise AttributeError, name

# CLI duplicate
class OOList(list):
    def ll_length(self):
        return len(self)

    def ll_getitem_fast(self, i):
        return self[i]

# CLI duplicate
class ExceptionWrapper:
    def __init__(self, class_name):
        # We put all of our classes into some package like 'pypy':
        # strip the initial 'pypy.' that results from the class name,
        # and we append a number to make the class name unique. Strip
        # those.
        pkg = getoption('package')+'.'
        assert class_name.startswith(pkg)
        uniqidx = class_name.rindex('_')
        self.class_name = class_name[len(pkg):uniqidx]

    def __repr__(self):
        return 'ExceptionWrapper(%s)' % repr(self.class_name)

class InstanceWrapper:
    def __init__(self, class_name, fields):
        self.class_name = class_name
        # fields is a list of (name, value) tuples
        self.fields = fields

    def __repr__(self):
        return 'InstanceWrapper(%s, %r)' % (self.class_name, self.fields)

# CLI could-be duplicate
class JvmGeneratedSourceWrapper(object):
    def __init__(self, gensrc):
        """ gensrc is an instance of JvmGeneratedSource """
        self.gensrc = gensrc

    def run(self,*args):
        if not self.gensrc.compiled:
            py.test.skip("Assembly disabled")

        if getoption('norun'):
            py.test.skip("Execution disabled")

#        if self._exe is None:
#            py.test.skip("Compilation disabled")

#        if getoption('norun'):
#            py.test.skip("Execution disabled")

        stdout, stderr, retval = self.gensrc.execute(args)
        return stdout, stderr, retval
        
    def __call__(self, *args):
        if not self.gensrc.compiled:
            py.test.skip("Assembly disabled")

        if getoption('norun'):
            py.test.skip("Execution disabled")

        stdout, stderr, retval = self.gensrc.execute(args)
        res = eval(stdout.strip())
        if isinstance(res, tuple):
            res = StructTuple(res) # so tests can access tuple elements with .item0, .item1, etc.
        elif isinstance(res, list):
            res = OOList(res)
        elif isinstance(res, ExceptionWrapper):
            raise res            
        return res

class JvmTest(BaseRtypingTest, OORtypeMixin):

    FLOAT_PRECISION = 7
    
    def __init__(self):
        self._func = None
        self._ann = None
        self._jvm_src = None

    def compile(self, fn, args, ann=None, backendopt=False):
        if ann is None:
            ann = [lltype_to_annotation(typeOf(x)) for x in args]
        if self._func is fn and self._ann == ann:
            return JvmGeneratedSourceWrapper(self._jvm_src)
        else:
            self._func = fn
            self._ann = ann
            olddefs = patch_os()
            self._jvm_src = generate_source_for_function(fn, ann, backendopt)
            unpatch_os(olddefs)
            if not getoption('noasm'):
                self._jvm_src.compile()
            return JvmGeneratedSourceWrapper(self._jvm_src)

    def _skip_win(self, reason):
        if hasattr(platform, 'system') and platform.system() == 'Windows':
            py.test.skip('Windows --> %s' % reason)
            
    def _skip_powerpc(self, reason):
        if hasattr(platform, 'processor') and platform.processor() == 'powerpc':
            py.test.skip('PowerPC --> %s' % reason)

    def _skip_llinterpreter(self, reason, skipLL=True, skipOO=True):
        pass

    def interpret(self, fn, args, annotation=None):
        detect_missing_support_programs()
        try:
            src = self.compile(fn, args, annotation)
            res = src(*args)
            return res
        except JvmError, e:
            e.pretty_print()
            raise

    def interpret_raises(self, exception, fn, args):
        import exceptions # needed by eval
        try:
            self.interpret(fn, args)
        except ExceptionWrapper, ex:
            assert issubclass(eval(ex.class_name), exception)
        else:
            assert False, 'function did not raise any exception at all'

    def float_eq(self, x, y):
        return self.float_eq_approx(x, y)

    def is_of_type(self, x, type_):
        return True # we can't really test the type

    def ll_to_string(self, s):
        return s

    def ll_to_unicode(self, s):
        return s

    def ll_to_list(self, l):
        return l

    def ll_to_tuple(self, t):
        return t

    def class_name(self, value):
        return value.class_name.split(".")[-1] 

    def is_of_instance_type(self, val):
        return isinstance(val, InstanceWrapper)

    def read_attr(self, obj, name):
        py.test.skip("read_attr not supported on JVM")
        # TODO --- this "almost works": I think the problem is that our
        # dump methods don't dump fields of the super class??
        #return obj.fields["o"+name]
