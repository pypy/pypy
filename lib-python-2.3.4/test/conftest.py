import py
import sys
import pypy
from pypy.interpreter.gateway import ApplevelClass 
from pypy.interpreter.error import OperationError
from pypy.tool import pytestsupport
from pypy.interpreter.module import Module as PyPyModule 
from pypy.interpreter.main import run_string, run_file

# the following adds command line options as a side effect! 
from pypy.conftest import gettestobjspace, option as pypy_option 
from test.regrtest import reportdiff

# 
# Interfacing/Integrating with py.test's collection process 
#

# XXX no nice way to implement a --listpassing py.test option?! 
#option = py.test.addoptions("compliance testing options", 
#    py.test.Option('-L', '--listpassing', action="store", default=None, 
#                   type="string", dest="listpassing", 
#                   help="just display the list of expected-to-pass tests.")

Option = py.test.Config.Option 
option = py.test.Config.addoptions("compliance testing options", 
    Option('-D', '--withdisabled', action="store_true", 
           default=False, dest="withdisabled", 
           help="include all disabled tests in the test run."), 
    Option('-E', '--extracttests', action="store_true", 
           default=False, dest="extracttests", 
           help="try to extract single tests and run them via py.test/PyPy"), 
    Option('-T', '--timeout', action="store", type="int", 
           default=15*60, dest="timeout", 
           help="timeout running of a test module (default 15*60 seconds)"), 
    ) 


mydir = py.magic.autopath().dirpath()
pypydir = py.path.local(pypy.__file__).dirpath()

def make_module(space, dottedname, filepath): 
    #print "making module", dottedname, "from", filepath 
    w_dottedname = space.wrap(dottedname) 
    mod = PyPyModule(space, w_dottedname) 
    w_globals = mod.w_dict 
    w_filename = space.wrap(str(filepath)) 
    w_execfile = space.builtin.get('execfile') 
    print "calling execfile", w_filename
    space.call_function(w_execfile, w_filename, w_globals, w_globals)
    w_mod = space.wrap(mod) 
    w_modules = space.sys.get('modules') 
    space.setitem(w_modules, w_dottedname, w_mod) 
    return w_mod 

def callex(space, func, *args, **kwargs): 
    try: 
        return func(*args, **kwargs) 
    except OperationError, e: 
        if e.match(space, space.w_KeyboardInterrupt): 
            raise KeyboardInterrupt 
        appexcinfo=pytestsupport.AppExceptionInfo(space, e) 
        if appexcinfo.traceback: 
            print "appexcinfo.traceback:"
            py.std.pprint.pprint(appexcinfo.traceback)
            raise py.test.Item.Failed(excinfo=appexcinfo) 
        raise 
    
w_utestlist = None 
w_doctestmodules = None 

def hack_test_support(space): 
    global w_utestlist, w_doctestmodules
    w_utestlist = space.newlist([]) 
    w_doctestmodules = space.newlist([]) 
    w_mod = make_module(space, 'unittest', mydir.join('pypy_unittest.py')) 
    #self.w_TestCase = space.getattr(w_mod, space.wrap('TestCase'))
    space.appexec([w_utestlist, w_doctestmodules], """
        (testlist, doctestmodules): 
            from test import test_support  # humpf

            def hack_run_unittest(*classes): 
                testlist.extend(list(classes))
            test_support.run_unittest = hack_run_unittest 

            def hack_run_doctest(module, verbose=None): 
                doctestmodules.append(module) 
            test_support.run_doctest = hack_run_doctest 

            def hack_run_suite(suite, testclass=None): 
                pass  # XXX 
            test_support.run_suite = hack_run_doctest 

    """) 

def getmyspace(): 
    space = gettestobjspace('std') 
    # we once and for all want to patch run_unittest 
    # to get us the list of intended unittest-TestClasses
    # from each regression test 
    if w_utestlist is None and option.extracttests: 
        callex(space, hack_test_support, space) 
    return space 

app = ApplevelClass('''
    #NOT_RPYTHON  

    def list_testmethods(cls): 
        """ return [(instance.setUp, instance.tearDown, 
                     [instance.testmethod1, ...]), ...]
        """ 
        clsname = cls.__name__
        instance = cls() 
        #print "checking", instance 
        methods = []
        for methodname in dir(cls): 
            if methodname.startswith('test'): 
                name = clsname + '.' + methodname 
                methods.append((name, getattr(instance, methodname)))
        return instance.setUp, instance.tearDown, methods 
''') 

list_testmethods = app.interphook('list_testmethods')

class OpErrorModule(py.test.collect.Module): 
    # wraps some methods around a py.test Module in order
    # to get clean KeyboardInterrupt behaviour (while 
    # running pypy we often get a wrapped 
    # space.w_KeyboardInterrupt)
    #
    def __init__(self, fspath, parent, testdecl): 
        super(py.test.collect.Module, self).__init__(fspath, parent) 
        self.testdecl = testdecl 

    space = property(lambda x: getmyspace()) 
    
    def tryiter(self, stopitems=()): 
        try: 
            for x in super(OpErrorModule, self).tryiter(stopitems): 
                yield x 
        except OperationError, e: 
            space = self.space 
            if space and e.match(space, space.w_KeyboardInterrupt): 
                raise Keyboardinterrupt 
            appexcinfo = pytestsupport.AppExceptionInfo(space, e) 
            if appexcinfo.traceback: 
                raise self.Failed(excinfo=appexcinfo) 
            raise 

class OutputTestModule(OpErrorModule): 
    def run(self): 
        return ['apprunoutput']
    def join(self, name): 
        if name == 'apprunoutput': 
            return OutputTestItem(name, parent=self, fspath=self.fspath) 

class SimpleRunModule(OpErrorModule): 
    def run(self): 
        return ['apprun']
    
    def join(self, name): 
        if name == 'apprun': 
            return RunAppFileItem(name, parent=self, fspath=self.fspath) 

class TestDeclMixin(object): 
    def testdecl(self): 
        current = self.parent 
        while current is not None: 
            if hasattr(current, 'testdecl'): 
                return current.testdecl 
            current = self.sparent 
    testdecl = property(testdecl) 

class RunAppFileItem(py.test.Item, TestDeclMixin): 
    """ simple run a module file at app level, fail the test 
        if running the appfile results in an OperationError. 
    """
    def __init__(self, name, parent, fspath): 
        super(RunAppFileItem, self).__init__(name, parent) 
        self.fspath = fspath 
        self.space = getmyspace()


    def getfspath(self): 
        if self.parent.testdecl.modified: 
            # we have to use a modified test ... (this could probably
            # be done by just looking for the according test file 
            # but i found this more explicit) 
            return pypydir.join('lib', 'test2', self.fspath.basename) 
        else: 
            return self.fspath # unmodified regrtest

    def run_file(self, fspath): 
        space = self.space 
        if self.testdecl.oldstyle or pypy_option.oldstyle: 
            space.enable_old_style_classes_as_default_metaclass() 
        try: 
            run_file(str(fspath), space) 
        finally: 
            if not pypy_option.oldstyle: 
                space.enable_new_style_classes_as_default_metaclass() 

    def run(self): 
        fspath = self.getfspath() 
        try: 
            self.run_file(fspath) 
        except OperationError, e: 
            space = self.space 
            if space and e.match(space, space.w_KeyboardInterrupt): 
                raise Keyboardinterrupt 
            appexcinfo = pytestsupport.AppExceptionInfo(space, e) 
            if appexcinfo.traceback: 
                raise self.Failed(excinfo=appexcinfo) 
            raise 

class OutputTestItem(RunAppFileItem): 
    """ Run a module file and compare its output 
        to the expected output in the output/ directory. 
    """ 
    def run(self): 
        outputpath = self.fspath.dirpath('output', self.fspath.purebasename) 
        if not outputpath.check(): 
            py.test.fail("expected outputfile at %s" %(outputpath,))

        oldsysout = sys.stdout 
        sys.stdout = capturesysout = py.std.cStringIO.StringIO() 
        try: 
            super(OutputTestItem, self).run() 
        finally: 
            sys.stdout = oldsysout 
        # we want to compare outputs 
        result = self.fspath.purebasename+"\n"+capturesysout.getvalue() # regrtest itself prepends the test_name to the captured output
        expected = outputpath.read(mode='r') 
        if result != expected: 
            reportdiff(expected, result) 
            py.test.fail("output check failed: %s" % (self.fspath.basename,))
        else: 
            print result 

#
class UTTestMainModule(OpErrorModule): 
    """ special handling for tests with a proper 'def test_main(): '
        definition invoking test_support.run_unittest (XXX and
        test_support.run_doctest). 
    """ 
    def _prepare(self): 
        if hasattr(self, '_testcases'): 
            return
        space = self.space
        self._testcases = callex(self.space, self.get_testcases) 
       
    def run(self): 
        self._prepare() 
        return [x[0] for x in self._testcases]

    def get_testcases(self): 
        name = self.fspath.purebasename 
        space = self.space 
        if self.testdecl.modified: 
            fspath = pypydir.join('lib', 'test2', self.fspath.basename) 
        else: 
            fspath = self.fspath 

        if self.testdecl.oldstyle or pypy_option.oldstyle: 
            space.enable_old_style_classes_as_default_metaclass() 
        try:  
            w_mod = make_module(space, name, fspath) 
        finally: 
            if not pypy_option.oldstyle: 
                space.enable_new_style_classes_as_default_metaclass() 

        # hack out testcases 
        space.appexec([w_mod, w_utestlist], """ 
            (mod, classlist): 
                classlist[:] = []
                mod.test_main() 
            """) 
        res = []
        #print w_utestlist
        for w_class in space.unpackiterable(w_utestlist): 
            w_name = space.getattr(w_class, space.wrap('__name__'))
            res.append((space.str_w(w_name), w_class ))
        res.sort()
        return res 

    def join(self, name): 
        for x,w_cls in self._testcases: 
            if x == name: 
                return UTAppTestCase(name, parent=self, w_cls=w_cls) 


class UTAppTestCase(py.test.collect.Class): 
    def __init__(self, name, parent, w_cls): 
        super(UTAppTestCase, self).__init__(name, parent) 
        self.w_cls = w_cls 

    def _prepare(self): 
        if not hasattr(self, 'space'): 
            self.space = space = self.parent.space
            w_item = list_testmethods(space, self.w_cls)
            w_setup, w_teardown, w_methods = space.unpackiterable(w_item) 
            methoditems_w = space.unpackiterable(w_methods)
            self.methods_w = methods_w = []
            for w_methoditem in methoditems_w: 
                w_name, w_method = space.unpacktuple(w_methoditem) 
                name = space.str_w(w_name) 
                methods_w.append((name, w_method, w_setup, w_teardown))
            methods_w.sort() 
            
    def run(self): 
        callex(self.parent.space, self._prepare,) 
        return [x[0] for x in self.methods_w]

    def join(self, name): 
        for x in self.methods_w: 
            if x[0] == name: 
                args = x[1:]
                return AppTestCaseMethod(name, self, *args) 

class AppTestCaseMethod(py.test.Item): 
    def __init__(self, name, parent, w_method, w_setup, w_teardown): 
        super(AppTestCaseMethod, self).__init__(name, parent) 
        self.space = parent.space 
        self.w_method = w_method 
        self.w_setup = w_setup 
        self.w_teardown = w_teardown 

    def run(self):      
        space = self.space
        try:
            filename = str(self.fspath) 
            w_argv = space.sys.get('argv')
            space.setitem(w_argv, space.newslice(None, None, None),
                          space.newlist([space.wrap(filename)]))
            space.call_function(self.w_setup) 
            try: 
                try: 
                    self.execute() 
                except OperationError, e:
                    if e.match(space, space.w_KeyboardInterrupt):
                        raise KeyboardInterrupt
                    raise  
            finally: 
                self.space.call_function(self.w_teardown) 
        except OperationError, e: 
            ilevel_excinfo = py.code.ExceptionInfo() 
            excinfo=pytestsupport.AppExceptionInfo(self.space, e) 
            if excinfo.traceback: 
                raise self.Failed(excinfo=excinfo) 
            raise self.Failed(excinfo=ilevel_excinfo) 

    def execute(self): 
        self.space.call_function(self.w_method)

# ________________________________________________________________________
#
# classification of all tests files (this is ongoing work) 
#

class TestDecl: 
    """ Test Declaration.""" 
    def __init__(self, enabled, testclass, modified=False, oldstyle=False): 
        """ if modified is True, the actual test item 
            needs to be taken from the pypy/lib/test2 
            hierarchy.  
        """ 
        self.enabled = enabled 
        self.testclass = testclass 
        self.modified = modified 
        self.oldstyle = True 

testmap = {
    'test_MimeWriter.py'     : TestDecl(False, OutputTestModule),
    'test_StringIO.py'       : TestDecl(True, UTTestMainModule),
    'test___all__.py'        : TestDecl(False, UTTestMainModule),
    'test___future__.py'     : TestDecl(False, SimpleRunModule), 
    'test_aepack.py'         : TestDecl(False, UTTestMainModule),
    'test_al.py'             : TestDecl(False, SimpleRunModule), 
    'test_anydbm.py'         : TestDecl(False, UTTestMainModule),
    'test_array.py'          : TestDecl(False, UTTestMainModule),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_asynchat.py'       : TestDecl(False, OutputTestModule),
    'test_atexit.py'         : TestDecl(False, SimpleRunModule),
    'test_audioop.py'        : TestDecl(False, SimpleRunModule),
    'test_augassign.py'      : TestDecl(False, OutputTestModule),
    'test_base64.py'         : TestDecl(True,  UTTestMainModule),
    'test_bastion.py'        : TestDecl(False, SimpleRunModule),
    'test_binascii.py'       : TestDecl(False, UTTestMainModule),
        #rev 10840: 2 of 8 tests fail

    'test_binhex.py'         : TestDecl(False, UTTestMainModule),
        #rev 10840: 1 of 1 test fails

    'test_binop.py'          : TestDecl(True,  UTTestMainModule),
    'test_bisect.py'         : TestDecl(True,  UTTestMainModule),
    'test_bool.py'           : TestDecl(False, UTTestMainModule),
        #rev 10840: Infinite recursion in DescrOperation.is_true

    'test_bsddb.py'          : TestDecl(False, UTTestMainModule),
    'test_bsddb185.py'       : TestDecl(False, UTTestMainModule),
    'test_bsddb3.py'         : TestDecl(False, UTTestMainModule),
    'test_bufio.py'          : TestDecl(False, SimpleRunModule),
    'test_builtin.py'        : TestDecl(True,  UTTestMainModule),
    'test_bz2.py'            : TestDecl(False, UTTestMainModule),
    'test_calendar.py'       : TestDecl(True, UTTestMainModule),
    'test_call.py'           : TestDecl(True,  UTTestMainModule),
    'test_capi.py'           : TestDecl(False, SimpleRunModule),
    'test_cd.py'             : TestDecl(False, SimpleRunModule),
    'test_cfgparser.py'      : TestDecl(False, UTTestMainModule),
        #rev 10840: Uncaught interp-level exception:
        #File "pypy/objspace/std/fake.py", line 133, in setfastscope
        #raise UnwrapError('calling %s: %s' % (self.code.cpy_callable, e))
        #pypy.objspace.std.model.UnwrapError: calling <built-in function backslashreplace_errors>: cannot unwrap <UserW_ObjectObject() instance of <W_TypeObject(UnicodeError)>>

    'test_cgi.py'            : TestDecl(False, OutputTestModule),
    'test_charmapcodec.py'   : TestDecl(True, UTTestMainModule),
    'test_cl.py'             : TestDecl(False, SimpleRunModule),
    'test_class.py'          : TestDecl(False, OutputTestModule),
    'test_cmath.py'          : TestDecl(True,  SimpleRunModule), 
    'test_codeccallbacks.py' : TestDecl(False, UTTestMainModule),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_codecs.py'         : TestDecl(False, UTTestMainModule),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_codeop.py'         : TestDecl(True,  UTTestMainModule),
    'test_coercion.py'       : TestDecl(False, OutputTestModule),
    'test_commands.py'       : TestDecl(True,  UTTestMainModule),
    'test_compare.py'        : TestDecl(True,  OutputTestModule, oldstyle=True),
    'test_compile.py'        : TestDecl(True,  UTTestMainModule),
    'test_complex.py'        : TestDecl(False, UTTestMainModule),
        #rev 10840: at least one test fails, after several hours I gave up waiting for the rest

    'test_contains.py'       : TestDecl(False, SimpleRunModule),
    'test_cookie.py'         : TestDecl(False, OutputTestModule),
    'test_copy.py'           : TestDecl(True, UTTestMainModule),
    'test_copy_reg.py'       : TestDecl(True, UTTestMainModule),
    'test_cpickle.py'        : TestDecl(False, UTTestMainModule),
    'test_crypt.py'          : TestDecl(False, SimpleRunModule),
    'test_csv.py'            : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: _csv

    'test_curses.py'         : TestDecl(False, SimpleRunModule),
    'test_datetime.py'       : TestDecl(True,  UTTestMainModule),
    'test_dbm.py'            : TestDecl(False, SimpleRunModule),
    'test_descr.py'          : TestDecl(False, UTTestMainModule),
    'test_descrtut.py'       : TestDecl(False, UTTestMainModule),
        #rev 10840: 19 of 96 tests fail

    'test_difflib.py'        : TestDecl(False, SimpleRunModule),
    'test_dircache.py'       : TestDecl(True, UTTestMainModule),
    'test_dis.py'            : TestDecl(True,  UTTestMainModule),
    'test_dl.py'             : TestDecl(False, SimpleRunModule),
    'test_doctest.py'        : TestDecl(False, SimpleRunModule),
    'test_doctest2.py'       : TestDecl(True, UTTestMainModule),
    'test_dumbdbm.py'        : TestDecl(False, UTTestMainModule),
        #rev 10840: 5 of 7 tests fail

    'test_dummy_thread.py'   : TestDecl(True, UTTestMainModule),
    'test_dummy_threading.py': TestDecl(False, SimpleRunModule),
    'test_email.py'          : TestDecl(False, UTTestMainModule),
        #rev 10840: Uncaught interp-level exception

    'test_email_codecs.py'   : TestDecl(False, SimpleRunModule),
    'test_enumerate.py'      : TestDecl(False, UTTestMainModule),
        #rev 10840: fails because enumerate is a type in CPy: the test tries to subclass it

    'test_eof.py'            : TestDecl(False, UTTestMainModule),
        #rev 10840: some error strings differ slightly XXX

    'test_errno.py'          : TestDecl(False, SimpleRunModule),
    'test_exceptions.py'     : TestDecl(False, OutputTestModule),
    'test_extcall.py'        : TestDecl(False, OutputTestModule),
    'test_fcntl.py'          : TestDecl(False, SimpleRunModule),
    'test_file.py'           : TestDecl(False, SimpleRunModule),
    'test_filecmp.py'        : TestDecl(False, UTTestMainModule),
    'test_fileinput.py'      : TestDecl(False, SimpleRunModule),
    'test_fnmatch.py'        : TestDecl(True, UTTestMainModule),
    'test_fork1.py'          : TestDecl(False, SimpleRunModule),
    'test_format.py'         : TestDecl(False, SimpleRunModule),
    'test_fpformat.py'       : TestDecl(True, UTTestMainModule),
    'test_frozen.py'         : TestDecl(False, OutputTestModule),
    'test_funcattrs.py'      : TestDecl(False, SimpleRunModule),
    'test_future.py'         : TestDecl(False, OutputTestModule),
    'test_future1.py'        : TestDecl(False, SimpleRunModule),
    'test_future2.py'        : TestDecl(False, SimpleRunModule),
    'test_future3.py'        : TestDecl(True, UTTestMainModule),
    'test_gc.py'             : TestDecl(False, SimpleRunModule),
    'test_gdbm.py'           : TestDecl(False, SimpleRunModule),
    'test_generators.py'     : TestDecl(False, UTTestMainModule),
        #rev 10840: 30 of 152 tests fail

    'test_getargs.py'        : TestDecl(False, SimpleRunModule),
    'test_getargs2.py'       : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: _testcapi

    'test_getopt.py'         : TestDecl(False, SimpleRunModule),
    'test_gettext.py'        : TestDecl(False, UTTestMainModule),
        #rev 10840: 28 of 28 tests fail

    'test_gl.py'             : TestDecl(False, SimpleRunModule),
    'test_glob.py'           : TestDecl(True, UTTestMainModule),
    'test_global.py'         : TestDecl(False, OutputTestModule),
    'test_grammar.py'        : TestDecl(False, OutputTestModule),
    'test_grp.py'            : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: grp

    'test_gzip.py'           : TestDecl(False, SimpleRunModule),
    'test_hash.py'           : TestDecl(True,  UTTestMainModule),
    'test_heapq.py'          : TestDecl(True,  UTTestMainModule),
    'test_hexoct.py'         : TestDecl(True,  UTTestMainModule),
    'test_hmac.py'           : TestDecl(True, UTTestMainModule),
    'test_hotshot.py'        : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: _hotshot

    'test_htmllib.py'        : TestDecl(True,  UTTestMainModule),
    'test_htmlparser.py'     : TestDecl(True,  UTTestMainModule),
    'test_httplib.py'        : TestDecl(False, OutputTestModule),
    'test_imageop.py'        : TestDecl(False, SimpleRunModule),
    'test_imaplib.py'        : TestDecl(False, SimpleRunModule),
    'test_imgfile.py'        : TestDecl(False, SimpleRunModule),
    'test_imp.py'            : TestDecl(False, UTTestMainModule),
    'test_import.py'         : TestDecl(False, SimpleRunModule),
    'test_importhooks.py'    : TestDecl(False, UTTestMainModule),
    'test_inspect.py'        : TestDecl(False, SimpleRunModule),
    'test_ioctl.py'          : TestDecl(False, UTTestMainModule),
    'test_isinstance.py'     : TestDecl(True,  UTTestMainModule),
    'test_iter.py'           : TestDecl(False, UTTestMainModule),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_itertools.py'      : TestDecl(True, UTTestMainModule, modified=True),
        # modified version in pypy/lib/test2

    'test_largefile.py'      : TestDecl(False, SimpleRunModule),
    'test_linuxaudiodev.py'  : TestDecl(False, OutputTestModule),
    'test_locale.py'         : TestDecl(False, SimpleRunModule),
    'test_logging.py'        : TestDecl(False, OutputTestModule),
    'test_long.py'           : TestDecl(True,  SimpleRunModule), # takes hours 
    'test_long_future.py'    : TestDecl(False, SimpleRunModule),
    'test_longexp.py'        : TestDecl(False, OutputTestModule),
    'test_macfs.py'          : TestDecl(False, UTTestMainModule),
    'test_macostools.py'     : TestDecl(False, UTTestMainModule),
    'test_macpath.py'        : TestDecl(False, UTTestMainModule),
    'test_mailbox.py'        : TestDecl(True, UTTestMainModule),
    'test_marshal.py'        : TestDecl(False, SimpleRunModule),
    'test_math.py'           : TestDecl(False, OutputTestModule),
    'test_md5.py'            : TestDecl(False, OutputTestModule),
    'test_mhlib.py'          : TestDecl(True, UTTestMainModule),
    'test_mimetools.py'      : TestDecl(True, UTTestMainModule),
    'test_mimetypes.py'      : TestDecl(True, UTTestMainModule),
    'test_minidom.py'        : TestDecl(False, SimpleRunModule),
    'test_mmap.py'           : TestDecl(False, OutputTestModule),
    'test_module.py'         : TestDecl(False, SimpleRunModule),
    'test_mpz.py'            : TestDecl(False, SimpleRunModule),
    'test_multifile.py'      : TestDecl(True, UTTestMainModule),
    'test_mutants.py'        : TestDecl(False, SimpleRunModule),
    'test_netrc.py'          : TestDecl(True, UTTestMainModule),
    'test_new.py'            : TestDecl(False, OutputTestModule),
    'test_nis.py'            : TestDecl(False, OutputTestModule),
    'test_normalization.py'  : TestDecl(False, UTTestMainModule),
    'test_ntpath.py'         : TestDecl(False, SimpleRunModule),
    'test_opcodes.py'        : TestDecl(False, OutputTestModule),
    'test_openpty.py'        : TestDecl(False, OutputTestModule),
    'test_operations.py'     : TestDecl(False, OutputTestModule),
    'test_operator.py'       : TestDecl(True,  UTTestMainModule),
    'test_optparse.py'       : TestDecl(False, UTTestMainModule),
    'test_os.py'             : TestDecl(True, UTTestMainModule),
    'test_ossaudiodev.py'    : TestDecl(False, OutputTestModule),
    'test_parser.py'         : TestDecl(True,  UTTestMainModule),
        #rev 10840: 18 of 18 tests fail

    'test_pep247.py'         : TestDecl(False, SimpleRunModule),
    'test_pep263.py'         : TestDecl(False, SimpleRunModule),
    'test_pep277.py'         : TestDecl(False, UTTestMainModule),
        # XXX this test is _also_ an output test, damn it 
        #     seems to be the only one that invokes run_unittest 
        #     and is an unittest 
    'test_pickle.py'         : TestDecl(False, UTTestMainModule),
    'test_pickletools.py'    : TestDecl(False, SimpleRunModule),
    'test_pkg.py'            : TestDecl(False, OutputTestModule),
    'test_pkgimport.py'      : TestDecl(True, UTTestMainModule),
    'test_plistlib.py'       : TestDecl(False, UTTestMainModule),
    'test_poll.py'           : TestDecl(False, OutputTestModule),
    'test_popen.py'          : TestDecl(False, OutputTestModule),
    'test_popen2.py'         : TestDecl(False, OutputTestModule),
    'test_posix.py'          : TestDecl(True, UTTestMainModule),
    'test_posixpath.py'      : TestDecl(True, UTTestMainModule),
    'test_pow.py'            : TestDecl(True, UTTestMainModule),
    'test_pprint.py'         : TestDecl(True,  UTTestMainModule),
    'test_profile.py'        : TestDecl(True, OutputTestModule),
    'test_profilehooks.py'   : TestDecl(True,  UTTestMainModule),
    'test_pty.py'            : TestDecl(False, OutputTestModule),
    'test_pwd.py'            : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: pwd

    'test_pyclbr.py'         : TestDecl(False, UTTestMainModule),
    'test_pyexpat.py'        : TestDecl(False, OutputTestModule),
    'test_queue.py'          : TestDecl(False, SimpleRunModule),
    'test_quopri.py'         : TestDecl(False, UTTestMainModule),
    'test_random.py'         : TestDecl(False, UTTestMainModule),
        #rev 10840: Uncaught app-level exception:
        #class WichmannHill_TestBasicOps(TestBasicOps):
        #File "test_random.py", line 125 in WichmannHill_TestBasicOps
        #gen = random.WichmannHill()
        #AttributeError: 'module' object has no attribute 'WichmannHill'

    'test_re.py'             : TestDecl(False, UTTestMainModule),
        #rev 10840: 7 of 47 tests fail

    'test_regex.py'          : TestDecl(False, OutputTestModule),
    'test_repr.py'           : TestDecl(False, UTTestMainModule),
        #rev 10840: 6 of 12 tests fail. Always minor stuff like
        #'<function object at 0x40db3e0c>' != '<built-in function hash>'

    'test_resource.py'       : TestDecl(False, OutputTestModule),
    'test_rfc822.py'         : TestDecl(True, UTTestMainModule),
    'test_rgbimg.py'         : TestDecl(False, OutputTestModule),
    'test_richcmp.py'        : TestDecl(False, UTTestMainModule),
        #rev 10840: 1 of 11 test fails. The failing one had an infinite recursion.

    'test_robotparser.py'    : TestDecl(True, UTTestMainModule),
    'test_rotor.py'          : TestDecl(False, OutputTestModule),
    'test_sax.py'            : TestDecl(False, SimpleRunModule),
    'test_scope.py'          : TestDecl(False, OutputTestModule),
    'test_scriptpackages.py' : TestDecl(False, UTTestMainModule),
    'test_select.py'         : TestDecl(False, SimpleRunModule),
    'test_sets.py'           : TestDecl(True, UTTestMainModule),
    'test_sgmllib.py'        : TestDecl(True,  UTTestMainModule),
    'test_sha.py'            : TestDecl(True, UTTestMainModule, modified=True),
        # one test is taken out (too_slow_test_case_3), rest passses 
    'test_shelve.py'         : TestDecl(True, UTTestMainModule),
    'test_shlex.py'          : TestDecl(True, UTTestMainModule),
    'test_shutil.py'         : TestDecl(True, UTTestMainModule),
    'test_signal.py'         : TestDecl(False, OutputTestModule),
    'test_slice.py'          : TestDecl(False, SimpleRunModule),
    'test_socket.py'         : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: thread

    'test_socket_ssl.py'     : TestDecl(False, UTTestMainModule),
    'test_socketserver.py'   : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: thread

    'test_softspace.py'      : TestDecl(False, SimpleRunModule),
    'test_sort.py'           : TestDecl(False, SimpleRunModule),
    'test_str.py'            : TestDecl(False, UTTestMainModule),
        #rev 10840: at least two tests fail, after several hours I gave up waiting for the rest

    'test_strftime.py'       : TestDecl(False, SimpleRunModule),
    'test_string.py'         : TestDecl(True,  UTTestMainModule),
    'test_stringprep.py'     : TestDecl(False, SimpleRunModule),
    'test_strop.py'          : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: strop

    'test_strptime.py'       : TestDecl(False, UTTestMainModule),
        #rev 10840: 1 of 42 test fails: seems to be some regex problem

    'test_struct.py'         : TestDecl(False, SimpleRunModule),
    'test_structseq.py'      : TestDecl(False, SimpleRunModule),
    'test_sunaudiodev.py'    : TestDecl(False, SimpleRunModule),
    'test_sundry.py'         : TestDecl(False, SimpleRunModule),
    'test_support.py'        : TestDecl(False, SimpleRunModule),
    'test_symtable.py'       : TestDecl(False, SimpleRunModule),
    'test_syntax.py'         : TestDecl(True, UTTestMainModule),
    'test_sys.py'            : TestDecl(True,  UTTestMainModule),
    'test_tarfile.py'        : TestDecl(False, UTTestMainModule),
        #rev 10840: 13 of 13 test fail

    'test_tempfile.py'       : TestDecl(False, UTTestMainModule),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_textwrap.py'       : TestDecl(True,  UTTestMainModule),
    'test_thread.py'         : TestDecl(False, OutputTestModule),
    'test_threaded_import.py': TestDecl(False, UTTestMainModule),
    'test_threadedtempfile.py': TestDecl(False, OutputTestModule),
        #rev 10840: ImportError: thread

    'test_threading.py'      : TestDecl(False, SimpleRunModule),
        #rev 10840: ImportError: thread

    'test_time.py'           : TestDecl(True, UTTestMainModule),
    'test_timeout.py'        : TestDecl(False, UTTestMainModule),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_timing.py'         : TestDecl(False, SimpleRunModule),
    'test_tokenize.py'       : TestDecl(False, OutputTestModule),
    'test_trace.py'          : TestDecl(True,  UTTestMainModule),
    'test_traceback.py'      : TestDecl(False, UTTestMainModule),
        #rev 10840: 2 of 2 tests fail

    'test_types.py'          : TestDecl(False, OutputTestModule, modified=True),
        #rev 10920: fails with: 
        #   E       vereq(a[::], a)
        #   >       (application-level) TypeError: an integer is required
        #   [/home/hpk/pypy-dist/pypy/lib/test2/test_types.py:217]
        
    'test_ucn.py'            : TestDecl(False, UTTestMainModule),
    'test_unary.py'          : TestDecl(True, UTTestMainModule),
    'test_unicode.py'        : TestDecl(False, UTTestMainModule),
    'test_unicode_file.py'   : TestDecl(False, OutputTestModule),
    'test_unicodedata.py'    : TestDecl(False, UTTestMainModule),
    'test_univnewlines.py'   : TestDecl(True, UTTestMainModule),
    'test_unpack.py'         : TestDecl(False, SimpleRunModule),
    'test_urllib.py'         : TestDecl(True, UTTestMainModule),
        #rev 10840: 10 of 10 tests fail

    'test_urllib2.py'        : TestDecl(False, SimpleRunModule),
    'test_urllibnet.py'      : TestDecl(False, UTTestMainModule),
    'test_urlparse.py'       : TestDecl(True,  UTTestMainModule),
    'test_userdict.py'       : TestDecl(True, UTTestMainModule),
        #rev 10840: 5 of 25 tests fail

    'test_userlist.py'       : TestDecl(False, UTTestMainModule),
        #rev 10840: at least two tests fail, after several hours I gave up waiting for the rest

    'test_userstring.py'     : TestDecl(False, UTTestMainModule),
    'test_uu.py'             : TestDecl(False, UTTestMainModule),
        #rev 10840: 1 of 9 test fails

    'test_warnings.py'       : TestDecl(True, UTTestMainModule),
    'test_wave.py'           : TestDecl(False, SimpleRunModule),
    'test_weakref.py'        : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: _weakref

    'test_whichdb.py'        : TestDecl(False, UTTestMainModule),
    'test_winreg.py'         : TestDecl(False, OutputTestModule),
    'test_winsound.py'       : TestDecl(False, UTTestMainModule),
    'test_xmllib.py'         : TestDecl(False, UTTestMainModule),
    'test_xmlrpc.py'         : TestDecl(False, UTTestMainModule),
        #rev 10840: 2 of 5 tests fail

    'test_xpickle.py'        : TestDecl(False, UTTestMainModule),
    'test_xreadline.py'      : TestDecl(False, OutputTestModule),
    'test_zipfile.py'        : TestDecl(False, SimpleRunModule),
    'test_zipimport.py'      : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: zlib

    'test_zlib.py'           : TestDecl(False, UTTestMainModule),
        #rev 10840: ImportError: zlib
}

class RegrDirectory(py.test.collect.Directory): 
    """ The central hub for gathering CPython's compliance tests
        Basically we work off the above 'testmap' 
        which describes for all test modules their specific 
        type.  XXX If you find errors in the classification 
        please correct them! 
    """ 
    testmap = testmap
    def run(self): 
        l = []
        items = self.testmap.items() 
        items.sort(lambda x,y: cmp(x[0].lower(), y[0].lower()))
        for name, testdecl in items: 
            if option.withdisabled or testdecl.enabled: 
                l.append(name) 
        return l 

    def join(self, name): 
        if name in self.testmap: 
            testdecl = self.testmap[name]
            fspath = self.fspath.join(name) 
            if option.extracttests:  
                return testdecl.testclass(fspath, parent=self, testdecl=testdecl) 
            else: 
                return RunFileExternal(fspath, parent=self, testdecl=testdecl) 

Directory = RegrDirectory


def getrev(path): 
    try: 
        return py.path.svnwc(mydir).info().rev
    except: 
        return 'unknown'  # on windows people not always have 'svn' in their path

class RunFileExternal(OpErrorModule): 
    # a Module shows more nicely with the session reporting 
    # (i know this needs to become nicer) 
    def tryiter(self, stopitems=()): 
        return []
    def run(self): 
        return ['pypy-ext']
    def join(self, name): 
        if name == 'pypy-ext': 
            return ReallyRunFileExternal(name, parent=self, fspath=self.fspath) 

class ReallyRunFileExternal(RunAppFileItem): 

    def run(self): 
        """ invoke a subprocess running the test file via PyPy. 
            record its output into the 'result' subdirectory. 
            (we might want to create subdirectories for 
            each user, because we will probably all produce 
            such result runs and they will not be the same
            i am afraid. 
        """ 
        import os
        import time
        import socket
        import getpass
        fspath = self.getfspath() 
        python = sys.executable 
        pypy_dir = py.path.local(pypy.__file__).dirpath()
        pypy_script = pypy_dir.join('interpreter', 'py.py')
        alarm_script = pypy_dir.join('tool', 'alarm.py')
        pypy_options = []
        if self.testdecl.oldstyle: 
            pypy_options.append('--oldstyle') 
        sopt = " ".join(pypy_options) 
        TIMEOUT = option.timeout 
        cmd = "%s %s %d %s %s %s" %(python, alarm_script, TIMEOUT, pypy_script, sopt, fspath)
        resultfilename = mydir.join('result', fspath.new(ext='.txt').basename)
        resultfile = resultfilename.open('w')

        try:
            username = getpass.getuser()
        except:
            username = 'unknown' 
        print >> resultfile, "command:", cmd
        print >> resultfile, "run by: %s@%s" % (username, socket.gethostname())
        print >> resultfile, "sys.platform:", sys.platform 
        print >> resultfile, "sys.version_info:", sys.version_info 
        print >> resultfile, "startdate:", time.ctime()
        print >> resultfile, 'pypy-revision:', getrev(pypydir)
        print >> resultfile, '='*60
        print "executing", cmd 
        starttime = time.time()
        resultfile.close()

        status = os.system("%s >>%s 2>&1" %(cmd, resultfilename) )
        if os.WIFEXITED(status):
            status = os.WEXITSTATUS(status)
        else:
            status = 'abnormal termination 0x%x' % status

        resultfile = resultfilename.open('a')
        print >> resultfile, '='*26, 'closed', '='*26
        print >> resultfile, 'execution time:', time.time() - starttime, 'seconds'
        print >> resultfile, 'exit status:', status
        resultfile.close()
        if status != 0:
            time.sleep(0.5)   # time for a Ctrl-C to reach us :-)
        #print output 
        assert status == 0, "exitstatus is %d" %(status,)
