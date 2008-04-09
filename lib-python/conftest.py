"""

test configuration(s) for running CPython's regression
test suite on top of PyPy 

"""
import py
import sys
import pypy
from pypy.interpreter.gateway import ApplevelClass 
from pypy.interpreter.error import OperationError
from pypy.interpreter.module import Module as PyPyModule 
from pypy.interpreter.main import run_string, run_file

# the following adds command line options as a side effect! 
from pypy.conftest import gettestobjspace, option as pypy_option 
from test.regrtest import reportdiff
from test import pystone

from pypy.tool.pytest import appsupport 
from pypy.tool.pytest.confpath import pypydir, libpythondir, \
                                      regrtestdir, modregrtestdir, testresultdir
from pypy.tool.pytest.result import Result, ResultFromMime

pypyexecpath = pypydir.join('bin', 'pypy-c')

dist_rsync_roots = ['.', '../pypy', '../py']
    
# 
# Interfacing/Integrating with py.test's collection process 
#

# XXX no nice way to implement a --listpassing py.test option?! 
#option = py.test.addoptions("compliance testing options", 
#    py.test.Option('-L', '--listpassing', action="store", default=None, 
#                   type="string", dest="listpassing", 
#                   help="just display the list of expected-to-pass tests.")

Option = py.test.config.Option 
option = py.test.config.addoptions("compliance testing options", 
    Option('-C', '--compiled', action="store_true", 
           default=False, dest="use_compiled", 
           help="use a compiled version of pypy"),
    Option('--compiled-pypy', action="store", type="string", dest="pypy_executable",
           default=str(pypyexecpath),
           help="to use together with -C to specify the path to the "
                "compiled version of pypy, by default expected in pypy/bin/pypy-c"),
    Option('-E', '--extracttests', action="store_true", 
           default=False, dest="extracttests", 
           help="try to extract single tests and run them via py.test/PyPy"), 
    Option('-T', '--timeout', action="store", type="string", 
           default="100mp", dest="timeout", 
           help="fail a test module after the given timeout. "
                "specify in seconds or 'NUMmp' aka Mega-Pystones"),
    Option('--resultdir', action="store", type="string", 
           default=None, dest="resultdir", 
           help="directory under which to store results in USER@HOST subdirs",
           ),
    )

def gettimeout(): 
    timeout = option.timeout.lower()
    if timeout.endswith('mp'): 
        megapystone = float(timeout[:-2])
        t, stone = pystone.Proc0(10000)
        pystonetime = t/stone 
        seconds = megapystone  * 1000000 * pystonetime 
        return seconds 
    return float(timeout) 

def callex(space, func, *args, **kwargs): 
    try: 
        return func(*args, **kwargs) 
    except OperationError, e: 
        ilevelinfo = py.code.ExceptionInfo()
        if e.match(space, space.w_KeyboardInterrupt): 
            raise KeyboardInterrupt 
        appexcinfo = appsupport.AppExceptionInfo(space, e) 
        if appexcinfo.traceback: 
            print "appexcinfo.traceback:"
            py.std.pprint.pprint(appexcinfo.traceback)
            raise py.test.collect.Item.Failed(excinfo=appexcinfo) 
        raise py.test.collect.Item.Failed(excinfo=ilevelinfo) 

#
# compliance modules where we invoke test_main() usually call into 
# test_support.(run_suite|run_doctests) 
# we intercept those calls and use the provided information 
# for our collection process.  This allows us to run all the 
# tests one by one. 
#

app = ApplevelClass('''
    #NOT_RPYTHON  

    import unittest 
    from test import test_support   
    import sys

    def getmethods(suite_or_class): 
        """ flatten out suites down to TestCase instances/methods. """ 
        if isinstance(suite_or_class, unittest.TestCase): 
            res = [suite_or_class]
        elif isinstance(suite_or_class, unittest.TestSuite): 
            res = []
            for x in suite_or_class._tests: 
                res.extend(getmethods(x))
        elif isinstance(suite_or_class, list): 
            res = []
            for x in suite_or_class: 
                res.extend(getmethods(x))
        else: 
            raise TypeError, "expected TestSuite or TestClass, got %r"  %(suite_or_class) 
        return res 

    #
    # exported API 
    #

    def intercept_test_support(): 
        """ intercept calls to test_support.run_doctest and run_suite. 
            Return doctestmodules, suites which will hold collected
            items from these test_support invocations. 
        """
        suites = []
        doctestmodules = []
        def hack_run_doctest(module, verbose=None): 
            doctestmodules.append(module) 
        test_support.run_doctest = hack_run_doctest 

        def hack_run_suite(suite, testclass=None): 
            suites.append(suite) 
        test_support.run_suite = hack_run_suite 
        return suites, doctestmodules 

    def collect_intercepted(suites, doctestmodules): 
        namemethodlist = []
        for method in getmethods(suites): 
            name = (method.__class__.__name__ + '.' + 
                    method._TestCase__testMethodName)
            namemethodlist.append((name, method))
        doctestlist = []
        for mod in doctestmodules: 
            doctestlist.append((mod.__name__, mod))
        return namemethodlist, doctestlist 

    def run_testcase_method(method): 
        result = method.defaultTestResult() 
        method.run(result)
        if result.errors:
            assert len(result.errors)
            print result.errors[0][1]
        if result.failures:
            assert len(result.failures)
            print result.failures[0][1]
        if result.failures or result.errors:
            return 1

    def set_argv(filename): 
        sys.argv[:] = ['python', filename]
''') 

intercept_test_support = app.interphook('intercept_test_support')
collect_intercepted = app.interphook('collect_intercepted')
run_testcase_method = app.interphook('run_testcase_method')
set_argv = app.interphook('set_argv')

def start_intercept(space): 
    w_suites, w_doctestmodules = space.unpacktuple(intercept_test_support(space))
    return w_suites, w_doctestmodules 

def collect_intercept(space, w_suites, w_doctestmodules): 
    w_result = callex(space, collect_intercepted, space, w_suites, w_doctestmodules)
    w_namemethods, w_doctestlist = space.unpacktuple(w_result) 
    return w_namemethods, w_doctestlist 

class SimpleRunItem(py.test.collect.Item): 
    """ Run a module file and compare its output 
        to the expected output in the output/ directory. 
    """ 
    def call_capture(self, space, func, *args): 
        regrtest = self.parent.regrtest 
        oldsysout = sys.stdout 
        sys.stdout = capturesysout = py.std.cStringIO.StringIO() 
        try: 
            try: 
                res = regrtest.run_file(space) 
            except: 
                print capturesysout.getvalue()
                raise 
            else: 
                return res, capturesysout.getvalue()
        finally: 
            sys.stdout = oldsysout 
        
    def run(self): 
        # XXX integrate this into InterceptedRunModule
        #     but we want a py.test refactoring towards
        #     more autonomy of colitems regarding 
        #     their representations 
        regrtest = self.parent.regrtest
        space = gettestobjspace(usemodules=[])
        res, output = self.call_capture(space, regrtest.run_file, space)

        outputpath = regrtest.getoutputpath() 
        if outputpath: 
            # we want to compare outputs 
            # regrtest itself prepends the test_name to the captured output
            result = outputpath.purebasename + "\n" + output 
            expected = outputpath.read(mode='r') 
            if result != expected: 
                reportdiff(expected, result) 
                py.test.fail("output check failed: %s" % (self.fspath.basename,))
        if output: 
            print output, 

#
class InterceptedRunModule(py.test.collect.Module): 
    """ special handling for tests with a proper 'def test_main(): '
        definition invoking test_support.run_suite or run_unittest 
        (XXX add support for test_support.run_doctest). 
    """ 
    def __init__(self, name, parent, regrtest): 
        super(InterceptedRunModule, self).__init__(name, parent)
        self.regrtest = regrtest
        self.fspath = regrtest.getfspath()

    def _prepare(self): 
        if hasattr(self, 'name2item'): 
            return
        self.name2item = {}
        space = gettestobjspace(usemodules=self.regrtest.usemodules)
        if self.regrtest.dumbtest or self.regrtest.getoutputpath(): 
            self.name2item['output'] = SimpleRunItem('output', self) 
            return 

        tup = start_intercept(space) 
        self.regrtest.run_file(space)
        w_namemethods, w_doctestlist = collect_intercept(space, *tup) 

        # setup {name -> wrapped testcase method}
        for w_item in space.unpackiterable(w_namemethods): 
            w_name, w_method = space.unpacktuple(w_item) 
            name = space.str_w(w_name) 
            testitem = AppTestCaseMethod(name, parent=self, w_method=w_method) 
            self.name2item[name] = testitem

        # setup {name -> wrapped doctest module}
        for w_item in space.unpackiterable(w_doctestlist): 
            w_name, w_module = space.unpacktuple(w_item) 
            name = space.str_w(w_name) 
            testitem = AppDocTestModule(name, parent=self, w_module=w_module)
            self.name2item[name] = testitem 
       
    def run(self): 
        self._prepare() 
        keys = self.name2item.keys()
        keys.sort(lambda x,y: cmp(x.lower(), y.lower()))
        return keys 

    def join(self, name): 
        self._prepare() 
        try: 
            return self.name2item[name]
        except KeyError: 
            pass

class AppDocTestModule(py.test.collect.Item): 
    def __init__(self, name, parent, w_module): 
        super(AppDocTestModule, self).__init__(name, parent) 
        self.w_module = w_module 

    def run(self): 
        py.test.skip("application level doctest modules not supported yet.")
    
class AppTestCaseMethod(py.test.collect.Item): 
    def __init__(self, name, parent, w_method): 
        super(AppTestCaseMethod, self).__init__(name, parent) 
        self.space = gettestobjspace() 
        self.w_method = w_method 

    def run(self):      
        space = self.space
        filename = str(self.fspath) 
        callex(space, set_argv, space, space.wrap(filename))
        #space.call_function(self.w_method)
        w_res = callex(space, run_testcase_method, space, self.w_method) 
        if space.is_true(w_res):
            raise AssertionError(
        "testcase instance invociation raised errors, see stdoudt")

# ________________________________________________________________________
#
# classification of all tests files (this is ongoing work) 
#

class RegrTest: 
    """ Regression Test Declaration.""" 
    def __init__(self, basename, enabled=False, dumbtest=False,
                                 oldstyle=False, core=False,
                                 compiler=None, 
                                 usemodules = ''): 
        self.basename = basename 
        self.enabled = enabled 
        self.dumbtest = dumbtest 
        # we have to determine the value of oldstyle
        # lazily because at RegrTest() call time the command
        # line options haven't been parsed!
        self._oldstyle = oldstyle 
        self._usemodules = usemodules.split()
        self._compiler = compiler 
        self.core = core

    def oldstyle(self): 
        return self._oldstyle #or pypy_option.oldstyle 
    oldstyle = property(oldstyle)

    def usemodules(self):
        return self._usemodules #+ pypy_option.usemodules
    usemodules = property(usemodules)

    def compiler(self): 
        return self._compiler #or pypy_option.compiler 
    compiler = property(compiler)

    def getoptions(self): 
        l = []
        for name in 'oldstyle', 'core': 
            if getattr(self, name): 
                l.append(name)
        for name in self.usemodules: 
            l.append(name)
        return l 

    def ismodified(self): 
        return modregrtestdir.join(self.basename).check() 

    def getfspath(self): 
        fn = modregrtestdir.join(self.basename)
        if fn.check(): 
            return fn 
        fn = regrtestdir.join(self.basename)
        return fn 

    def getoutputpath(self): 
        p = modregrtestdir.join('output', self.basename).new(ext='')
        if p.check(file=1):
            return p
        p = regrtestdir.join('output', self.basename).new(ext='')
        if p.check(file=1): 
            return p 

    def _prepare(self, space): 
        # output tests sometimes depend on not running in
        # verbose mode 
        if not hasattr(self, '_prepared'): 
            if self.getoutputpath(): 
                space.appexec([], """(): 
                    from test import test_support
                    test_support.verbose = False
            """)
            self._prepared = True
            
    def run_file(self, space): 
        self._prepare(space)
        fspath = self.getfspath()
        assert fspath.check()
        if self.oldstyle: 
            space.enable_old_style_classes_as_default_metaclass() 
        try: 
            modname = fspath.purebasename 
            space.appexec([], '''():
                from test import %(modname)s
                m = %(modname)s
                if hasattr(m, 'test_main'):
                    m.test_main()
            ''' % locals())
        finally: 
            space.enable_new_style_classes_as_default_metaclass() 

testmap = [
    RegrTest('test___all__.py', enabled=True, core=True),
        # fixable
    RegrTest('test___future__.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test__locale.py', enabled=True),
    RegrTest('test_aepack.py', enabled=False),
    RegrTest('test_al.py', enabled=False, dumbtest=1),
    RegrTest('test_anydbm.py', enabled=True),
    RegrTest('test_applesingle.py', enabled=False),
    RegrTest('test_array.py', enabled=True, core=True, usemodules='struct'),
    RegrTest('test_asynchat.py', enabled=False, usemodules='thread'),
    RegrTest('test_atexit.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_audioop.py', enabled=False, dumbtest=1),
    RegrTest('test_augassign.py', enabled=True, core=True),
    RegrTest('test_base64.py', enabled=True),
    RegrTest('test_bastion.py', enabled=True, dumbtest=1),
    RegrTest('test_binascii.py', enabled=False),
        #rev 10840: 2 of 8 tests fail

    RegrTest('test_binhex.py', enabled=False),
        #rev 10840: 1 of 1 test fails

    RegrTest('test_binop.py', enabled=True, core=True),
    RegrTest('test_bisect.py', enabled=True, core=True),
    RegrTest('test_bool.py', enabled=True, core=True),
    RegrTest('test_bsddb.py', enabled=False),
    RegrTest('test_bsddb185.py', enabled=False),
    RegrTest('test_bsddb3.py', enabled=False),
    RegrTest('test_bufio.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_builtin.py', enabled=True, core=True),
    RegrTest('test_bz2.py', usemodules='bz2', enabled=True),
    RegrTest('test_calendar.py', enabled=True),
    RegrTest('test_call.py', enabled=True, core=True),
    RegrTest('test_capi.py', enabled=False, dumbtest=1),
    RegrTest('test_cd.py', enabled=False, dumbtest=1),
    RegrTest('test_cfgparser.py', enabled=False),
        #rev 10840: Uncaught interp-level exception:
        #File "pypy/objspace/std/fake.py", line 133, in setfastscope
        #raise UnwrapError('calling %s: %s' % (self.code.cpy_callable, e))
        #pypy.objspace.std.model.UnwrapError: calling <built-in function backslashreplace_errors>: cannot unwrap <UserW_ObjectObject() instance of <W_TypeObject(UnicodeError)>>

    RegrTest('test_cgi.py', enabled=True),
    RegrTest('test_charmapcodec.py', enabled=True, core=True),
    RegrTest('test_cl.py', enabled=False, dumbtest=1),
    RegrTest('test_class.py', enabled=True, oldstyle=True, core=True),
    RegrTest('test_cmath.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_codeccallbacks.py', enabled=True, core=True),
    RegrTest('test_codecencodings_cn.py', enabled=False),
    RegrTest('test_codecencodings_hk.py', enabled=False),
    RegrTest('test_codecencodings_jp.py', enabled=False),
    RegrTest('test_codecencodings_kr.py', enabled=False),
    RegrTest('test_codecencodings_tw.py', enabled=False),

    RegrTest('test_codecmaps_cn.py', enabled=False),
    RegrTest('test_codecmaps_hk.py', enabled=False),
    RegrTest('test_codecmaps_jp.py', enabled=False),
    RegrTest('test_codecmaps_kr.py', enabled=False),
    RegrTest('test_codecmaps_tw.py', enabled=False),
    RegrTest('test_codecs.py', enabled=True, core=True),
    RegrTest('test_codeop.py', enabled=True, core=True),
    RegrTest('test_coercion.py', enabled=True, oldstyle=True, core=True),
    
    RegrTest('test_colorsys.py', enabled=True),
    RegrTest('test_commands.py', enabled=True),
    RegrTest('test_compare.py', enabled=True, oldstyle=True, core=True),
    RegrTest('test_compile.py', enabled=True, core=True),
    RegrTest('test_compiler.py', enabled=True, core=False), # this test tests the compiler package from stdlib
    RegrTest('test_complex.py', enabled=True, core=True),

    RegrTest('test_contains.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_cookie.py', enabled=False),
    RegrTest('test_cookielib.py', enabled=False),
    RegrTest('test_copy.py', enabled=True, core=True),
    RegrTest('test_copy_reg.py', enabled=True, core=True),
    RegrTest('test_cpickle.py', enabled=True, core=True),
    RegrTest('test_crypt.py', usemodules='crypt', enabled=False, dumbtest=1),
    RegrTest('test_csv.py', enabled=False),
        #rev 10840: ImportError: _csv

    RegrTest('test_curses.py', enabled=False, dumbtest=1),
    RegrTest('test_datetime.py', enabled=True),
    RegrTest('test_dbm.py', enabled=False, dumbtest=1),
    RegrTest('test_decimal.py', enabled=True),
    RegrTest('test_decorators.py', enabled=True, core=True),
    RegrTest('test_deque.py', enabled=True, core=True),
    RegrTest('test_descr.py', enabled=True, core=True, oldstyle=True, usemodules='_weakref'),
    RegrTest('test_descrtut.py', enabled=True, core=True, oldstyle=True),
    RegrTest('test_dict.py', enabled=True, core=True),

    RegrTest('test_difflib.py', enabled=True, dumbtest=1),
    RegrTest('test_dircache.py', enabled=True, core=True),
    RegrTest('test_dis.py', enabled=True),
    RegrTest('test_distutils.py', enabled=True),
    RegrTest('test_dl.py', enabled=False, dumbtest=1),
    RegrTest('test_doctest.py', usemodules="thread", enabled=True),
    RegrTest('test_doctest2.py', enabled=True),
    RegrTest('test_dumbdbm.py', enabled=True),
    RegrTest('test_dummy_thread.py', enabled=True, core=True),
    RegrTest('test_dummy_threading.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_email.py', enabled=False),
        #rev 10840: Uncaught interp-level exception

    RegrTest('test_email_codecs.py', enabled=False, dumbtest=1),
    RegrTest('test_enumerate.py', enabled=True, core=True),
    RegrTest('test_eof.py', enabled=True, core=True),

    RegrTest('test_errno.py', enabled=True, dumbtest=1),
    RegrTest('test_exceptions.py', enabled=True, core=True),
    RegrTest('test_extcall.py', enabled=True, core=True),
    RegrTest('test_fcntl.py', enabled=False, dumbtest=1, usemodules='fcntl'),
    RegrTest('test_file.py', enabled=True, dumbtest=1, usemodules="posix", core=True),
    RegrTest('test_filecmp.py', enabled=True, core=True),
    RegrTest('test_fileinput.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_fnmatch.py', enabled=True, core=True),
    RegrTest('test_fork1.py', enabled=False, dumbtest=1),
    RegrTest('test_format.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_fpformat.py', enabled=True, core=True),
    RegrTest('test_frozen.py', enabled=False),
    RegrTest('test_funcattrs.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_future.py', enabled=True, core=True),
    RegrTest('test_future1.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_future2.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_future3.py', enabled=True, core=True),
    RegrTest('test_gc.py', enabled=True, dumbtest=1, usemodules='_weakref'),
    RegrTest('test_gdbm.py', enabled=False, dumbtest=1),
    RegrTest('test_generators.py', enabled=True, core=True, usemodules='thread _weakref'),
        #rev 10840: 30 of 152 tests fail
    RegrTest('test_genexps.py', enabled=True, core=True, usemodules='_weakref'),
    RegrTest('test_getargs.py', enabled=False, dumbtest=1),
    RegrTest('test_getargs2.py', enabled=False),
        #rev 10840: ImportError: _testcapi

    RegrTest('test_getopt.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_gettext.py', enabled=False),
        #rev 10840: 28 of 28 tests fail

    RegrTest('test_gl.py', enabled=False, dumbtest=1),
    RegrTest('test_glob.py', enabled=True, core=True),
    RegrTest('test_global.py', enabled=True, core=True, compiler='ast'),
    RegrTest('test_grammar.py', enabled=True, core=True),
    RegrTest('test_grp.py', enabled=False),
        #rev 10840: ImportError: grp

    RegrTest('test_gzip.py', enabled=False, dumbtest=1),
    RegrTest('test_hash.py', enabled=True, core=True),
    RegrTest('test_heapq.py', enabled=True, core=True),
    RegrTest('test_hexoct.py', enabled=True, core=True),
    RegrTest('test_hmac.py', enabled=True),
    RegrTest('test_hotshot.py', enabled=False),
        #rev 10840: ImportError: _hotshot

    RegrTest('test_htmllib.py', enabled=True),
    RegrTest('test_htmlparser.py', enabled=True),
    RegrTest('test_httplib.py', enabled=True),
    RegrTest('test_imageop.py', enabled=False, dumbtest=1),
    RegrTest('test_imaplib.py', enabled=True, dumbtest=1),
    RegrTest('test_imgfile.py', enabled=False, dumbtest=1),
    RegrTest('test_imp.py', enabled=True, core=True, usemodules='thread'),
    RegrTest('test_import.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_importhooks.py', enabled=True, core=True),
    RegrTest('test_inspect.py', enabled=True, dumbtest=1),
    RegrTest('test_ioctl.py', enabled=False),
    RegrTest('test_isinstance.py', enabled=True, core=True),
    RegrTest('test_iter.py', enabled=True, core=True),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser
    RegrTest('test_iterlen.py', enabled=True, core=True),
    RegrTest('test_itertools.py', enabled=True, core=True),
        # modified version in pypy/lib/test2

    RegrTest('test_largefile.py', enabled=True, dumbtest=1),
    RegrTest('test_linuxaudiodev.py', enabled=False),
    RegrTest('test_list.py', enabled=True, core=True),
    RegrTest('test_locale.py', enabled=False, dumbtest=1),
    RegrTest('test_logging.py', enabled=False, usemodules='thread'),
    RegrTest('test_long.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_long_future.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_longexp.py', enabled=True, core=True),
    RegrTest('test_macfs.py', enabled=False),
    RegrTest('test_macostools.py', enabled=False),
    RegrTest('test_macpath.py', enabled=True),
    RegrTest('test_mailbox.py', enabled=True),
    RegrTest('test_marshal.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_math.py', enabled=True, core=True, usemodules='math'),
    RegrTest('test_md5.py', enabled=False),
    RegrTest('test_mhlib.py', enabled=True),
    RegrTest('test_mimetools.py', enabled=True),
    RegrTest('test_mimetypes.py', enabled=True),
    RegrTest('test_MimeWriter.py', enabled=True, core=False),
    RegrTest('test_minidom.py', enabled=False, dumbtest=1),
    RegrTest('test_mmap.py', enabled=False),
    RegrTest('test_module.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_multibytecodec.py', enabled=True),
    RegrTest('test_multibytecodec_support.py', enabled=True, core=True),
    RegrTest('test_multifile.py', enabled=True),
    RegrTest('test_mutants.py', enabled=True, dumbtest=1, core="possibly"),
    RegrTest('test_netrc.py', enabled=True),
    RegrTest('test_new.py', enabled=True, core=True, oldstyle=True),
    RegrTest('test_nis.py', enabled=False),
    RegrTest('test_normalization.py', enabled=False),
    RegrTest('test_ntpath.py', enabled=True, dumbtest=1),
    RegrTest('test_opcodes.py', enabled=True, core=True),
    RegrTest('test_openpty.py', enabled=False),
    RegrTest('test_operations.py', enabled=True, core=True),
    RegrTest('test_operator.py', enabled=True, core=True),
    RegrTest('test_optparse.py', enabled=False),
        # this test fails because it expects that PyPy's builtin
        # functions act as if they are staticmethods that can be put 
        # on classes and don't get bound etc.pp. 

    RegrTest('test_os.py', enabled=True, core=True),
    RegrTest('test_ossaudiodev.py', enabled=False),
    RegrTest('test_parser.py', enabled=True, core=True),
        #rev 10840: 18 of 18 tests fail

    RegrTest('test_peepholer.py', enabled=True),
    RegrTest('test_pep247.py', enabled=False, dumbtest=1),
    RegrTest('test_pep263.py', enabled=True, dumbtest=1),
    RegrTest('test_pep277.py', enabled=False),
        # XXX this test is _also_ an output test, damn it 
        #     seems to be the only one that invokes run_unittest 
        #     and is an unittest 
    RegrTest('test_pep292.py', enabled=True),
    RegrTest('test_pickle.py', enabled=True, core=True),
    RegrTest('test_pickletools.py', enabled=True, dumbtest=1, core=False),
    RegrTest('test_pkg.py', enabled=True, core=True),
    RegrTest('test_pkgimport.py', enabled=True, core=True),
    RegrTest('test_plistlib.py', enabled=False),
    RegrTest('test_poll.py', enabled=False),
    RegrTest('test_popen.py', enabled=True),
    RegrTest('test_popen2.py', enabled=True),
    RegrTest('test_posix.py', enabled=True),
    RegrTest('test_posixpath.py', enabled=True),
    RegrTest('test_pow.py', enabled=True, core=True),
    RegrTest('test_pprint.py', enabled=True, core=True),
    RegrTest('test_profile.py', enabled=True),
    RegrTest('test_profilehooks.py', enabled=True, core=True),
    RegrTest('test_pty.py', enabled=False),
    RegrTest('test_pwd.py', enabled=False),
        #rev 10840: ImportError: pwd

    RegrTest('test_pyclbr.py', enabled=False),
    RegrTest('test_pyexpat.py', enabled=False),
    RegrTest('test_queue.py', enabled=False, dumbtest=1),
    RegrTest('test_quopri.py', enabled=True),
    RegrTest('test_random.py', enabled=False),
        #rev 10840: Uncaught app-level exception:
        #class WichmannHill_TestBasicOps(TestBasicOps):
        #File "test_random.py", line 125 in WichmannHill_TestBasicOps
        #gen = random.WichmannHill()
        #AttributeError: 'module' object has no attribute 'WichmannHill'

    RegrTest('test_re.py', enabled=True, core=True),

    RegrTest('test_regex.py', enabled=False),
    RegrTest('test_repr.py', enabled=True, oldstyle=True, core=True),
        #rev 10840: 6 of 12 tests fail. Always minor stuff like
        #'<function object at 0x40db3e0c>' != '<built-in function hash>'

    RegrTest('test_resource.py', enabled=False),
    RegrTest('test_rfc822.py', enabled=True),
    RegrTest('test_rgbimg.py', enabled=False),
    RegrTest('test_richcmp.py', enabled=True, core=True),
        #rev 10840: 1 of 11 test fails. The failing one had an infinite recursion.

    RegrTest('test_robotparser.py', enabled=True),
    RegrTest('test_sax.py', enabled=False, dumbtest=1),
    RegrTest('test_scope.py', enabled=True, core=True),
    RegrTest('test_scriptpackages.py', enabled=False),
    RegrTest('test_select.py', enabled=False, dumbtest=1),
    RegrTest('test_set.py', enabled=True, core=True),
    RegrTest('test_sets.py', enabled=True),
    RegrTest('test_sgmllib.py', enabled=True),
    RegrTest('test_sha.py', enabled=True),
        # one test is taken out (too_slow_test_case_3), rest passses 
    RegrTest('test_shelve.py', enabled=True),
    RegrTest('test_shlex.py', enabled=True),
    RegrTest('test_shutil.py', enabled=True),
    RegrTest('test_signal.py', enabled=False),
    RegrTest('test_site.py', enabled=False, core=False), # considered cpython impl-detail 
        # Needs non-faked codecs.
    RegrTest('test_slice.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_socket.py', enabled=False, usemodules='thread _weakref'),

    RegrTest('test_socket_ssl.py', enabled=False),
    RegrTest('test_socketserver.py', enabled=False, usemodules='thread'),

    RegrTest('test_softspace.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_sort.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_str.py', enabled=True, core=True),
        #rev 10840: at least two tests fail, after several hours I gave up waiting for the rest

    RegrTest('test_strftime.py', enabled=False, dumbtest=1),
    RegrTest('test_string.py', enabled=True, core=True),
    RegrTest('test_StringIO.py', enabled=True, core=True),
    RegrTest('test_stringprep.py', enabled=True, dumbtest=1),
    RegrTest('test_strop.py', enabled=False),
        #rev 10840: ImportError: strop

    RegrTest('test_strptime.py', enabled=False),
        #rev 10840: 1 of 42 test fails: seems to be some regex problem

    RegrTest('test_struct.py', enabled=True, dumbtest=1, usemodules='struct'),
    RegrTest('test_structseq.py', enabled=False, dumbtest=1),
    RegrTest('test_subprocess.py', enabled=False, usemodules='signal'),
    RegrTest('test_sunaudiodev.py', enabled=False, dumbtest=1),
    RegrTest('test_sundry.py', enabled=False, dumbtest=1),
    # test_support is not a test
    RegrTest('test_symtable.py', enabled=False, dumbtest=1),
    RegrTest('test_syntax.py', enabled=True, core=True),
    RegrTest('test_sys.py', enabled=True, core=True),
    RegrTest('test_tcl.py', enabled=False),
    RegrTest('test_tarfile.py', enabled=False),
        #rev 10840: 13 of 13 test fail

    RegrTest('test_tempfile.py', enabled=False),
        # tempfile does: class ...         unlink = _os.unlink!!!
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    RegrTest('test_textwrap.py', enabled=True),
    RegrTest('test_thread.py', enabled=True, usemodules="thread", core=True),
    RegrTest('test_threaded_import.py', usemodules="thread", enabled=True, core=True),
    RegrTest('test_threadedtempfile.py', 
             usemodules="thread", enabled=True, core=False), # tempfile is non-core by itself 
        #rev 10840: ImportError: thread

    RegrTest('test_threading.py', usemodules="thread", enabled=True, dumbtest=1, core=True),
        #rev 10840: ImportError: thread
    RegrTest('test_threading_local.py', usemodules="thread", enabled=True, dumbtest=1, core=True),
    RegrTest('test_threadsignals.py', usemodules="thread", enabled=False, dumbtest=1),

    RegrTest('test_time.py', enabled=True, core=True),
    RegrTest('test_timeout.py', enabled=False),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    RegrTest('test_timing.py', enabled=False, dumbtest=1),
    RegrTest('test_tokenize.py', enabled=False),
    RegrTest('test_trace.py', enabled=True, core=True),
    RegrTest('test_traceback.py', enabled=True, core=True),
        #rev 10840: 2 of 2 tests fail
    RegrTest('test_transformer.py', enabled=True, core=True),
    RegrTest('test_tuple.py', enabled=True, core=True),

    RegrTest('test_types.py', enabled=True, core=True),
        #rev 11598: one of the mod related to dict iterators is questionable
        # and questions whether how we implement them is meaningful in the
        # long run
        
    RegrTest('test_ucn.py', enabled=False),
    RegrTest('test_unary.py', enabled=True, core=True),
    RegrTest('test_unicode.py', enabled=True, core=True),
    RegrTest('test_unicode_file.py', enabled=False),
    RegrTest('test_unicodedata.py', enabled=False),
    RegrTest('test_unittest.py', enabled=True, core=True),
    RegrTest('test_univnewlines.py', enabled=True, core=True),
    RegrTest('test_unpack.py', enabled=True, dumbtest=1, core=True),
    RegrTest('test_urllib.py', enabled=True),
    RegrTest('test_urllib2.py', enabled=True, dumbtest=1),
    RegrTest('test_urllib2net.py', enabled=True),
    RegrTest('test_urllibnet.py', enabled=False),
        # try to understand failure!!!
    RegrTest('test_urlparse.py', enabled=True),
    RegrTest('test_userdict.py', enabled=True, core=True),
    RegrTest('test_userlist.py', enabled=True, core=True),
    RegrTest('test_userstring.py', enabled=True, core=True),
    RegrTest('test_uu.py', enabled=False),
        #rev 10840: 1 of 9 test fails

    RegrTest('test_warnings.py', enabled=True, core=True),
    RegrTest('test_wave.py', enabled=False, dumbtest=1),
    RegrTest('test_weakref.py', enabled=True, core=True, usemodules='_weakref'),

    RegrTest('test_whichdb.py', enabled=True),
    RegrTest('test_winreg.py', enabled=False),
    RegrTest('test_winsound.py', enabled=False),
    RegrTest('test_xmllib.py', enabled=False),
    RegrTest('test_xmlrpc.py', enabled=False),
        #rev 10840: 2 of 5 tests fail

    RegrTest('test_xpickle.py', enabled=False),
    RegrTest('test_xrange.py', enabled=True, core=True),
    RegrTest('test_zipfile.py', enabled=False, dumbtest=1),
    RegrTest('test_zipimport.py', enabled=True, usemodules='zlib zipimport'),
    RegrTest('test_zlib.py', enabled=True, usemodules='zlib'),
]

class RegrDirectory(py.test.collect.Directory): 
    """ The central hub for gathering CPython's compliance tests
        Basically we work off the above 'testmap' 
        which describes for all test modules their specific 
        type.  XXX If you find errors in the classification 
        please correct them! 
    """ 
    def get(self, name, cache={}): 
        if not cache: 
            for x in testmap: 
                cache[x.basename] = x
        return cache.get(name, None)
        
    def run(self): 
        return [x.basename for x in testmap]

    def join(self, name): 
        regrtest = self.get(name) 
        if regrtest is not None: 
            if not option.extracttests:  
                return RunFileExternal(name, parent=self, regrtest=regrtest) 
            else: 
                return InterceptedRunModule(name, self, regrtest) 

Directory = RegrDirectory


def getrev(path): 
    try: 
        return py.path.svnwc(pypydir).info().rev
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        # on windows people not always have 'svn' in their path
        # but there are also other kinds of problems that
        # could occur and we just default to revision
        # "unknown" for them
        return 'unknown'  

def getexecutable(_cache={}):
    execpath = py.path.local(option.pypy_executable)
    if not _cache:
        text = execpath.sysexec('-c', 
            'import sys; '
            'print sys.version; '
            'print sys.pypy_svn_url; '
            'print sys.pypy_translation_info; ')
        lines = [line.strip() for line in text.split('\n')]
        assert len(lines) == 4 and lines[3] == ''
        assert lines[2].startswith('{') and lines[2].endswith('}')
        info = eval(lines[2])
        info['version'] = lines[0]
        info['rev'] = eval(lines[1])[1]
        _cache.update(info)
    return execpath, _cache

class RunFileExternal(py.test.collect.Module): 
    def __init__(self, name, parent, regrtest): 
        super(RunFileExternal, self).__init__(name, parent) 
        self.regrtest = regrtest 
        self.fspath = regrtest.getfspath()

    def tryiter(self, stopitems=()): 
        # shortcut pre-counting of items 
        return []

    def run(self): 
        if self.regrtest.ismodified(): 
            return ['modified']
        return ['unmodified']

    def join(self, name): 
        return ReallyRunFileExternal(name, parent=self) 


def ensuretestresultdir():
    resultdir = option.resultdir
    default_place = False
    if resultdir is not None:
        resultdir = py.path.local(option.resultdir)
    else:
        if option.use_compiled:
            return None
        default_place = True
        resultdir = testresultdir
        
    if not resultdir.check(dir=1):
        if default_place:
            py.test.skip("""'testresult' directory not found.
                 To run tests in reporting mode (without -E), you first have to
                 check it out as follows: 
                 svn co http://codespeak.net/svn/pypy/testresult %s""" % (
                testresultdir, ))
        else:
            py.test.skip("'%s' test result dir not found" % resultdir)
    return resultdir 

#
# testmethod: 
# invoking in a seprate process: py.py TESTFILE
#
import os
import time
import socket
import getpass

class ReallyRunFileExternal(py.test.collect.Item): 
    _resultcache = None
    def _haskeyword(self, keyword): 
        if keyword == 'core': 
            return self.parent.regrtest.core 
        if keyword not in ('error', 'ok', 'timeout'): 
            return super(ReallyRunFileExternal, self).haskeyword(keyword)
        if self._resultcache is None: 
            from pypy.tool.pytest.overview import ResultCache
            self.__class__._resultcache = rc = ResultCache() 
            rc.parselatest()
        result = self._resultcache.getlatestrelevant(self.fspath.purebasename)
        if not result: return False
        if keyword == 'timeout': return result.istimeout()
        if keyword == 'error': return result.iserror()
        if keyword == 'ok': return result.isok()
        assert False, "should not be there" 

    def getinvocation(self, regrtest): 
        fspath = regrtest.getfspath() 
        python = sys.executable 
        pypy_script = pypydir.join('bin', 'py.py')
        alarm_script = pypydir.join('tool', 'alarm.py')
        watchdog_script = pypydir.join('tool', 'watchdog.py')

        regr_script = pypydir.join('tool', 'pytest', 
                                   'run-script', 'regrverbose.py')
        
        if option.use_compiled:
            execpath, info = getexecutable()        
        pypy_options = []
        if regrtest.oldstyle: 
            if (option.use_compiled and
                not info.get('objspace.std.oldstyle', False)):
                py.test.skip("old-style classes not available with this pypy-c")
            pypy_options.append('--oldstyle') 
        if regrtest.compiler:
            pypy_options.append('--compiler=%s' % regrtest.compiler)
        pypy_options.extend(
            ['--withmod-%s' % mod for mod in regrtest.usemodules])
        sopt = " ".join(pypy_options) 
        # we use the regrverbose script to run the test, but don't get
        # confused: it still doesn't set verbose to True by default if
        # regrtest.outputpath() is true, because output tests get confused
        # in verbose mode.  You can always force verbose mode by passing
        # the -v option to py.test.  The regrverbose script contains the
        # logic that CPython uses in its regrtest.py.
        regrrun = str(regr_script)
        if not regrtest.getoutputpath() or pypy_option.verbose:
            regrrun_verbosity = '1'
        else:
            regrrun_verbosity = '0'
        
        TIMEOUT = gettimeout()
        if option.use_compiled:
            cmd = "%s %s %s %s" %(
                execpath, 
                regrrun, regrrun_verbosity, fspath.purebasename)
            if sys.platform != 'win32':
                cmd = "%s %s %s %s" %(
                       python, watchdog_script, TIMEOUT,
                       cmd)
        else:
            cmd = "%s %s %d %s %s %s %s %s" %(
                python, alarm_script, TIMEOUT, 
                pypy_script, sopt, 
                regrrun, regrrun_verbosity, fspath.purebasename)
        return cmd 

    def run(self): 
        """ invoke a subprocess running the test file via PyPy. 
            record its output into the 'result/user@host' subdirectory. 
            (we might want to create subdirectories for 
            each user, because we will probably all produce 
            such result runs and they will not be the same
            i am afraid. 
        """ 
        regrtest = self.parent.regrtest
        result = self.getresult(regrtest) 
        testresultdir = ensuretestresultdir()
        if testresultdir is not None:
            resultdir = testresultdir.join(result['userhost'])
            assert resultdir.ensure(dir=1)

            fn = resultdir.join(regrtest.basename).new(ext='.txt') 
            if result.istimeout(): 
                if fn.check(file=1): 
                    try: 
                        oldresult = ResultFromMime(fn)
                    except TypeError: 
                        pass
                    else: 
                        if not oldresult.istimeout(): 
                            py.test.skip("timed out, not overwriting "
                                         "more interesting non-timeout outcome")
            
            fn.write(result.repr_mimemessage().as_string(unixfrom=False))
            
        if result['exit-status']:  
             time.sleep(0.5)   # time for a Ctrl-C to reach us :-)
             print >>sys.stdout, result.getnamedtext('stdout') 
             print >>sys.stderr, result.getnamedtext('stderr') 
             py.test.fail("running test failed, see stderr output below") 

    def getstatusouterr(self, cmd): 
        tempdir = py.path.local.mkdtemp() 
        try: 
            stdout = tempdir.join(self.fspath.basename) + '.out'
            stderr = tempdir.join(self.fspath.basename) + '.err'
            if sys.platform == 'win32':
                status = os.system("%s >%s 2>%s" %(cmd, stdout, stderr))
                if status>=0:
                    status = status
                else:
                    status = 'abnormal termination 0x%x' % status
            else:
                status = os.system("%s >>%s 2>>%s" %(cmd, stdout, stderr))
                if os.WIFEXITED(status):
                    status = os.WEXITSTATUS(status)
                else:
                    status = 'abnormal termination 0x%x' % status
            return status, stdout.read(mode='rU'), stderr.read(mode='rU')
        finally: 
            tempdir.remove()

    def getresult(self, regrtest): 
        cmd = self.getinvocation(regrtest) 
        result = Result()
        fspath = regrtest.getfspath() 
        result['fspath'] = str(fspath) 
        result['pypy-revision'] = getrev(pypydir) 
        if option.use_compiled:
            execpath, info = getexecutable()
            result['pypy-revision'] = info['rev']
            result['executable'] = execpath.basename
            for key, value in info.items():
                if key == 'rev':
                    continue
                result['executable-%s' % key] = str(value)
        else:
            result['executable'] = 'py.py'
        result['options'] = regrtest.getoptions() 
        result['timeout'] = gettimeout()
        result['startdate'] = time.ctime()
        starttime = time.time() 

        # really run the test in a sub process
        exit_status, test_stdout, test_stderr = self.getstatusouterr(cmd) 

        timedout = test_stderr.rfind(26*"=" + "timedout" + 26*"=") != -1 
        if not timedout: 
            timedout = test_stderr.rfind("KeyboardInterrupt") != -1
        result['execution-time'] = time.time() - starttime
        result.addnamedtext('stdout', test_stdout)
        result.addnamedtext('stderr', test_stderr)

        outcome = 'OK'
        expectedpath = regrtest.getoutputpath()
        if not exit_status: 
            if expectedpath is not None: 
                expected = expectedpath.read(mode='rU')
                test_stdout = "%s\n%s" % (self.fspath.purebasename, test_stdout)     
                if test_stdout != expected: 
                    exit_status = 2  
                    res, out, err = py.io.StdCapture.call(reportdiff, expected, test_stdout)
                    outcome = 'ERROUT' 
                    result.addnamedtext('reportdiff', out)
            else:
                if 'FAIL' in test_stdout or 'ERROR' in test_stderr:
                    outcome = 'FAIL'
        elif timedout: 
            outcome = "T/O"    
        else: 
            outcome = "ERR"
        
        result['exit-status'] = exit_status 
        result['outcome'] = outcome 
        return result


#
# Sanity check  (could be done more nicely too)
#
import os
samefile = getattr(os.path, 'samefile', 
                   lambda x,y : str(x) == str(y))
if samefile(os.getcwd(), str(regrtestdir.dirpath())):
    raise NotImplementedError(
        "Cannot run py.test with this current directory:\n"
        "the app-level sys.path will contain %s before %s)." % (
            regrtestdir.dirpath(), modregrtestdir.dirpath()))
