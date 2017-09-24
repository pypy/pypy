#!/usr/bin/env python
from __future__ import print_function

import os, sys
import argparse, re, shutil, tarfile, urllib2


DEBUG_TESTBUILD = False

TARBALL_CACHE_DIR = 'releases'

ROOT_KEEP = ['build', 'cmake', 'config', 'core', 'etc', 'interpreter',
             'io', 'LICENSE', 'net', 'Makefile', 'CMakeLists.txt', 'math',
             'main'] # main only needed in more recent root b/c of rootcling
ROOT_CORE_KEEP = ['CMakeLists.txt', 'base', 'clib', 'clingutils', 'cont',
                  'dictgen', 'foundation', 'lzma', 'macosx', 'meta',
                  'metacling', 'metautils', 'rootcling_stage1', 'textinput',
                  'thread', 'unix', 'utils', 'winnt', 'zip']
ROOT_IO_KEEP = ['CMakeLists.txt', 'io', 'rootpcm']
ROOT_NET_KEEP = ['CMakeLists.txt', 'net']
ROOT_MATH_KEEP = ['CMakeLists.txt', 'mathcore']
ROOT_ETC_KEEP = ['Makefile.arch', 'class.rules', 'cmake', 'dictpch',
                 'gdb-backtrace.sh', 'gitinfo.txt', 'helgrind-root.supp',
                 'hostcert.conf', 'system.plugins-ios',
                 'valgrind-root-python.supp', 'valgrind-root.supp', 'vmc']

ROOT_EXPLICIT_REMOVE = ['core/base/v7', 'math/mathcore/v7', 'io/io/v7']


ERR_RELEASE_NOT_FOUND = 2


#
## CLI arguments
#
class ReleaseValidation(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if not re.match(r'6\.\d\d\.\d\d', value):
            raise argparse.ArgumentTypeError(
                "release number should of the form '6.dd.dd'")
        setattr(namespace, self.dest, value)
        return value

parser = argparse.ArgumentParser(
    description='Build PyPi package for cppyy containing the minimum of ROOT')
parser.add_argument('-r', '--release', type=str, nargs='?',
                    action=ReleaseValidation, help='ROOT release to use')

args = parser.parse_args()


#
## ROOT source pull and cleansing
#
def clean_directory(directory, keeplist, trim_cmake=True):
    removed_entries = []
    for entry in os.listdir(directory):
        if entry[0] == '.' or entry in keeplist:
            continue
        removed_entries.append(entry)
        entry = os.path.join(directory, entry)
        print('now removing', entry)
        if os.path.isdir(entry):
            shutil.rmtree(entry)
        else:
            os.remove(entry)

    if not trim_cmake:
        return

    # now take the removed entries out of the CMakeLists.txt
    if removed_entries:
        inp = os.path.join(directory, 'CMakeLists.txt')
        print('trimming', inp)
        outp = inp+'.new'
        new_cml = open(outp, 'w')
        for line in open(inp).readlines():
            if ('add_subdirectory' in line) or\
               ('COMMAND' in line and 'copy' in line) or\
               ('ROOT_ADD_TEST_SUBDIRECTORY' in line) or\
               ('install(DIRECTORY' in line):
                for sub in removed_entries:
                    if sub in line:
                        line = '#'+line
                        break
            new_cml.write(line)
        new_cml.close()
        os.rename(outp, inp)
    else:
        print('reusing existing %s/CMakeLists.txt' % (directory,))
 

class ReleaseValidation(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if not re.match(r'6\.\d\d\.\d\d', value):
            raise argparse.ArgumentTypeError(
                "release number should of the form '6.dd.dd'")
        setattr(namespace, self.dest, value)
        return value

parser = argparse.ArgumentParser(
    description='Build PyPi package for cppyy containing the minimum of ROOT')
parser.add_argument('-r', '--release', type=str, nargs='?',
                    action=ReleaseValidation, help='ROOT release to use')

args = parser.parse_args()

if not os.path.exists(TARBALL_CACHE_DIR):
    os.mkdir(TARBALL_CACHE_DIR)

if args.release:
  # use provided release
    fn = 'root_v%s.source.tar.gz' % args.release
    addr = 'https://root.cern.ch/download/'+fn
    if not os.path.exists(os.path.join(TARBALL_CACHE_DIR, fn)):
        try:
            print('retrieving', fn)
            resp = urllib2.urlopen(addr, fn)
            out = open(os.path.join(TARBALL_CACHE_DIR, fn), 'wb')
            out.write(resp.read())
            out.close()
        except urllib2.HTTPError:
            print('release %s not found' % args.release)
            sys.exit(ERR_RELEASE_NOT_FOUND)
    else:
        print('reusing', fn, 'from local directory')
else:
    print('provide release ... getting latest release is not yet implemented ...')
    sys.exit(1)
  # get latest and set fn, args.release, etc.

# construct version for package
args.version = ''
testnext = False
for c in args.release:
    if testnext:
        testnext = False
        if c == '0':
            continue
    if c == '.':
        testnext = True
    args.version += c
args.version += '.0'

fn = os.path.join(TARBALL_CACHE_DIR, fn)
pkgdir = os.path.join('root-'+args.release)
if not os.path.exists(pkgdir):
    print('now extracting', args.release)
    tf = tarfile.TarFile.gzopen(fn)
    tf.extractall()
    tf.close()
else:
    print('reusing existing directory', pkgdir)

# remove everything except for the listed set of libraries
os.chdir(pkgdir)

clean_directory(os.path.curdir, ROOT_KEEP)
clean_directory('core',         ROOT_CORE_KEEP)
clean_directory('etc',          ROOT_ETC_KEEP, trim_cmake=False)
clean_directory('io',           ROOT_IO_KEEP)
clean_directory('math',         ROOT_MATH_KEEP)
clean_directory('net',          ROOT_NET_KEEP)


# trim main (only need rootcling)
print('trimming main')
for entry in os.listdir('main/src'):
    if entry != 'rootcling.cxx':
        os.remove('main/src/'+entry)
inp = 'main/CMakeLists.txt'
outp = inp+'.new'
new_cml = open(outp, 'w')
for line in open(inp).readlines():
    if ('ROOT_EXECUTABLE' in line or\
        'SET_TARGET_PROPERTIES' in line) and\
       not 'rootcling' in line:
        line = '#'+line
    new_cml.write(line)
new_cml.close()
os.rename(outp, inp)


# remove afterimage and ftgl explicitly
print('trimming externals')
for cmf in ['AfterImage', 'FTGL']:
    os.remove('cmake/modules/Find%s.cmake' % (cmf,))
inp = 'cmake/modules/SearchInstalledSoftware.cmake'
outp = inp+'.new'
now_stripping = False
new_cml = open(outp, 'w')
for line in open(inp).readlines():
    if '#---Check for ftgl if needed' == line[0:28] or\
       '#---Check for AfterImage' == line[0:24]:
        now_stripping = True
    elif '#---Check' == line[0:9]:
        now_stripping = False
    if now_stripping:
        line = '#'+line
    new_cml.write(line)
new_cml.close()
os.rename(outp, inp)

inp = 'cmake/modules/RootBuildOptions.cmake'
outp = inp+'.new'
new_cml = open(outp, 'w')
for line in open(inp).readlines():
    if 'ROOT_BUILD_OPTION(builtin_ftgl' in line or\
       'ROOT_BUILD_OPTION(builtin_afterimage' in line:
        line = '#'+line
    new_cml.write(line)
new_cml.close()
os.rename(outp, inp)


# remove testing and examples
print('trimming testing')
inp = 'CMakeLists.txt'
outp = inp+'.new'
now_stripping = False
new_cml = open(outp, 'w')
for line in open(inp).readlines():
    if '#---Configure Testing using CTest' == line[0:33] or\
       '#---hsimple.root' == line[0:16]:
        now_stripping = True
    elif '#---Packaging' == line[0:13] or\
         '#---version' == line[0:11]:
        now_stripping = False
    if now_stripping:
        line = '#'+line
    new_cml.write(line)
new_cml.close()
os.rename(outp, inp)

print('trimming RootCPack')
inp = 'cmake/modules/RootCPack.cmake'
outp = inp+'.new'
new_cml = open(outp, 'w')
for line in open(inp):
    if 'README.txt' in line:
        line = '#'+line
    new_cml.write(line)
new_cml.close()
os.rename(outp, inp)

# some more explicit removes:
for dir_to_remove in ROOT_EXPLICIT_REMOVE:
    try:
        shutil.rmtree(dir_to_remove)
    except OSError:
        pass

# special fixes
inp = 'core/base/src/TVirtualPad.cxx'
outp = inp+'.new'
new_cml = open(outp, 'w')
for line in open(inp):
    if '#include "X3DBuffer.h"' == line[0:22]:
        line = """//#include "X3DBuffer.h"
typedef struct _x3d_sizeof_ {
   int  numPoints;
   int  numSegs;
   int  numPolys;
} Size3D;
"""
    new_cml.write(line)
new_cml.close()
os.rename(outp, inp)

inp = 'math/mathcore/src/Fitter.cxx'
if os.path.exists(inp):
    outp = inp+'.new'
    new_cml = open(outp, 'w')
    for line in open(inp):
        if '#include "TF1.h"' in line:
            continue
        new_cml.write(line)
    new_cml.close()
    os.rename(outp, inp)

# done
os.chdir(os.path.pardir)

# debugging: run a test build
if DEBUG_TESTBUILD:
    print('running a debug test build')
    tb = "test_builddir"
    if os.path.exists(tb):
        shutil.rmtree(tb)
    os.mkdir(tb)
    os.chdir(tb)
    os.system('cmake ../%s -DCMAKE_INSTALL_PREFIX=../install -Dminimal=ON -Dasimage=OFF' % pkgdir)
    os.system('make -j 32')


#
## package creation
#
countdown = 0
pidir = 'Package-'+args.release
print('creating package', pidir)
if not os.path.exists(pidir):
    os.mkdir(pidir)
os.chdir(pidir); countdown += 1

print('creating LICENSE.txt')
with open('LICENSE.txt', 'w') as outp:
    outp.write("""There are three main parts:

 LLVM: distributed under University of Illinois/NCSA Open Source License
   https://opensource.org/licenses/UoI-NCSA.php
 ROOT: distributed under LGPL 2.1
   https://root.cern.ch/license
 Cppyy: distributed under LBNL BSD
   https://fedoraproject.org/wiki/Licensing/LBNLBSD
""")

print('creating MANIFEST.in')
with open('MANIFEST.in', 'w') as outp:
    outp.write("""# Include the license file
include LICENSE.txt

# Include the data files
recursive-include src *
""")

print('creating README.rst')
with open('README.rst', 'w') as outp:
    outp.write("""PyPy cling-support
==================

----

Find the documentation here:
  http://doc.pypy.org/en/latest/cppyy.html
""")

print('creating setup.cfg')
with open('setup.cfg', 'w') as outp:
    outp.write("""[bdist_wheel]
universal=0
""")

print('creating setup.py')
with open('setup.py', 'w') as outp:
    outp.write("""import os, sys, subprocess
from setuptools import setup, find_packages
from distutils import log
from distutils.command.build import build as _build
from setuptools.command.install import install as _install
from distutils.sysconfig import get_python_lib
from distutils.errors import DistutilsSetupError
from codecs import open

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

builddir = None
def get_builddir():
    global builddir
    if builddir is None:
        topdir = os.getcwd()
        builddir = os.path.join(topdir, 'builddir')
    return builddir

srcdir = None
def get_srcdir():
    global srcdir
    if srcdir is None:
        topdir = os.getcwd()
        srcdir = os.path.join(topdir, 'src', 'backend')
    return srcdir

class my_cmake_build(_build):
    def __init__(self, dist, *args, **kwargs):
        _build.__init__(self, dist, *args, **kwargs)
        # TODO: can't seem to find a better way of getting hold of
        # the install_lib parameter during the build phase ...
        prefix = ''
        try:
            prefix = dist.get_command_obj('install').install_lib
        except AttributeError:
            pass
        if not prefix:
            prefix = get_python_lib(1, 0)
        self.prefix = os.path.join(prefix, 'cppyy_backend')

    def run(self):
        # base run
        _build.run(self)

        # custom run
        log.info('Now building libcppyy_backend.so and dependencies')
        builddir = get_builddir()
        srcdir = get_srcdir()
        if not os.path.exists(builddir):
            log.info('Creating build directory %s ...' % builddir)
            os.makedirs(builddir)

        os.chdir(builddir)
        log.info('Running cmake for cppyy_backend')
        if subprocess.call([
                'cmake', srcdir, '-Dminimal=ON -Dasimage=OFF',
                '-DCMAKE_INSTALL_PREFIX='+self.prefix]) != 0:
            raise DistutilsSetupError('Failed to configure cppyy_backend')

        nprocs = os.getenv("MAKE_NPROCS")
        if nprocs:
            try:
                ival = int(nprocs)
                nprocs = '-j'+nprocs
            except ValueError:
                log.warn("Integer expected for MAKE_NPROCS, but got %s (ignored)", nprocs)
                nprocs = '-j1'
        else:
            nprocs = '-j1'
        log.info('Now building cppyy_backend and dependencies ...')
        if subprocess.call(['make', nprocs]) != 0:
            raise DistutilsSetupError('Failed to build cppyy_backend')

        log.info('build finished')

class my_libs_install(_install):
    def run(self):
        # base install
        _install.run(self)

        # custom install
        log.info('Now installing libcppyy_backend.so and dependencies')
        builddir = get_builddir()
        if not os.path.exists(builddir):
            raise DistutilsSetupError('Failed to find build dir!')
        os.chdir(builddir)

        prefix = self.install_lib
        log.info('Now installing in %s ...', prefix)
        if subprocess.call(['make', 'install']) != 0:
            raise DistutilsSetupError('Failed to install cppyy_backend')

        log.info('install finished')

    def get_outputs(self):
        outputs = _install.get_outputs(self)
        outputs.append(os.path.join(self.install_lib, 'cppyy_backend'))
        return outputs

setup(
    name='PyPy-cppyy-backend',
""")
    outp.write("    version='%s', # corresponds to ROOT %s, extra number is for packager\n"\
         % (args.version, args.release))
    outp.write("""    description='Cling support for PyPy',
    long_description=long_description,

    url='http://pypy.org',

    # Author details
    author='PyPy Developers',
    author_email='pypy-dev@python.org',

    license='LLVM: UoI-NCSA; ROOT: LGPL 2.1; Cppyy: LBNL BSD',

    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',

        'Topic :: Software Development',
        'Topic :: Software Development :: Interpreters',

        #'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: C',
        'Programming Language :: C++',

        'Natural Language :: English'
    ],

    keywords='interpreter development',

    packages=find_packages('src', ['backend']),
    include_package_data=True,

    extras_require={
    },

    cmdclass = {
        'build': my_cmake_build,
        'install': my_libs_install,
    },
)
""")


print('creating src ... ROOT part')
if not os.path.exists('src'):
    os.mkdir('src')
os.chdir('src'); countdown += 1
if not os.path.exists('backend'):
    src = os.path.join(os.path.pardir, os.path.pardir, pkgdir)
    print('now copying', src)
    shutil.copytree(src, 'backend')

print('creating src ... cppyy part')
os.chdir('backend'); countdown += 1
if not os.path.exists('cppyy'):
    os.mkdir('cppyy')
    os.chdir('cppyy'); countdown += 1

    with open('CMakeLists.txt', 'w') as outp:
        outp.write("""############################################################################
# CMakeLists.txt file for building cppyy package
############################################################################

ROOT_GLOB_SOURCES(sources ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cxx)
set_source_files_properties(${sources} COMPILE_FLAGS "-fomit-frame-pointer -fvisibility=hidden -DRPY_EXTERN=RPY_EXPORTED -DRPYTHON_LL2CTYPES")

add_definitions(${CLING_CXXFLAGS})

ROOT_LINKER_LIBRARY(cppyy_backend ${sources}
                               LIBRARIES ${CMAKE_DL_LIBS}
                               DEPENDENCIES Core Cling RIO Thread)

add_dependencies(cppyy_backend CLING)
""")

    os.mkdir('src')
    os.chdir('src'); countdown += 1
    print('pulling cppyy/clingcwrapper.cxx from pypy')
    base = 'https://bitbucket.org/pypy/pypy/raw/default/pypy/module/cppyy/'
    for cppyy_file in ['src/callcontext.h', 'include/capi.h', 'src/clingcwrapper.cxx',
                       'include/clingcwrapper.h', 'include/cpp_cppyy.h', 'include/cppyy.h']:
        resp = urllib2.urlopen(base+cppyy_file)
        with open(os.path.basename(cppyy_file), 'w') as outp:
            outp.write(resp.read())

    # fix include
    inp = 'capi.h'
    outp = inp+'.new'
    new_cml = open(outp, 'w')
    for line in open(inp).readlines():
        if 'src/precommondefs.h' in line:
            line = '#include "precommondefs.h"\n'
        new_cml.write(line)
    new_cml.close()
    os.rename(outp, inp)

    with open('precommondefs.h', 'w') as outp:
        outp.write("""/***** Start of precommondefs.h *****/

/* This is extracted from pyconfig.h from CPython.  It sets the macros
   that affect the features we get from system include files.
   It must not #include anything. */

#ifndef __PYPY_PRECOMMONDEFS_H
#define __PYPY_PRECOMMONDEFS_H


/* Define on Darwin to activate all library features */
#define _DARWIN_C_SOURCE 1
/* This must be set to 64 on some systems to enable large file support. */
#define _FILE_OFFSET_BITS 64
/* Define on Linux to activate all library features */
#define _GNU_SOURCE 1
/* This must be defined on some systems to enable large file support. */
#define _LARGEFILE_SOURCE 1
/* Define on NetBSD to activate all library features */
#define _NETBSD_SOURCE 1
/* Define to activate features from IEEE Stds 1003.1-2001 */
#ifndef _POSIX_C_SOURCE
#  define _POSIX_C_SOURCE 200112L
#endif
/* Define on FreeBSD to activate all library features */
#define __BSD_VISIBLE 1
#define __XSI_VISIBLE 700
/* Windows: winsock/winsock2 mess */
#define WIN32_LEAN_AND_MEAN
#ifdef _WIN64
   typedef          __int64 Signed;
   typedef unsigned __int64 Unsigned;
#  define SIGNED_MIN LLONG_MIN
#else
   typedef          long Signed;
   typedef unsigned long Unsigned;
#  define SIGNED_MIN LONG_MIN
#endif

#if !defined(RPY_ASSERT) && !defined(RPY_LL_ASSERT) && !defined(NDEBUG)
#  define NDEBUG
#endif


/* All functions and global variables declared anywhere should use
   one of the following attributes:

   RPY_EXPORTED:  the symbol is exported out of libpypy-c.so.

   RPY_EXTERN:    the symbol is not exported out of libpypy-c.so, but
                  otherwise works like 'extern' by being available to
                  other C sources.

   static:        as usual, this means the symbol is local to this C file.

   Don't use _RPY_HIDDEN directly.  For tests involving building a custom
   .so, translator/tool/cbuild.py overrides RPY_EXTERN so that it becomes
   equal to RPY_EXPORTED.

   Any function or global variable declared with no attribute at all is
   a bug; please report or fix it.
*/
#ifdef __GNUC__
#  define RPY_EXPORTED extern __attribute__((visibility("default")))
#  define _RPY_HIDDEN  __attribute__((visibility("hidden")))
#else
#  define RPY_EXPORTED extern __declspec(dllexport)
#  define _RPY_HIDDEN  /* nothing */
#endif
#ifndef RPY_EXTERN
#  define RPY_EXTERN   extern _RPY_HIDDEN
#endif


#endif /* __PYPY_PRECOMMONDEFS_H */

/***** End of precommondefs.h *****/
""")

# back up to pip package top
for i in range(countdown-1):
    os.chdir(os.path.pardir)

# add cppyy module to cmake
os.chdir('src/backend')
inp = 'CMakeLists.txt'
print('adding cppyy to cmake')
outp = inp+'.new'
new_cml = open(outp, 'w')
for line in open(inp).readlines():
    if 'add_subdirectory' in line and 'net' in line:
        line += 'add_subdirectory (cppyy)\n'
    new_cml.write(line)
new_cml.close()
os.rename(outp, inp)

# done!
