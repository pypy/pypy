"""

test configuration(s) for running CPython's regression
test suite on top of PyPy

"""
import py.path as pypath
import pytest
import sys
import re

# the following adds command line options as a side effect!
from pypy.conftest import option as pypy_option

from pypy.tool.pytest.confpath import pypydir, testdir

pytest_plugins = "resultlog",
rsyncdirs = ['.', '../pypy/']

#
# Interfacing/Integrating with pytest's collection process
#

def pytest_addoption(parser):
    group = parser.getgroup("compliance testing options")
    group.addoption('-T', '--timeout', action="store", type="string",
                    default="1000", dest="timeout",
                    help="fail a test module after the given timeout. "
                         "specify in seconds or 'NUMmp' aka Mega-Pystones")
    group.addoption('--pypy', action="store", type="string", dest="pypy",
                    help="use given pypy executable to run lib-python tests. ")
    group.addoption('--filter', action="store", type="string", default=None,
                    dest="unittest_filter", help="Similar to -k, XXX")

def gettimeout(timeout):
    from rpython.translator.test import rpystone
    if timeout.endswith('mp'):
        megapystone = float(timeout[:-2])
        t, stone = pystone.Proc0(10000)
        pystonetime = t/stone
        seconds = megapystone * 1000000 * pystonetime
        return seconds
    return float(timeout)

# ________________________________________________________________________
#
# classification of all tests files (this is ongoing work)
#

class RegrTest:
    """ Regression Test Declaration."""
    def __init__(self, basename, skip=False):
        self.basename = basename
        self.skip = skip
        assert self.getfspath().check(), "%r not found!" % (basename,)

    def ismodified(self):
        #XXX: ask hg
        return None

    def getfspath(self):
        return testdir.join(self.basename)

testmap = [
    RegrTest('test___all__.py'),
    RegrTest('test___future__.py'),
    RegrTest('test__locale.py'),
    RegrTest('test__opcode.py'),
    RegrTest('test__osx_support.py'),
    RegrTest('test__xxsubinterpreters.py'),
    RegrTest('test_abc.py'),
    RegrTest('test_abstract_numbers.py'),
    RegrTest('test_aifc.py'),
    RegrTest('test_argparse.py'),
    RegrTest('test_array.py'),
    RegrTest('test_asdl_parser.py'),
    RegrTest('test_ast.py'),
    RegrTest('test_asyncgen.py'),
    RegrTest('test_asynchat.py'),
    RegrTest('test_asyncio'),
    RegrTest('test_asyncore.py'),
    RegrTest('test_atexit.py'),
    RegrTest('test_audioop.py'),
    RegrTest('test_audit.py'),
    RegrTest('test_augassign.py'),
    RegrTest('test_base64.py'),
    RegrTest('test_baseexception.py'),
    RegrTest('test_bdb.py'),
    RegrTest('test_bigaddrspace.py'),
    RegrTest('test_bigmem.py'),
    RegrTest('test_binascii.py'),
    RegrTest('test_binhex.py'),
    RegrTest('test_binop.py'),
    RegrTest('test_bisect.py'),
    RegrTest('test_bool.py'),
    RegrTest('test_buffer.py'),
    RegrTest('test_bufio.py'),
    RegrTest('test_builtin.py'),
    RegrTest('test_bytes.py'),
    RegrTest('test_bz2.py'),
    RegrTest('test_c_locale_coercion.py'),
    RegrTest('test_calendar.py'),
    RegrTest('test_call.py'),
    RegrTest('test_capi'),
    RegrTest('test_cgi.py'),
    RegrTest('test_cgitb.py'),
    RegrTest('test_charmapcodec.py'),
    RegrTest('test_check_c_globals.py'),
    RegrTest('test_class.py'),
    RegrTest('test_clinic.py'),
    RegrTest('test_cmath.py'),
    RegrTest('test_cmd.py'),
    RegrTest('test_cmd_line.py'),
    RegrTest('test_cmd_line_script.py'),
    RegrTest('test_code.py'),
    RegrTest('test_code_module.py'),
    RegrTest('test_codeccallbacks.py'),
    RegrTest('test_codecencodings_cn.py'),
    RegrTest('test_codecencodings_hk.py'),
    RegrTest('test_codecencodings_iso2022.py'),
    RegrTest('test_codecencodings_jp.py'),
    RegrTest('test_codecencodings_kr.py'),
    RegrTest('test_codecencodings_tw.py'),
    RegrTest('test_codecmaps_cn.py'),
    RegrTest('test_codecmaps_hk.py'),
    RegrTest('test_codecmaps_jp.py'),
    RegrTest('test_codecmaps_kr.py'),
    RegrTest('test_codecmaps_tw.py'),
    RegrTest('test_codecs.py'),
    RegrTest('test_codeop.py'),
    RegrTest('test_collections.py'),
    RegrTest('test_colorsys.py'),
    RegrTest('test_compare.py'),
    RegrTest('test_compile.py'),
    RegrTest('test_compileall.py'),
    RegrTest('test_complex.py'),
    RegrTest('test_concurrent_futures.py', skip="XXX: deadlocks" if sys.platform == 'win32' else False),
    RegrTest('test_configparser.py'),
    RegrTest('test_contains.py'),
    RegrTest('test_context.py'),
    RegrTest('test_contextlib.py'),
    RegrTest('test_contextlib_async.py'),
    RegrTest('test_copy.py'),
    RegrTest('test_copyreg.py'),
    RegrTest('test_coroutines.py'),
    RegrTest('test_cprofile.py'),
    RegrTest('test_crashers.py'),
    RegrTest('test_crypt.py'),
    RegrTest('test_csv.py'),
    RegrTest('test_ctypes.py'),
    RegrTest('test_curses.py'),
    RegrTest('test_dataclasses.py'),
    RegrTest('test_datetime.py'),
    RegrTest('test_dbm.py'),
    RegrTest('test_dbm_dumb.py'),
    RegrTest('test_dbm_gnu.py'),
    RegrTest('test_dbm_ndbm.py'),
    RegrTest('test_decimal.py'),
    RegrTest('test_decorators.py'),
    RegrTest('test_defaultdict.py'),
    RegrTest('test_deque.py'),
    RegrTest('test_descr.py'),
    RegrTest('test_descrtut.py'),
    RegrTest('test_devpoll.py'),
    RegrTest('test_dict.py'),
    RegrTest('test_dict_version.py', skip="implementation detail"),
    RegrTest('test_dictcomps.py'),
    RegrTest('test_dictviews.py'),
    RegrTest('test_difflib.py'),
    RegrTest('test_dis.py'),
    RegrTest('test_distutils.py'),
    RegrTest('test_doctest.py'),
    RegrTest('test_doctest2.py'),
    RegrTest('test_docxmlrpc.py'),
    RegrTest('test_dtrace.py'),
    RegrTest('test_dynamic.py'),
    RegrTest('test_dynamicclassattribute.py'),
    RegrTest('test_eintr.py'),
    RegrTest('test_email'),
    RegrTest('test_embed.py'),
    RegrTest('test_ensurepip.py'),
    RegrTest('test_enum.py'),
    RegrTest('test_enumerate.py'),
    RegrTest('test_eof.py'),
    RegrTest('test_epoll.py'),
    RegrTest('test_errno.py'),
    RegrTest('test_exception_hierarchy.py'),
    RegrTest('test_exception_variations.py'),
    RegrTest('test_exceptions.py'),
    RegrTest('test_extcall.py'),
    RegrTest('test_faulthandler.py'),
    RegrTest('test_fcntl.py'),
    RegrTest('test_file.py'),
    RegrTest('test_file_eintr.py'),
    RegrTest('test_filecmp.py'),
    RegrTest('test_fileinput.py'),
    RegrTest('test_fileio.py'),
    RegrTest('test_finalization.py'),
    RegrTest('test_float.py'),
    RegrTest('test_flufl.py'),
    RegrTest('test_fnmatch.py'),
    RegrTest('test_fork1.py'),
    RegrTest('test_format.py'),
    RegrTest('test_fractions.py'),
    RegrTest('test_frame.py'),
    RegrTest('test_frozen.py'),
    RegrTest('test_fstring.py'),
    RegrTest('test_ftplib.py'),
    RegrTest('test_funcattrs.py'),
    RegrTest('test_functools.py'),
    RegrTest('test_future.py'),
    RegrTest('test_future3.py'),
    RegrTest('test_future4.py'),
    RegrTest('test_future5.py'),
    RegrTest('test_gc.py', skip="implementation detail"),
    RegrTest('test_gdb.py', skip="not applicable"),
    RegrTest('test_generator_stop.py'),
    RegrTest('test_generators.py'),
    RegrTest('test_genericalias.py'),
    RegrTest('test_genericclass.py'),
    RegrTest('test_genericpath.py'),
    RegrTest('test_genexps.py'),
    RegrTest('test_getopt.py'),
    RegrTest('test_getpass.py'),
    RegrTest('test_gettext.py'),
    RegrTest('test_glob.py'),
    RegrTest('test_global.py'),
    RegrTest('test_grammar.py'),
    RegrTest('test_graphlib.py'),
    RegrTest('test_grp.py'),
    RegrTest('test_gzip.py'),
    RegrTest('test_hash.py'),
    RegrTest('test_hashlib.py'),
    RegrTest('test_heapq.py'),
    RegrTest('test_hmac.py'),
    RegrTest('test_html.py'),
    RegrTest('test_htmlparser.py'),
    RegrTest('test_http_cookiejar.py'),
    RegrTest('test_http_cookies.py'),
    RegrTest('test_httplib.py'),
    RegrTest('test_httpservers.py'),
    RegrTest('test_idle.py'),
    RegrTest('test_imaplib.py'),
    RegrTest('test_imghdr.py'),
    RegrTest('test_imp.py'),
    RegrTest('test_import'),
    RegrTest('test_importlib'),
    RegrTest('test_index.py'),
    RegrTest('test_inspect.py'),
    RegrTest('test_interpreters.py'),
    RegrTest('test_int.py'),
    RegrTest('test_int_literal.py'),
    RegrTest('test_io.py'),
    RegrTest('test_ioctl.py'),
    RegrTest('test_ipaddress.py'),
    RegrTest('test_isinstance.py'),
    RegrTest('test_iter.py'),
    RegrTest('test_iterlen.py'),
    RegrTest('test_itertools.py'),
    RegrTest('test_json'),
    RegrTest('test_keyword.py'),
    RegrTest('test_keywordonlyarg.py'),
    RegrTest('test_kqueue.py'),
    RegrTest('test_largefile.py'),
    RegrTest('test_lib2to3.py'),
    RegrTest('test_linecache.py'),
    RegrTest('test_list.py'),
    RegrTest('test_listcomps.py'),
    RegrTest('test_lltrace.py'),
    RegrTest('test_locale.py'),
    RegrTest('test_logging.py'),
    RegrTest('test_long.py'),
    RegrTest('test_longexp.py'),
    RegrTest('test_lzma.py'),
    RegrTest('test_macurl2path.py'),
    RegrTest('test_mailbox.py'),
    RegrTest('test_mailcap.py'),
    RegrTest('test_marshal.py'),
    RegrTest('test_math.py'),
    RegrTest('test_memoryio.py'),
    RegrTest('test_memoryview.py'),
    RegrTest('test_metaclass.py'),
    RegrTest('test_mimetypes.py'),
    RegrTest('test_minidom.py'),
    RegrTest('test_mmap.py'),
    RegrTest('test_module.py'),
    RegrTest('test_modulefinder.py'),
    RegrTest('test_msilib.py'),
    RegrTest('test_multibytecodec.py'),
    RegrTest('test_multiprocessing_fork.py'),
    RegrTest('test_multiprocessing_forkserver.py'),
    RegrTest('test_multiprocessing_main_handling.py'),
    RegrTest('test_multiprocessing_spawn.py'),
    RegrTest('test_named_expressions.py'),
    RegrTest('test_netrc.py'),
    RegrTest('test_nis.py'),
    RegrTest('test_nntplib.py'),
    RegrTest('test_ntpath.py'),
    RegrTest('test_numeric_tower.py'),
    RegrTest('test_opcache.py'),
    RegrTest('test_opcodes.py'),
    RegrTest('test_openpty.py'),
    RegrTest('test_operator.py'),
    RegrTest('test_optparse.py'),
    RegrTest('test_ordered_dict.py'),
    RegrTest('test_os.py'),
    RegrTest('test_ossaudiodev.py'),
    RegrTest('test_osx_env.py'),
    RegrTest('test_pathlib.py'),
    RegrTest('test_patma.py'),
    RegrTest('test_pdb.py'),
    RegrTest('test_peepholer.py'),
    RegrTest('test_peg_generator'),
    RegrTest('test_pickle.py'),
    RegrTest('test_picklebuffer.py'),
    RegrTest('test_pickletools.py'),
    RegrTest('test_pipes.py'),
    RegrTest('test_pkg.py'),
    RegrTest('test_pkgutil.py'),
    RegrTest('test_platform.py'),
    RegrTest('test_plistlib.py'),
    RegrTest('test_poll.py'),
    RegrTest('test_popen.py'),
    RegrTest('test_poplib.py'),
    RegrTest('test_positional_only_arg.py'),
    RegrTest('test_posix.py'),
    RegrTest('test_posixpath.py'),
    RegrTest('test_pow.py'),
    RegrTest('test_pprint.py'),
    RegrTest('test_print.py'),
    RegrTest('test_profile.py'),
    RegrTest('test_property.py'),
    RegrTest('test_pstats.py'),
    RegrTest('test_pty.py'),
    RegrTest('test_pulldom.py'),
    RegrTest('test_pwd.py'),
    RegrTest('test_py_compile.py'),
    RegrTest('test_pyclbr.py'),
    RegrTest('test_pydoc.py'),
    RegrTest('test_pyexpat.py'),
    RegrTest('test_queue.py'),
    RegrTest('test_quopri.py'),
    RegrTest('test_raise.py'),
    RegrTest('test_random.py'),
    RegrTest('test_range.py'),
    RegrTest('test_re.py'),
    RegrTest('test_readline.py'),
    RegrTest('test_regrtest.py'),
    RegrTest('test_repl.py'),
    RegrTest('test_reprlib.py'),
    RegrTest('test_resource.py'),
    RegrTest('test_richcmp.py'),
    RegrTest('test_rlcompleter.py'),
    RegrTest('test_robotparser.py'),
    RegrTest('test_runpy.py'),
    RegrTest('test_sax.py'),
    RegrTest('test_sched.py'),
    RegrTest('test_scope.py'),
    RegrTest('test_script_helper.py'),
    RegrTest('test_secrets.py'),
    RegrTest('test_select.py'),
    RegrTest('test_selectors.py'),
    RegrTest('test_set.py'),
    RegrTest('test_setcomps.py'),
    RegrTest('test_shelve.py'),
    RegrTest('test_shlex.py'),
    RegrTest('test_shutil.py'),
    RegrTest('test_signal.py'),
    RegrTest('test_site.py'),
    RegrTest('test_slice.py'),
    RegrTest('test_smtpd.py'),
    RegrTest('test_smtplib.py'),
    RegrTest('test_smtpnet.py'),
    RegrTest('test_sndhdr.py'),
    RegrTest('test_socket.py'),
    RegrTest('test_socketserver.py'),
    RegrTest('test_sort.py'),
    RegrTest('test_source_encoding.py'),
    RegrTest('test_spwd.py'),
    RegrTest('test_sqlite.py'),
    RegrTest('test_ssl.py'),
    RegrTest('test_startfile.py'),
    RegrTest('test_stat.py'),
    RegrTest('test_statistics.py'),
    RegrTest('test_strftime.py'),
    RegrTest('test_string.py'),
    RegrTest('test_string_literals.py'),
    RegrTest('test_stringprep.py'),
    RegrTest('test_strptime.py'),
    RegrTest('test_strtod.py'),
    RegrTest('test_struct.py'),
    RegrTest('test_structseq.py'),
    RegrTest('test_subclassinit.py'),
    RegrTest('test_subprocess.py'),
    RegrTest('test_sunau.py'),
    RegrTest('test_sundry.py'),
    RegrTest('test_super.py'),
    RegrTest('test_support.py'),
    RegrTest('test_symtable.py', skip="implementation detail"),
    RegrTest('test_syntax.py'),
    RegrTest('test_sys.py'),
    RegrTest('test_sys_setprofile.py'),
    RegrTest('test_sys_settrace.py'),
    RegrTest('test_sysconfig.py'),
    RegrTest('test_sysconfig_pypy.py'),
    RegrTest('test_syslog.py'),
    RegrTest('test_tabnanny.py'),
    RegrTest('test_tarfile.py'),
    RegrTest('test_tcl.py'),
    RegrTest('test_telnetlib.py'),
    RegrTest('test_tempfile.py'),
    RegrTest('test_textwrap.py'),
    RegrTest('test_thread.py'),
    RegrTest('test_threadedtempfile.py'),
    RegrTest('test_threading.py'),
    RegrTest('test_threading_local.py'),
    RegrTest('test_threadsignals.py'),
    RegrTest('test_time.py'),
    RegrTest('test_timeit.py'),
    RegrTest('test_timeout.py'),
    RegrTest('test_tix.py'),
    RegrTest('test_tk.py'),
    RegrTest('test_tokenize.py'),
    RegrTest('test_tools', skip="CPython internal details"),
    RegrTest('test_trace.py'),
    RegrTest('test_traceback.py'),
    RegrTest('test_tracemalloc.py'),
    RegrTest('test_ttk_guionly.py'),
    RegrTest('test_ttk_textonly.py'),
    RegrTest('test_tuple.py'),
    RegrTest('test_turtle.py'),
    RegrTest('test_type_comments.py'),
    RegrTest('test_typechecks.py'),
    RegrTest('test_types.py'),
    RegrTest('test_type_annotations.py'),
    RegrTest('test_typing.py'),
    RegrTest('test_ucn.py'),
    RegrTest('test_unary.py'),
    RegrTest('test_unicode.py'),
    RegrTest('test_unicode_file.py'),
    RegrTest('test_unicode_file_functions.py'),
    RegrTest('test_unicode_identifiers.py'),
    RegrTest('test_unicodedata.py'),
    RegrTest('test_unittest.py'),
    RegrTest('test_univnewlines.py'),
    RegrTest('test_unpack.py'),
    RegrTest('test_unpack_ex.py'),
    RegrTest('test_unparse.py'),
    RegrTest('test_urllib.py'),
    RegrTest('test_urllib2.py'),
    RegrTest('test_urllib2_localnet.py'),
    RegrTest('test_urllib2net.py'),
    RegrTest('test_urllib_response.py'),
    RegrTest('test_urllibnet.py'),
    RegrTest('test_urlparse.py'),
    RegrTest('test_userdict.py'),
    RegrTest('test_userlist.py'),
    RegrTest('test_userstring.py'),
    RegrTest('test_utf8_mode.py'),
    RegrTest('test_utf8source.py'),
    RegrTest('test_uu.py'),
    RegrTest('test_uuid.py'),
    RegrTest('test_venv.py'),
    RegrTest('test_wait3.py'),
    RegrTest('test_wait4.py'),
    RegrTest('test_warnings'),
    RegrTest('test_wave.py'),
    RegrTest('test_weakref.py'),
    RegrTest('test_weakset.py'),
    RegrTest('test_webbrowser.py'),
    RegrTest('test_winconsoleio.py'),
    RegrTest('test_winreg.py'),
    RegrTest('test_winsound.py'),
    RegrTest('test_with.py'),
    RegrTest('test_wsgiref.py'),
    RegrTest('test_xdrlib.py'),
    RegrTest('test_xml_dom_minicompat.py'),
    RegrTest('test_xml_etree.py'),
    RegrTest('test_xml_etree_c.py'),
    RegrTest('test_xmlrpc.py'),
    RegrTest('test_xmlrpc_net.py'),
    RegrTest('test_xxtestfuzz.py', skip="CPython internal details"),
    RegrTest('test_xxlimited.py', skip="CPython internal details"),
    RegrTest('test_yield_from.py'),
    RegrTest('test_zipapp.py'),
    RegrTest('test_zipfile.py'),
    RegrTest('test_zipfile64.py'),
    RegrTest('test_zipimport.py'),
    RegrTest('test_zipimport_support.py'),
    RegrTest('test_zlib.py'),
    RegrTest('test_zoneinfo'),
]

def check_testmap_complete():
    listed_names = dict.fromkeys([regrtest.basename for regrtest in testmap])
    assert len(listed_names) == len(testmap)
    # names to ignore
    listed_names['test_support.py'] = True
    listed_names['test_multibytecodec_support.py'] = True
    missing = []
    for path in testdir.listdir(fil='test_*'):
        name = path.basename
        if (name.endswith('.py') or path.isdir()) and name not in listed_names:
            missing.append('    RegrTest(%r),' % (name,))
    missing.sort()
    assert not missing, "non-listed tests:\n%s" % ('\n'.join(missing),)
check_testmap_complete()

def pytest_configure(config):
    config._basename2spec = cache = {}
    for x in testmap:
        cache[x.basename] = x

def pytest_ignore_collect(path, config):
    if path.basename == '__init__.py':
        return False
    if path.isfile():
        regrtest = config._basename2spec.get(path.basename, None)
        if regrtest is None or path.dirpath() != testdir:
            return True

def pytest_collect_file(path, parent):
    if path.basename == '__init__.py':
        # handle the RegrTest for the whole subpackage here
        pkg_path = path.dirpath()
        regrtest = parent.config._basename2spec.get(pkg_path.basename, None)
        if pkg_path.dirpath() == testdir and regrtest:
            return RunFileExternal(
                pkg_path.basename, parent=parent, regrtest=regrtest)


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makemodule(path, parent):
    config = parent.config
    regrtest = config._basename2spec[path.basename]
    return RunFileExternal(path.basename, parent=parent, regrtest=regrtest)

class RunFileExternal(pytest.collect.File):
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
# invoking in a separate process: python TESTFILE
#
import os

class ReallyRunFileExternal(pytest.collect.Item):
    class ExternalFailure(Exception):
        """Failure in running subprocess"""

    def getinvocation(self, regrtest):
        fspath = regrtest.getfspath()
        python = sys.executable
        alarm_script = pypydir.join('tool', 'alarm.py')
        if sys.platform == 'win32':
            watchdog_name = 'watchdog_nt.py'
        else:
            watchdog_name = 'watchdog.py'
        watchdog_script = pypydir.join('tool', watchdog_name)

        option = self.config.option
        TIMEOUT = gettimeout(option.timeout.lower())
        execpath = pypath.local(option.pypy)
        if not execpath.check():
            execpath = pypath.local.sysfind(option.pypy)
        if not execpath:
            raise LookupError("could not find executable %r" % option.pypy)

        cmd = "%s -m test -v %s" % (execpath, fspath.purebasename)
        # add watchdog for timing out
        cmd = "%s %s %s %s" % (python, watchdog_script, TIMEOUT, cmd)
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
        if regrtest.skip:
            if regrtest.skip is True:
                msg = "obsolete or unsupported platform"
            else:
                msg = regrtest.skip
            pytest.skip(msg)
        (skipped, exit_status, test_stdout, test_stderr) = \
            self.getresult(regrtest)
        if skipped:
            pytest.skip(test_stderr.splitlines()[-1])
        if exit_status:
            raise self.ExternalFailure(test_stdout, test_stderr)

    def repr_failure(self, excinfo):
        if not excinfo.errisinstance(self.ExternalFailure):
            return super(ReallyRunFileExternal, self).repr_failure(excinfo)
        out, err = excinfo.value.args
        return out + err

    def getstatusouterr(self, cmd):
        tempdir = pytest.ensuretemp(self.fspath.basename)
        stdout = tempdir.join(self.fspath.basename) + '.out'
        stderr = tempdir.join(self.fspath.basename) + '.err'
        if sys.platform == 'win32':
            status = os.system("%s >%s 2>%s" % (cmd, stdout, stderr))
            if status >= 0:
                status = status
            else:
                status = 'abnormal termination 0x%x' % status
        else:
            if self.config.option.unittest_filter is not None:
                cmd += ' --filter %s' % self.config.option.unittest_filter
            if self.config.option.usepdb:
                cmd += ' --pdb'
            if self.config.option.capture == 'no':
                status = os.system(cmd)
                stdout.write('')
                stderr.write('')
            else:
                status = os.system("%s >>%s 2>>%s" % (cmd, stdout, stderr))
            if os.WIFEXITED(status):
                status = os.WEXITSTATUS(status)
            else:
                status = 'abnormal termination 0x%x' % status
        return status, stdout.read(mode='rU'), stderr.read(mode='rU')

    def getresult(self, regrtest):
        cmd = self.getinvocation(regrtest)
        tempdir = pytest.ensuretemp(self.fspath.basename)
        oldcwd = tempdir.chdir()
        exit_status, test_stdout, test_stderr = self.getstatusouterr(cmd)
        oldcwd.chdir()
        skipped = False
        timedout = test_stderr.rfind(26*"=" + "timedout" + 26*"=") != -1
        if not timedout:
            timedout = test_stderr.rfind("KeyboardInterrupt") != -1
        if test_stderr.rfind(26*"=" + "skipped" + 26*"=") != -1:
            skipped = True
        if not exit_status:
            # match "FAIL" but not e.g. "FAILURE", which is in the output of a
            # test in test_zipimport_support.py
            if re.search(r'\bFAIL\b', test_stdout) or re.search('[^:]ERROR', test_stderr):
                exit_status = 2

        return skipped, exit_status, test_stdout, test_stderr
