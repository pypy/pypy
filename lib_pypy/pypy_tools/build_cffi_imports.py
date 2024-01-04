from __future__ import print_function
import sys, shutil, os, tempfile, hashlib
import sysconfig
from os.path import join

try:
    import _multiprocessing
except ImportError:
    # The only function we need from multiprocessing is cpu_count(), which is
    # written in the pure Python part of multiprocessing. We can make it work
    # in environments that don't have _multiprocessing by adding an empty
    # module in place of _multiprocessing.
    import types
    sys.modules['_multiprocessing'] = types.ModuleType('fake _multiprocessing')
import multiprocessing

# do not use the long-running runsubprocess._run here, since building some of
# the extensions enable importing them later
os.environ['PYPY_DONT_RUN_SUBPROCESS'] = '1'

class MissingDependenciesError(Exception):
    pass


cffi_build_scripts = [
    ("_ctypes._ctypes_cffi",
     "_ctypes/_ctypes_build.py" if sys.platform == 'darwin' else None),
    ("_pypy_util_cffi_inner", "_pypy_util_build.py"), # this needs to come before ssl
    ("_ssl", "_ssl_build.py"),
    ("sqlite3", "_sqlite3_build.py"),
    ("audioop", "_audioop_build.py"),
    ("_tkinter", "_tkinter/tklib_build.py"),
    ("curses", "_curses_build.py" if sys.platform != "win32" else None),
    ("syslog", "_syslog_build.py" if sys.platform != "win32" else None),
    ("gdbm", "_gdbm_build.py"  if sys.platform != "win32" else None),
    ("grp", "_pwdgrp_build.py" if sys.platform != "win32" else None),
    ("resource", "_resource_build.py" if sys.platform != "win32" else None),
    # ("_decimal", "_decimal_build.py"),  # issue 3024
    ("xx", None),    # for testing: 'None' should be completely ignored
    ]

# for distribution, we may want to fetch dependencies not provided by
# the OS, such as a recent openssl/libressl.
curdir = os.path.abspath(os.path.dirname(__file__))
deps_destdir = os.path.join(curdir, 'dest')
configure_args = ['./configure',
            '--prefix=/usr',
            '--disable-shared',
            '--enable-silent-rules',
            '--disable-dependency-tracking',
        ]
cffi_dependencies = {
    '_ssl': ('https://www.openssl.org/source/openssl-3.0.12.tar.gz',
              'f93c9e8edde5e9166119de31755fc87b4aa34863662f67ddfcba14d0b6b69b61',
              [
               ['./config', '--prefix=/usr', 'no-shared', 'enable-fips'],
               ['make', '-s', '-j', str(multiprocessing.cpu_count())],
               ['make', 'install', 'DESTDIR={}/'.format(deps_destdir)],
              ]),
    'lzma': ('https://github.com/tukaani-project/xz/releases/download/v5.2.12/xz-5.2.12.tar.gz',
             '61bda930767dcb170a5328a895ec74cab0f5aac4558cdda561c83559db582a13',
             [configure_args,
              ['make', '-s', '-j', str(multiprocessing.cpu_count())],
              ['make', 'install', 'DESTDIR={}/'.format(deps_destdir)],
             ]),
}

if sys.platform == "darwin":
    # this does not compile on the linux buildbot, linker is missing '_history_list'
    cffi_dependencies['gdbm'] = (
              'https://ftp.gnu.org/gnu/gdbm/gdbm-1.23.tar.gz',
              '74b1081d21fff13ae4bd7c16e5d6e504a4c26f7cde1dca0d963a484174bbcacd',
              [configure_args + ['--without-readline'],
              ['make', '-s', '-j', str(multiprocessing.cpu_count())],
              ['make', 'install', 'DESTDIR={}/'.format(deps_destdir)],
             ])

def _unpack_tarfile(filename, extract_dir):
    """Unpack tar/tar.gz/tar.bz2/tar.xz `filename` to `extract_dir`
    """
    import tarfile  # late import for breaking circular dependency
    try:
        tarobj = tarfile.open(filename)
    except tarfile.TarError:
        raise ReadError(
            "%s is not a compressed or uncompressed tar file" % filename)
    try:
        tarobj.extractall(extract_dir)
    finally:
        tarobj.close()

def _sha256(filename):
    dgst = hashlib.sha256()

    with open(filename, 'rb') as fp:
        dgst.update(fp.read())
    return dgst.hexdigest()


def _build_dependency(name, patches=[]):
    import shutil
    from rpython.tool.runsubprocess import run_subprocess

    try:
        url, dgst, build_cmds = cffi_dependencies[name]
    except KeyError:
        return 0, None, None

    archive_dir = os.path.join(tempfile.gettempdir(), 'pypy-archives')

    if not os.path.isdir(archive_dir):
        os.makedirs(archive_dir)

    archive = os.path.join(archive_dir, url.rsplit('/', 1)[-1])

    # next, fetch the archive to disk, if needed
    if not os.path.exists(archive) or _sha256(archive) != dgst:
        # Since we do not have a functioning ssl module, we cannot use urllib
        # On one of the buildbots, wget is broken
        if os.environ.get("USE_CURL", False):
            print('fetching archive via curl', url, file=sys.stderr)
            status, stdout, stderr = run_subprocess('curl', ['-sSLo', archive, url])
        else:
            print('fetching archive via wget', url, file=sys.stderr)
            status, stdout, stderr = run_subprocess('wget', ['-O', archive, url])
        if status != 0:
            return status, stdout, stderr

    # make sure the hash matches
    if _sha256(archive) != dgst:
        return 1, '{} archive {} hash mismatch'.format(name, archive), ''

    shutil.rmtree(deps_destdir, ignore_errors=True)
    os.makedirs(deps_destdir)

    # extract the into our destination directory
    print('unpacking archive', archive, file=sys.stderr)
    _unpack_tarfile(archive, deps_destdir)

    sources = os.path.join(
        deps_destdir,
        os.path.basename(archive).rsplit('.', 2)[0],
    )

    # apply any patches
    if patches:
        for patch in patches:
            print('applying patch', patch, file=sys.stderr)
            status, stdout, stderr = run_subprocess(
                '/usr/bin/patch', ['-p1', '-i', patch], cwd=sources,
            )

            if status != 0:
                return status, stdout, stderr
    env = os.environ
    if sys.platform == 'darwin':
        target = sysconfig.get_config_var('MACOSX_DEPLOYMENT_TARGET')
        if target:
            # override the value for building support libraries
            env = os.environ.copy()
            env['MACOSX_DEPLOYMENT_TARGET'] = target
            print('setting MACOSX_DEPLOYMENT_TARGET to "{}"'.format(target))
        
    for args in build_cmds:
        print('running', ' '.join(args), 'in', sources, file=sys.stderr)
        status, stdout, stderr = run_subprocess(args[0], args[1:],
                                                cwd=sources, env=env)
        if status != 0:
            break
    return status, stdout, stderr

def create_cffi_import_libraries(pypy_c, options, basedir, only=None,
                                 embed_dependencies=False, rebuild=False):
    from rpython.tool.runsubprocess import run_subprocess
    print('calling create_cffi_import_libraries with "embed_dependencies"', embed_dependencies)

    shutil.rmtree(str(join(basedir,'lib_pypy','__pycache__')),
                  ignore_errors=True)
    # be sure pip, setuptools are installed in a fresh pypy
    # allows proper functioning of cffi on win32 with newer vc compilers
    # XXX move this to a build slave step?
    env = os.environ
    if sys.platform == 'win32':
        env = os.environ.copy()
        env['INCLUDE'] = r'..\externals\include;' + env.get('INCLUDE', '')
        env['LIB'] = r'..\externals\lib;' + env.get('LIB', '')
        env['PATH'] = r'..\externals\bin;' + env.get('PATH', '')
    status, stdout, stderr = run_subprocess(str(pypy_c), ['-c', 'import setuptools'])
    if status  != 0:
        status, stdout, stderr = run_subprocess(str(pypy_c), ['-m', 'ensurepip'])
    failures = []

    for key, module in cffi_build_scripts:
        if only and key not in only:
            print("* SKIPPING", key, '(not specified in --only)')
            continue
        if module is None or getattr(options, 'no_' + key, False):
            continue
        if not rebuild:
            # the key is the module name, has it already been built?
            status, stdout, stderr = run_subprocess(str(pypy_c),
                                         ['-c', 'import %s' % key], env=env)
            if status  == 0:
                print('*', ' %s already built' % key, file=sys.stderr)
                continue

        if module.endswith('.py'):
            args = [module]
            cwd = str(join(basedir,'lib_pypy'))
        else:
            args = ['-c', 'import ' + module]
            cwd = None

        print('*', ' '.join(args), file=sys.stderr)
        if embed_dependencies and key in cffi_dependencies:
            status, stdout, stderr = _build_dependency(key)
            if status != 0:
                failures.append((key, module))
                print("stdout:")
                print(stdout.decode('utf-8'))
                print("stderr:")
                print(stderr.decode('utf-8'))
                continue

            env['CPPFLAGS'] = '-I{}/usr/include {}'.format(
                            deps_destdir, env.get('CPPFLAGS', ''))
            env['LDFLAGS'] = '-L{}/usr/lib64 -L{}/usr/lib {}'.format(
                            deps_destdir, deps_destdir, env.get('LDFLAGS', ''))

        try:
            status, bld_stdout, bld_stderr = run_subprocess(str(pypy_c), args,
                                                    cwd=cwd, env=env)
            if status != 0:
                print("stdout:")
                print(bld_stdout, file=sys.stderr)
                print("stderr:")
                print(bld_stderr, file=sys.stderr)
                raise RuntimeError('building {} failed'.format(key))
            elif key in ("_ssl",):
                print("stdout:")
                print(bld_stdout, file=sys.stderr)
                print("stderr:")
                print(bld_stderr, file=sys.stderr)
        except:
            import traceback;traceback.print_exc()
            failures.append((key, module))
        else:
            # Make sure it worked
            status, stdout, stderr = run_subprocess(str(pypy_c),
                         ['-c', "print('testing {0}'); import {0}".format(key)],
                         env=env)
            if status != 0:
                failures.append((key, module))
                print("build stdout:")
                print(bld_stdout, file=sys.stderr)
                print("build stderr:")
                print(bld_stderr, file=sys.stderr)
                print("test stdout:")
                print(stdout, file=sys.stderr)
                print("test stderr:")
                print(stderr, file=sys.stderr)
        if os.path.exists(deps_destdir):
            shutil.rmtree(deps_destdir, ignore_errors=True)
    return failures

if __name__ == '__main__':
    import argparse
    if '__pypy__' not in sys.builtin_module_names:
        print('Call with a pypy interpreter', file=sys.stderr)
        sys.exit(1)

    tool_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    base_dir = os.path.dirname(os.path.dirname(tool_dir))
    sys.path.insert(0, base_dir)

    class Options(object):
        pass

    parser = argparse.ArgumentParser(description='Build all cffi backends in lib_pypy')
    parser.add_argument('--exefile', dest='exefile', default=sys.executable,
                        help='instead of executing sys.executable' \
                             ' you can specify an alternative pypy vm here')
    parser.add_argument('--rebuild', dest='rebuild', action='store_true',
        help='Rebuild the module even if it already appears to have been built.')
    parser.add_argument('--only', dest='only', default=None,
                        help='Only build the modules delimited by a colon. E.g. _ssl,sqlite')
    parser.add_argument('--embed-dependencies', dest='embed_dependencies', action='store_true',
        help='embed dependencies for distribution')
    args = parser.parse_args()

    exename = join(os.getcwd(), args.exefile)
    basedir = exename

    while not os.path.exists(join(basedir,'include')):
        _basedir = os.path.dirname(basedir)
        if _basedir == basedir:
            raise ValueError('interpreter %s not inside pypy repo', 
                                 str(exename))
        basedir = _basedir
    options = Options()
    if args.only is None:
        only = None
    else:
        only = set(args.only.split(','))
    failures = create_cffi_import_libraries(exename, options, basedir, only=only,
                                            embed_dependencies=args.embed_dependencies,
                                            rebuild=args.rebuild)
    if len(failures) > 0:
        print('*** failed to build the CFFI modules %r' % (
            [f[1] for f in failures],), file=sys.stderr)
        print('''
PyPy can still be used as long as you don't need the corresponding
modules.  If you do need them, please install the missing headers and
libraries (see error messages just above) and then re-run the command:

    %s %s
''' % (sys.executable, ' '.join(sys.argv)), file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # monkey patch a failure, just to test
        print('This line should be followed by a traceback', file=sys.stderr)
        for k, m in cffi_build_scripts:
            setattr(options, 'no_' + k, True)
        must_fail = '_missing_build_script.py'
        assert not os.path.exists(str(join(join(basedir,'lib_pypy'),must_fail)))
        cffi_build_scripts.append('should_fail', must_fail)
        failures = create_cffi_import_libraries(exename, options, basedir, only=only)
        assert len(failures) == 1
