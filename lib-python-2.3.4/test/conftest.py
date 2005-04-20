import py
import sys
import pypy
from pypy.interpreter.gateway import ApplevelClass 
from pypy.interpreter.error import OperationError
from pypy.tool import pytestsupport
from pypy.interpreter.module import Module as PyPyModule 
from pypy.interpreter.main import run_string, run_file

# the following adds command line options as a side effect! 
from pypy.conftest import gettestobjspace, option
from test.regrtest import reportdiff

# 
# Interfacing/Integrating with py.test's collection process 
#

# XXX no nice way to implement a --listpassing py.test option?! 
#option = py.test.addoptions("compliance testing options", 
#    py.test.Option('-L', '--listpassing', action="store", default=None, 
#                   type="string", dest="listpassing", 
#                   help="just display the list of expected-to-pass tests.")

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
        raise
    
w_testlist = None 

def hack_test_support(space): 
    global w_testlist  
    w_testlist = space.newlist([]) 
    space.appexec([w_testlist], """
        (testlist): 
            def hack_run_unittest(*classes): 
                testlist.extend(list(classes))
            from test import test_support  # humpf
            test_support.run_unittest = hack_run_unittest 
    """) 

def getmyspace(): 
    space = gettestobjspace('std') 
    # we once and for all want to patch run_unittest 
    # to get us the list of intended unittest-TestClasses
    # from each regression test 
    if w_testlist is None: 
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
    
    def tryiter(self, stopitems=()): 
        try: 
            for x in super(OpErrorModule, self).tryiter(stopitems): 
                yield x 
        except OperationError, e: 
            space = getattr(self, 'space', None) 
            if space and e.match(space, space.w_KeyboardInterrupt): 
                raise Keyboardinterrupt 
            raise 

class OutputTestModule(OpErrorModule): 
    def run(self): 
        return [self.fspath.purebasename]
    def join(self, name): 
        if name == self.fspath.purebasename: 
            return OutputTestItem(name, parent=self) 

class OutputTestItem(py.test.Item): 
    def run(self): 
        outputpath = self.fspath.dirpath('output', self.name) 
        if not outputpath.check(): 
            py.test.fail("expected outputfile at %s" %(outputpath,))
        if self.parent.testdecl.modified: 
            fspath = pypydir.join('lib', 'test2', self.fspath.basename) 
        else: 
            fspath = self.fspath # unmodified regrtest
        space = getmyspace() 
        try: 
            oldsysout = sys.stdout 
            sys.stdout = capturesysout = py.std.cStringIO.StringIO() 
            try: 
                print self.fspath.purebasename 
                run_file(str(fspath), space=space) 
            finally: 
                sys.stdout = oldsysout 
        except OperationError, e: 
            raise self.Failed(
                excinfo=pytestsupport.AppExceptionInfo(space, e))
        else: 
            # we want to compare outputs 
            result = capturesysout.getvalue() 
            expected = outputpath.read(mode='r') 
            if result != expected: 
                reportdiff(expected, result) 
                py.test.fail("output check failed: %s" % (self.fspath.basename,))


class UnknownTestModule(py.test.collect.Module): 
    def run(self): 
        py.test.skip("missing test type for: %s" %(self.fspath.basename))
       
class UTModuleMainTest(OpErrorModule): 
    def _prepare(self): 
        if hasattr(self, '_testcases'): 
            return
        self.space = space = getmyspace() 
        def f(): 
            w_mod = make_module(space, 'unittest', mydir.join('pypy_unittest.py')) 
            self.w_TestCase = space.getattr(w_mod, space.wrap('TestCase'))
            self._testcases = self.get_testcases() 
        callex(space, f) 
       
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
        w_mod = make_module(space, name, fspath) 

        # hack out testcases 
        space.appexec([w_mod, w_testlist], """ 
            (mod, classlist): 
                classlist[:] = []
                mod.test_main() 
            """) 
        res = []
        #print w_testlist
        for w_class in space.unpackiterable(w_testlist): 
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

class TestDecl: 
    """ Test Declaration. """ 
    def __init__(self, enabled, testclass, modified=False): 
        self.enabled = enabled 
        self.testclass = testclass 
        self.modified = modified 

testmap = {
    'test_MimeWriter.py'     : TestDecl(False, OutputTestModule),
    'test_StringIO.py'       : TestDecl(True, UTModuleMainTest),
    'test___all__.py'        : TestDecl(False, UTModuleMainTest),
    'test___future__.py'     : TestDecl(False, UnknownTestModule),
    'test_aepack.py'         : TestDecl(False, UTModuleMainTest),
    'test_al.py'             : TestDecl(False, UnknownTestModule),
    'test_anydbm.py'         : TestDecl(False, UTModuleMainTest),
    'test_array.py'          : TestDecl(False, UTModuleMainTest),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_asynchat.py'       : TestDecl(False, OutputTestModule),
    'test_atexit.py'         : TestDecl(False, UnknownTestModule),
    'test_audioop.py'        : TestDecl(False, UnknownTestModule),
    'test_augassign.py'      : TestDecl(False, OutputTestModule),
    'test_base64.py'         : TestDecl(True,  UTModuleMainTest),
    'test_bastion.py'        : TestDecl(False, UnknownTestModule),
    'test_binascii.py'       : TestDecl(False, UTModuleMainTest),
        #rev 10840: 2 of 8 tests fail

    'test_binhex.py'         : TestDecl(False, UTModuleMainTest),
        #rev 10840: 1 of 1 test fails

    'test_binop.py'          : TestDecl(True,  UTModuleMainTest),
    'test_bisect.py'         : TestDecl(True,  UTModuleMainTest),
    'test_bool.py'           : TestDecl(False, UTModuleMainTest),
        #rev 10840: Infinite recursion in DescrOperation.is_true

    'test_bsddb.py'          : TestDecl(False, UTModuleMainTest),
    'test_bsddb185.py'       : TestDecl(False, UTModuleMainTest),
    'test_bsddb3.py'         : TestDecl(False, UTModuleMainTest),
    'test_bufio.py'          : TestDecl(False, UnknownTestModule),
    'test_builtin.py'        : TestDecl(True,  UTModuleMainTest),
    'test_bz2.py'            : TestDecl(False, UTModuleMainTest),
    'test_calendar.py'       : TestDecl(True, UTModuleMainTest),
    'test_call.py'           : TestDecl(True,  UTModuleMainTest),
    'test_capi.py'           : TestDecl(False, UnknownTestModule),
    'test_cd.py'             : TestDecl(False, UnknownTestModule),
    'test_cfgparser.py'      : TestDecl(False, UTModuleMainTest),
        #rev 10840: Uncaught interp-level exception:
        #File "pypy/objspace/std/fake.py", line 133, in setfastscope
        #raise UnwrapError('calling %s: %s' % (self.code.cpy_callable, e))
        #pypy.objspace.std.model.UnwrapError: calling <built-in function backslashreplace_errors>: cannot unwrap <UserW_ObjectObject() instance of <W_TypeObject(UnicodeError)>>

    'test_cgi.py'            : TestDecl(False, OutputTestModule),
    'test_charmapcodec.py'   : TestDecl(True, UTModuleMainTest),
    'test_cl.py'             : TestDecl(False, UnknownTestModule),
    'test_class.py'          : TestDecl(False, OutputTestModule),
    'test_cmath.py'          : TestDecl(True,  UnknownTestModule),
    'test_codeccallbacks.py' : TestDecl(False, UTModuleMainTest),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_codecs.py'         : TestDecl(False, UTModuleMainTest),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_codeop.py'         : TestDecl(True,  UTModuleMainTest),
    'test_coercion.py'       : TestDecl(False, OutputTestModule),
    'test_commands.py'       : TestDecl(True,  UTModuleMainTest),
    'test_compare.py'        : TestDecl(True,  OutputTestModule),
    'test_compile.py'        : TestDecl(True,  UTModuleMainTest),
    'test_complex.py'        : TestDecl(False, UTModuleMainTest),
        #rev 10840: at least one test fails, after several hours I gave up waiting for the rest

    'test_contains.py'       : TestDecl(False, UnknownTestModule),
    'test_cookie.py'         : TestDecl(False, OutputTestModule),
    'test_copy.py'           : TestDecl(True, UTModuleMainTest),
    'test_copy_reg.py'       : TestDecl(True, UTModuleMainTest),
    'test_cpickle.py'        : TestDecl(False, UTModuleMainTest),
    'test_crypt.py'          : TestDecl(False, UnknownTestModule),
    'test_csv.py'            : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: _csv

    'test_curses.py'         : TestDecl(False, UnknownTestModule),
    'test_datetime.py'       : TestDecl(True,  UTModuleMainTest),
    'test_dbm.py'            : TestDecl(False, UnknownTestModule),
    'test_descr.py'          : TestDecl(False, UTModuleMainTest),
    'test_descrtut.py'       : TestDecl(False, UTModuleMainTest),
        #rev 10840: 19 of 96 tests fail

    'test_difflib.py'        : TestDecl(False, UnknownTestModule),
    'test_dircache.py'       : TestDecl(True, UTModuleMainTest),
    'test_dis.py'            : TestDecl(True,  UTModuleMainTest),
    'test_dl.py'             : TestDecl(False, UnknownTestModule),
    'test_doctest.py'        : TestDecl(False, UnknownTestModule),
    'test_doctest2.py'       : TestDecl(True, UTModuleMainTest),
    'test_dumbdbm.py'        : TestDecl(False, UTModuleMainTest),
        #rev 10840: 5 of 7 tests fail

    'test_dummy_thread.py'   : TestDecl(True, UTModuleMainTest),
    'test_dummy_threading.py': TestDecl(False, UnknownTestModule),
    'test_email.py'          : TestDecl(False, UTModuleMainTest),
        #rev 10840: Uncaught interp-level exception

    'test_email_codecs.py'   : TestDecl(False, UnknownTestModule),
    'test_enumerate.py'      : TestDecl(False, UTModuleMainTest),
        #rev 10840: fails because enumerate is a type in CPy: the test tries to subclass it

    'test_eof.py'            : TestDecl(False, UTModuleMainTest),
        #rev 10840: some error strings differ slightly XXX

    'test_errno.py'          : TestDecl(False, UnknownTestModule),
    'test_exceptions.py'     : TestDecl(False, OutputTestModule),
    'test_extcall.py'        : TestDecl(False, OutputTestModule),
    'test_fcntl.py'          : TestDecl(False, UnknownTestModule),
    'test_file.py'           : TestDecl(False, UnknownTestModule),
    'test_filecmp.py'        : TestDecl(False, UTModuleMainTest),
    'test_fileinput.py'      : TestDecl(False, UnknownTestModule),
    'test_fnmatch.py'        : TestDecl(True, UTModuleMainTest),
    'test_fork1.py'          : TestDecl(False, UnknownTestModule),
    'test_format.py'         : TestDecl(False, UnknownTestModule),
    'test_fpformat.py'       : TestDecl(True, UTModuleMainTest),
    'test_frozen.py'         : TestDecl(False, OutputTestModule),
    'test_funcattrs.py'      : TestDecl(False, UnknownTestModule),
    'test_future.py'         : TestDecl(False, OutputTestModule),
    'test_future1.py'        : TestDecl(False, UnknownTestModule),
    'test_future2.py'        : TestDecl(False, UnknownTestModule),
    'test_future3.py'        : TestDecl(True, UTModuleMainTest),
    'test_gc.py'             : TestDecl(False, UnknownTestModule),
    'test_gdbm.py'           : TestDecl(False, UnknownTestModule),
    'test_generators.py'     : TestDecl(False, UTModuleMainTest),
        #rev 10840: 30 of 152 tests fail

    'test_getargs.py'        : TestDecl(False, UnknownTestModule),
    'test_getargs2.py'       : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: _testcapi

    'test_getopt.py'         : TestDecl(False, UnknownTestModule),
    'test_gettext.py'        : TestDecl(False, UTModuleMainTest),
        #rev 10840: 28 of 28 tests fail

    'test_gl.py'             : TestDecl(False, UnknownTestModule),
    'test_glob.py'           : TestDecl(True, UTModuleMainTest),
    'test_global.py'         : TestDecl(False, OutputTestModule),
    'test_grammar.py'        : TestDecl(False, OutputTestModule),
    'test_grp.py'            : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: grp

    'test_gzip.py'           : TestDecl(False, UnknownTestModule),
    'test_hash.py'           : TestDecl(True,  UTModuleMainTest),
    'test_heapq.py'          : TestDecl(True,  UTModuleMainTest),
    'test_hexoct.py'         : TestDecl(True,  UTModuleMainTest),
    'test_hmac.py'           : TestDecl(True, UTModuleMainTest),
    'test_hotshot.py'        : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: _hotshot

    'test_htmllib.py'        : TestDecl(True,  UTModuleMainTest),
    'test_htmlparser.py'     : TestDecl(True,  UTModuleMainTest),
    'test_httplib.py'        : TestDecl(False, OutputTestModule),
    'test_imageop.py'        : TestDecl(False, UnknownTestModule),
    'test_imaplib.py'        : TestDecl(False, UnknownTestModule),
    'test_imgfile.py'        : TestDecl(False, UnknownTestModule),
    'test_imp.py'            : TestDecl(False, UTModuleMainTest),
    'test_import.py'         : TestDecl(False, UnknownTestModule),
    'test_importhooks.py'    : TestDecl(False, UTModuleMainTest),
    'test_inspect.py'        : TestDecl(False, UnknownTestModule),
    'test_ioctl.py'          : TestDecl(False, UTModuleMainTest),
    'test_isinstance.py'     : TestDecl(True,  UTModuleMainTest),
    'test_iter.py'           : TestDecl(False, UTModuleMainTest),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_itertools.py'      : TestDecl(False, UTModuleMainTest),
        #rev 10840: Alternate version in test2

    'test_largefile.py'      : TestDecl(False, UnknownTestModule),
    'test_linuxaudiodev.py'  : TestDecl(False, OutputTestModule),
    'test_locale.py'         : TestDecl(False, UnknownTestModule),
    'test_logging.py'        : TestDecl(False, OutputTestModule),
    'test_long.py'           : TestDecl(True,  UnknownTestModule), # takes hours 
    'test_long_future.py'    : TestDecl(False, UnknownTestModule),
    'test_longexp.py'        : TestDecl(False, OutputTestModule),
    'test_macfs.py'          : TestDecl(False, UTModuleMainTest),
    'test_macostools.py'     : TestDecl(False, UTModuleMainTest),
    'test_macpath.py'        : TestDecl(False, UTModuleMainTest),
    'test_mailbox.py'        : TestDecl(True, UTModuleMainTest),
    'test_marshal.py'        : TestDecl(False, UnknownTestModule),
    'test_math.py'           : TestDecl(False, OutputTestModule),
    'test_md5.py'            : TestDecl(False, OutputTestModule),
    'test_mhlib.py'          : TestDecl(True, UTModuleMainTest),
    'test_mimetools.py'      : TestDecl(True, UTModuleMainTest),
    'test_mimetypes.py'      : TestDecl(True, UTModuleMainTest),
    'test_minidom.py'        : TestDecl(False, UnknownTestModule),
    'test_mmap.py'           : TestDecl(False, OutputTestModule),
    'test_module.py'         : TestDecl(False, UnknownTestModule),
    'test_mpz.py'            : TestDecl(False, UnknownTestModule),
    'test_multifile.py'      : TestDecl(True, UTModuleMainTest),
    'test_mutants.py'        : TestDecl(False, UnknownTestModule),
    'test_netrc.py'          : TestDecl(True, UTModuleMainTest),
    'test_new.py'            : TestDecl(False, OutputTestModule),
    'test_nis.py'            : TestDecl(False, OutputTestModule),
    'test_normalization.py'  : TestDecl(False, UTModuleMainTest),
    'test_ntpath.py'         : TestDecl(False, UnknownTestModule),
    'test_opcodes.py'        : TestDecl(False, OutputTestModule),
    'test_openpty.py'        : TestDecl(False, OutputTestModule),
    'test_operations.py'     : TestDecl(False, OutputTestModule),
    'test_operator.py'       : TestDecl(True,  UTModuleMainTest),
    'test_optparse.py'       : TestDecl(False, UTModuleMainTest),
    'test_os.py'             : TestDecl(True, UTModuleMainTest),
    'test_ossaudiodev.py'    : TestDecl(False, OutputTestModule),
    'test_parser.py'         : TestDecl(True,  UTModuleMainTest),
        #rev 10840: 18 of 18 tests fail

    'test_pep247.py'         : TestDecl(False, UnknownTestModule),
    'test_pep263.py'         : TestDecl(False, UnknownTestModule),
    'test_pep277.py'         : TestDecl(False, UTModuleMainTest),
    'test_pickle.py'         : TestDecl(False, UTModuleMainTest),
    'test_pickletools.py'    : TestDecl(False, UnknownTestModule),
    'test_pkg.py'            : TestDecl(False, OutputTestModule),
    'test_pkgimport.py'      : TestDecl(True, UTModuleMainTest),
    'test_plistlib.py'       : TestDecl(False, UTModuleMainTest),
    'test_poll.py'           : TestDecl(False, OutputTestModule),
    'test_popen.py'          : TestDecl(False, OutputTestModule),
    'test_popen2.py'         : TestDecl(False, OutputTestModule),
    'test_posix.py'          : TestDecl(True, UTModuleMainTest),
    'test_posixpath.py'      : TestDecl(True, UTModuleMainTest),
    'test_pow.py'            : TestDecl(True, UTModuleMainTest),
    'test_pprint.py'         : TestDecl(True,  UTModuleMainTest),
    'test_profile.py'        : TestDecl(True, OutputTestModule),
    'test_profilehooks.py'   : TestDecl(True,  UTModuleMainTest),
    'test_pty.py'            : TestDecl(False, OutputTestModule),
    'test_pwd.py'            : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: pwd

    'test_pyclbr.py'         : TestDecl(False, UTModuleMainTest),
    'test_pyexpat.py'        : TestDecl(False, OutputTestModule),
    'test_queue.py'          : TestDecl(False, UnknownTestModule),
    'test_quopri.py'         : TestDecl(False, UTModuleMainTest),
    'test_random.py'         : TestDecl(False, UTModuleMainTest),
        #rev 10840: Uncaught app-level exception:
        #class WichmannHill_TestBasicOps(TestBasicOps):
        #File "test_random.py", line 125 in WichmannHill_TestBasicOps
        #gen = random.WichmannHill()
        #AttributeError: 'module' object has no attribute 'WichmannHill'

    'test_re.py'             : TestDecl(False, UTModuleMainTest),
        #rev 10840: 7 of 47 tests fail

    'test_regex.py'          : TestDecl(False, OutputTestModule),
    'test_repr.py'           : TestDecl(False, UTModuleMainTest),
        #rev 10840: 6 of 12 tests fail. Always minor stuff like
        #'<function object at 0x40db3e0c>' != '<built-in function hash>'

    'test_resource.py'       : TestDecl(False, OutputTestModule),
    'test_rfc822.py'         : TestDecl(True, UTModuleMainTest),
    'test_rgbimg.py'         : TestDecl(False, OutputTestModule),
    'test_richcmp.py'        : TestDecl(False, UTModuleMainTest),
        #rev 10840: 1 of 11 test fails. The failing one had an infinite recursion.

    'test_robotparser.py'    : TestDecl(True, UTModuleMainTest),
    'test_rotor.py'          : TestDecl(False, OutputTestModule),
    'test_sax.py'            : TestDecl(False, UnknownTestModule),
    'test_scope.py'          : TestDecl(False, OutputTestModule),
    'test_scriptpackages.py' : TestDecl(False, UTModuleMainTest),
    'test_select.py'         : TestDecl(False, UnknownTestModule),
    'test_sets.py'           : TestDecl(True, UTModuleMainTest),
    'test_sgmllib.py'        : TestDecl(True,  UTModuleMainTest),
    'test_sha.py'            : TestDecl(True, UTModuleMainTest, modified=True),
        # one test is taken out (too_slow_test_case_3), rest passses 
    'test_shelve.py'         : TestDecl(True, UTModuleMainTest),
    'test_shlex.py'          : TestDecl(True, UTModuleMainTest),
    'test_shutil.py'         : TestDecl(True, UTModuleMainTest),
    'test_signal.py'         : TestDecl(False, OutputTestModule),
    'test_slice.py'          : TestDecl(False, UnknownTestModule),
    'test_socket.py'         : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: thread

    'test_socket_ssl.py'     : TestDecl(False, UTModuleMainTest),
    'test_socketserver.py'   : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: thread

    'test_softspace.py'      : TestDecl(False, UnknownTestModule),
    'test_sort.py'           : TestDecl(False, UnknownTestModule),
    'test_str.py'            : TestDecl(False, UTModuleMainTest),
        #rev 10840: at least two tests fail, after several hours I gave up waiting for the rest

    'test_strftime.py'       : TestDecl(False, UnknownTestModule),
    'test_string.py'         : TestDecl(True,  UTModuleMainTest),
    'test_stringprep.py'     : TestDecl(False, UnknownTestModule),
    'test_strop.py'          : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: strop

    'test_strptime.py'       : TestDecl(False, UTModuleMainTest),
        #rev 10840: 1 of 42 test fails: seems to be some regex problem

    'test_struct.py'         : TestDecl(False, UnknownTestModule),
    'test_structseq.py'      : TestDecl(False, UnknownTestModule),
    'test_sunaudiodev.py'    : TestDecl(False, UnknownTestModule),
    'test_sundry.py'         : TestDecl(False, UnknownTestModule),
    'test_support.py'        : TestDecl(False, UnknownTestModule),
    'test_symtable.py'       : TestDecl(False, UnknownTestModule),
    'test_syntax.py'         : TestDecl(True, UTModuleMainTest),
    'test_sys.py'            : TestDecl(True,  UTModuleMainTest),
    'test_tarfile.py'        : TestDecl(False, UTModuleMainTest),
        #rev 10840: 13 of 13 test fail

    'test_tempfile.py'       : TestDecl(False, UTModuleMainTest),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_textwrap.py'       : TestDecl(True,  UTModuleMainTest),
    'test_thread.py'         : TestDecl(False, OutputTestModule),
    'test_threaded_import.py': TestDecl(False, UTModuleMainTest),
    'test_threadedtempfile.py': TestDecl(False, OutputTestModule),
        #rev 10840: ImportError: thread

    'test_threading.py'      : TestDecl(False, UnknownTestModule),
        #rev 10840: ImportError: thread

    'test_time.py'           : TestDecl(True, UTModuleMainTest),
    'test_timeout.py'        : TestDecl(False, UTModuleMainTest),
        #rev 10840: Uncaught interp-level exception: Same place as test_cfgparser

    'test_timing.py'         : TestDecl(False, UnknownTestModule),
    'test_tokenize.py'       : TestDecl(False, OutputTestModule),
    'test_trace.py'          : TestDecl(True,  UTModuleMainTest),
    'test_traceback.py'      : TestDecl(False, UTModuleMainTest),
        #rev 10840: 2 of 2 tests fail

    'test_types.py'          : TestDecl(False, OutputTestModule, modified=True),
        #rev 10920: fails with: 
        #   E       vereq(a[::], a)
        #   >       (application-level) TypeError: an integer is required
        #   [/home/hpk/pypy-dist/pypy/lib/test2/test_types.py:217]
        
    'test_ucn.py'            : TestDecl(False, UTModuleMainTest),
    'test_unary.py'          : TestDecl(True, UTModuleMainTest),
    'test_unicode.py'        : TestDecl(False, UTModuleMainTest),
    'test_unicode_file.py'   : TestDecl(False, OutputTestModule),
    'test_unicodedata.py'    : TestDecl(False, UTModuleMainTest),
    'test_univnewlines.py'   : TestDecl(True, UTModuleMainTest),
    'test_unpack.py'         : TestDecl(False, UnknownTestModule),
    'test_urllib.py'         : TestDecl(True, UTModuleMainTest),
        #rev 10840: 10 of 10 tests fail

    'test_urllib2.py'        : TestDecl(False, UnknownTestModule),
    'test_urllibnet.py'      : TestDecl(False, UTModuleMainTest),
    'test_urlparse.py'       : TestDecl(True,  UTModuleMainTest),
    'test_userdict.py'       : TestDecl(True, UTModuleMainTest),
        #rev 10840: 5 of 25 tests fail

    'test_userlist.py'       : TestDecl(False, UTModuleMainTest),
        #rev 10840: at least two tests fail, after several hours I gave up waiting for the rest

    'test_userstring.py'     : TestDecl(False, UTModuleMainTest),
    'test_uu.py'             : TestDecl(False, UTModuleMainTest),
        #rev 10840: 1 of 9 test fails

    'test_warnings.py'       : TestDecl(True, UTModuleMainTest),
    'test_wave.py'           : TestDecl(False, UnknownTestModule),
    'test_weakref.py'        : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: _weakref

    'test_whichdb.py'        : TestDecl(False, UTModuleMainTest),
    'test_winreg.py'         : TestDecl(False, OutputTestModule),
    'test_winsound.py'       : TestDecl(False, UTModuleMainTest),
    'test_xmllib.py'         : TestDecl(False, UTModuleMainTest),
    'test_xmlrpc.py'         : TestDecl(False, UTModuleMainTest),
        #rev 10840: 2 of 5 tests fail

    'test_xpickle.py'        : TestDecl(False, UTModuleMainTest),
    'test_xreadline.py'      : TestDecl(False, OutputTestModule),
    'test_zipfile.py'        : TestDecl(False, UnknownTestModule),
    'test_zipimport.py'      : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: zlib

    'test_zlib.py'           : TestDecl(False, UTModuleMainTest),
        #rev 10840: ImportError: zlib
}

class RegrDirectory(py.test.collect.Directory): 
    testmap = testmap
    def run(self): 
        l = []
        items = self.testmap.items() 
        items.sort(lambda x,y: cmp(x[0].lower(), y[0].lower()))
        for name, testdecl in items: 
            if testdecl.enabled: 
                l.append(name) 
        return l 

    def join(self, name): 
        if name in self.testmap: 
            testdecl = self.testmap[name]
            fspath = self.fspath.join(name) 
            return testdecl.testclass(fspath, parent=self, testdecl=testdecl) 
        else: 
            raise ValueError("no test type specified for %s" %(name,))

Directory = RegrDirectory

