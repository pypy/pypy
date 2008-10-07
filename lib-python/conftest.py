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

dist_rsync_roots = ['.', '../pypy', '../py']
    
# 
# Interfacing/Integrating with py.test's collection process 
#

Option = py.test.config.Option 
option = py.test.config.addoptions("compliance testing options", 
    Option('-T', '--timeout', action="store", type="string", 
           default="100mp", dest="timeout", 
           help="fail a test module after the given timeout. "
                "specify in seconds or 'NUMmp' aka Mega-Pystones"),
    Option('--pypy', action="store", type="string",
           dest="pypy",  help="use given pypy executable to run lib-python tests. "
                              "This will run the tests directly (i.e. not through py.py)")
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

# ________________________________________________________________________
#
# classification of all tests files (this is ongoing work) 
#

class RegrTest: 
    """ Regression Test Declaration.""" 
    def __init__(self, basename, enabled=False, dumbtest=False,
                                 core=False,
                                 compiler=None, 
                                 usemodules = ''): 
        self.basename = basename 
        self.enabled = enabled 
        self.dumbtest = dumbtest 
        self._usemodules = usemodules.split()
        self._compiler = compiler 
        self.core = core

    def usemodules(self):
        return self._usemodules #+ pypy_option.usemodules
    usemodules = property(usemodules)

    def compiler(self): 
        return self._compiler #or pypy_option.compiler 
    compiler = property(compiler)

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
        modname = fspath.purebasename 
        space.appexec([], '''():
            from test import %(modname)s
            m = %(modname)s
            if hasattr(m, 'test_main'):
                m.test_main()
        ''' % locals())

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
    RegrTest('test_class.py', enabled=True, core=True),
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
    RegrTest('test_coercion.py', enabled=True, core=True),
    
    RegrTest('test_colorsys.py', enabled=True),
    RegrTest('test_commands.py', enabled=True),
    RegrTest('test_compare.py', enabled=True, core=True),
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
    RegrTest('test_descr.py', enabled=True, core=True, usemodules='_weakref'),
    RegrTest('test_descrtut.py', enabled=True, core=True),
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
    RegrTest('test_global.py', enabled=True, core=True),
    RegrTest('test_grammar.py', enabled=True, core=True),
    RegrTest('test_grp.py', enabled=False),
        #rev 10840: ImportError: grp

    RegrTest('test_gzip.py', enabled=False, dumbtest=1),
    RegrTest('test_hash.py', enabled=True, core=True),
    RegrTest('test_hashlib.py', enabled=True, core=True),
        # test_hashlib comes from 2.5 
    
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
    RegrTest('test_new.py', enabled=True, core=True),
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
    RegrTest('test_repr.py', enabled=True, core=True),
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
    RegrTest('test_StringIO.py', enabled=True, core=True, usemodules='cStringIO'),
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
        
    def collect(self): 
        l = []
        for x in testmap:
            name = x.basename
            regrtest = self.get(name)
            if regrtest is not None: 
                #if option.extracttests:  
                #    l.append(InterceptedRunModule(name, self, regrtest))
                #else:
                l.append(RunFileExternal(name, parent=self, regrtest=regrtest))
        return l 

Directory = RegrDirectory

class RunFileExternal(py.test.collect.Module): 
    def __init__(self, name, parent, regrtest): 
        super(RunFileExternal, self).__init__(name, parent) 
        self.regrtest = regrtest 
        self.fspath = regrtest.getfspath()

    def collect(self): 
        if self.regrtest.ismodified(): 
            name = 'modified'
        else:
            name = 'unmodified'
        return [ReallyRunFileExternal(name, parent=self)] 

#
# testmethod: 
# invoking in a seprate process: py.py TESTFILE
#
import os
import time
import socket
import getpass

class ReallyRunFileExternal(py.test.collect.Item): 
    def getinvocation(self, regrtest): 
        fspath = regrtest.getfspath() 
        python = sys.executable 
        pypy_script = pypydir.join('bin', 'py.py')
        alarm_script = pypydir.join('tool', 'alarm.py')
        watchdog_script = pypydir.join('tool', 'watchdog.py')

        regr_script = pypydir.join('tool', 'pytest', 
                                   'run-script', 'regrverbose.py')
        
        pypy_options = []
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
        if option.pypy:
            execpath = py.path.local(option.pypy)
            if not execpath.check():
                execpath = py.path.local.sysfind(option.pypy)
            if not execpath:
                raise LookupError("could not find executable %r" %(option.pypy,))
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

    def runtest(self): 
        """ invoke a subprocess running the test file via PyPy. 
            record its output into the 'result/user@host' subdirectory. 
            (we might want to create subdirectories for 
            each user, because we will probably all produce 
            such result runs and they will not be the same
            i am afraid. 
        """ 
        regrtest = self.parent.regrtest
        exit_status, test_stdout, test_stderr = self.getresult(regrtest) 
        if exit_status:
             time.sleep(0.5)   # time for a Ctrl-C to reach us :-)
             print >>sys.stdout, test_stdout
             print >>sys.stderr, test_stderr
             py.test.fail("running test failed, see stderr output below") 

    def getstatusouterr(self, cmd): 
        tempdir = py.test.ensuretemp(self.fspath.basename)
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

    def getresult(self, regrtest): 
        cmd = self.getinvocation(regrtest) 
        exit_status, test_stdout, test_stderr = self.getstatusouterr(cmd) 
        timedout = test_stderr.rfind(26*"=" + "timedout" + 26*"=") != -1 
        if not timedout: 
            timedout = test_stderr.rfind("KeyboardInterrupt") != -1
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
                    test_stderr += ("-" * 80 + "\n") + out
            else:
                if 'FAIL' in test_stdout or 'ERROR' in test_stderr:
                    outcome = 'FAIL'
                    exit_status = 2  
        elif timedout: 
            outcome = "T/O"    
        else: 
            outcome = "ERR"
        
        return exit_status, test_stdout, test_stderr

    def _keywords(self):
        lst = list(py.test.collect.Item._keywords(self))
        regrtest = self.parent.regrtest
        if regrtest.core:
            lst.append('core')
        return lst

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
