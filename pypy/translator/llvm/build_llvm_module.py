"""
Build a Python module out of llvmfile and a Pyrex wrapper file.
"""

import os, sys

from py.process import cmdexec 
from py import path 
import py

from pypy.translator.tool.cbuild import make_c_from_pyxfile
from pypy.translator.tool import stdoutcapture
from pypy.translator.llvm.log import log

SIMPLE_OPTIMIZATION_SWITCHES = (" ".join([
    # kill code - hopefully to speed things up
    "-globaldce -adce -deadtypeelim -simplifycfg",

    # call %malloc -> malloc inst
    "-raiseallocs",

    # clean up disgusting code
    "-simplifycfg",

    # kill useless allocas
    "-mem2reg",

    # clean up disgusting code
    "-simplifycfg",

    "-verify",
    ]))

flags = os.popen("gccas /dev/null -o /dev/null -debug-pass=Arguments 2>&1").read()[17:-1].split()

#if int(os.popen("opt --help 2>&1").read().find('-heap2stack')) >= 0:
#    flags.insert(flags.index("-inline")+1, "-heap2stack -debug")

OPTIMIZATION_SWITCHES = " ".join(flags)

def compile_module(module, source_files, object_files, library_files):
    open("%s_setup.py" % module, "w").write(str(py.code.Source(
        '''
        from distutils.core import setup
        from distutils.extension import Extension
        setup(name="%(module)s",
            ext_modules = [Extension(
                name = "%(module)s",
                sources = %(source_files)s,
                libraries = %(library_files)s,
                extra_objects = %(object_files)s)])
        ''' % locals())))
    cmd ="python %s_setup.py build_ext --inplace --force" % module
    log.build(cmd)
    cmdexec(cmd)

def make_module_from_llvm(genllvm, llvmfile, pyxfile=None, optimize=True, exe_name=None):
    include_dir = py.magic.autopath().dirpath()
    dirpath = llvmfile.dirpath()
    lastdir = path.local()
    os.chdir(str(dirpath))
    b = llvmfile.purebasename
    if pyxfile:
        modname = pyxfile.purebasename
        source_files = [ "%s.c" % modname ]
    else:
        source_files = []
    from distutils.sysconfig import EXEC_PREFIX
    object_files = ["-L%s/lib" % EXEC_PREFIX]
    library_files = genllvm.gcpolicy.gc_libraries()
    gc_libs = ' '.join(['-l' + lib for lib in library_files])

    if optimize:
        optimization_switches = OPTIMIZATION_SWITCHES
    else:
        optimization_switches = SIMPLE_OPTIMIZATION_SWITCHES

    #XXX outcommented for testing merging extern.ll in main .ll file
    #cmds = ["llvm-as %s.ll" % b]
    #
    #bcfile = dirpath.join("externs", "externs_linked.bc")
    #cmds.append("llvm-link %s.bc %s -o %s_all.bc" % (b, str(bcfile), b))
    #ball = str(dirpath.join('%s_all.bc' % b))
    #cmds.append("opt %s %s -f -o %s.bc" % (OPTIMIZATION_SWITCHES, ball, b))

    use_gcc = True
    profile = False
    cleanup = False

    if sys.platform == 'darwin':
        import distutils.sysconfig
        libdir = distutils.sysconfig.EXEC_PREFIX + "/lib"
        gc_libs_path = '-L%s -ldl' % libdir
    else:
        gc_libs_path = '-static'

    cmds = ["llvm-as < %s.ll | opt %s -f -o %s.bc" % (b, optimization_switches, b)]
    if not use_gcc:
        cmds.append("llc %s %s.bc -f -o %s.s" % (genllvm.exceptionpolicy.llc_options(), b, b))
        cmds.append("as %s.s -o %s.o" % (b, b))
        if exe_name:
            cmd = "gcc %s.o %s %s -lm -pipe -o %s" % (b, gc_libs_path, gc_libs, exe_name)
            cmds.append(cmd)
        object_files.append("%s.o" % b)
    else:
        cmds.append("llc %s %s.bc -march=c -f -o %s.c" % (genllvm.exceptionpolicy.llc_options(), b, b))
        if exe_name:
            cmd = "gcc %s.c -c -O2 -pipe" % b
            if profile:
                cmd += ' -pg'
            else:
                cmd += ' -fomit-frame-pointer'
            cmds.append(cmd)
            cmd = "gcc %s.o %s %s -lm -pipe -o %s" % (b, gc_libs_path, gc_libs, exe_name)
            if profile:
                cmd += ' -pg'
            cmds.append(cmd)
        source_files.append("%s.c" % b)

    if cleanup and exe_name and not profile:
        cmds.append('strip ' + exe_name)
        upx = os.popen('which upx 2>&1').read()
        if upx and not upx.startswith('which'): #compress file even further
            cmds.append('upx ' + exe_name)

    try:
        if pyxfile:
            log.build("modname", modname)
        c = stdoutcapture.Capture(mixed_out_err = True)
        log.build("working in", path.local())
        try:
            try:
                for cmd in cmds:
                    log.build(cmd)
                    cmdexec(cmd)
                if pyxfile:
                    make_c_from_pyxfile(pyxfile)
                    compile_module(modname, source_files, object_files, library_files)
            finally:
                foutput, ferror = c.done()
        except:
            data = 'OUTPUT:\n' + foutput.read() + '\n\nERROR:\n' + ferror.read()
            if pyxfile:
                fdump = open("%s.errors" % modname, "w")
                fdump.write(data)
                fdump.close()
            log.build(data)
            raise
        # XXX do we need to do some check on fout/ferr?
        # XXX not a nice way to import a module
        if pyxfile:
            log.build("inserting path to sys.path", dirpath)
            sys.path.insert(0, '.')
            cmd = "import %(modname)s as testmodule" % locals()
            log.build(cmd)
            exec cmd
            sys.path.pop(0)
    finally:
        os.chdir(str(lastdir))
    if pyxfile:
        return testmodule
    if exe_name:
        exe_path = str(llvmfile.dirpath().join(exe_name))
        return exe_path
