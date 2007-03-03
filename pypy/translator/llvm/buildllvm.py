import os
import sys

import py

from pypy.translator.llvm.log import log
from pypy.translator.llvm.pyxwrapper import write_pyx_wrapper 
from pypy.translator.tool import stdoutcapture
from pypy.translator.tool.cbuild import make_c_from_pyxfile

import distutils.sysconfig

def llvm_is_on_path():
    if py.path.local.sysfind("llvm-as") is None or \
       py.path.local.sysfind("llvm-gcc") is None:
        return False 
    return True

def _exe_version(exe, cache={}):
    try:
        v =  cache[exe]
    except KeyError:
        v = os.popen(exe + ' -version 2>&1').read()
        v = ''.join([c for c in v if c.isdigit()])
        v = int(v) / 10.0
        cache[exe] = v
    return v

llvm_version = lambda: _exe_version('llvm-as')

def postfix():
    if llvm_version() >= 2.0:
        return '.i32'
    else:
        return ''

def _exe_version2(exe):
    v = os.popen(exe + ' --version 2>&1').read()
    i = v.index(')')
    v = v[i+2:].split()[0].split('.')
    major, minor = v[0], ''.join([c for c in v[1] if c.isdigit()])
    v = float(major) + float(minor) / 10.0
    return v

gcc_version = lambda: _exe_version2('gcc')
llvm_gcc_version = lambda: _exe_version2('llvm-gcc')

def optimizations(simple, use_gcc):

    if simple:
        opts = "-globaldce -adce -deadtypeelim -simplifycfg -raiseallocs " \
               "-simplifycfg -mem2reg -simplifycfg -verify "
    else:
#         opts = """-verify -lowersetjmp -funcresolve -raiseallocs -simplifycfg -mem2reg -globalopt -globaldce -ipconstprop -deadargelim -instcombine -simplifycfg -basiccg -prune-eh -inline -simplify-libcalls -basiccg -argpromotion -raise -tailduplicate -simplifycfg -scalarrepl -instcombine -break-crit-edges -condprop -tailcallelim -simplifycfg -reassociate -loopsimplify -licm -lcssa -loop-unswitch -instcombine -indvars -loop-unroll -instcombine -lowerswitch -instcombine -load-vn -gcse -sccp -instcombine -break-crit-edges -condprop -dse -mergereturn -adce -simplifycfg -deadtypeelim -constmerge -verify"""
        cmd = "gccas /dev/null -o /dev/null -debug-pass=Arguments 2>&1"
        gccas_output = os.popen(cmd)
        opts = gccas_output.read()[17:-1] + " "
        opts += "-globalopt -constmerge -ipsccp -deadargelim -inline " \
                "-instcombine -scalarrepl -globalsmodref-aa -licm -load-vn " \
                "-gcse -instcombine -simplifycfg -globaldce "
        #opts += "-inline-threshold=200 "   #default: 200
    return opts

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
    py.process.cmdexec(cmd)


def build_module(genllvm):
    # use pyrex to create module for CPython
    postfix = ''
    basename = genllvm.filename.purebasename + '_wrapper' + postfix + '.pyx'
    pyxfile = genllvm.filename.new(basename = basename)
    write_pyx_wrapper(genllvm, pyxfile)
    return make_module_from_llvm(genllvm, genllvm.filename, pyxfile=pyxfile)

def build_standalone(genllvm, exename):
    return make_module_from_llvm(genllvm, genllvm.filename, exe_name=exename)

def make_module_from_llvm(genllvm, llvmfile,
                          pyxfile=None, optimize=True, exe_name=None,
                          profile=False, cleanup=False, use_gcc=True):

    if exe_name:
        use_gcc = genllvm.config.translation.llvm_via_c

    # where we are building
    dirpath = llvmfile.dirpath()

    # change into dirpath and store current path to change back
    lastdir = str(py.path.local())
    os.chdir(str(dirpath))

    b = llvmfile.purebasename

    # run llvm assembler and optimizer
    simple_optimizations = not optimize
    opts = optimizations(simple_optimizations, use_gcc)
    if llvm_version() < 2.0:
        cmds = ["llvm-as < %s.ll | opt %s -f -o %s.bc" % (b, opts, b)]
    else: #we generate 1.x .ll files, so upgrade these first
        cmds = ["llvm-upgrade < %s.ll | llvm-as | opt %s -f -o %s.bc" % (b, opts, b)]

    object_files = ["-L/sw/lib"]
    library_files = genllvm.db.gcpolicy.gc_libraries()
    gc_libs = ' '.join(['-l' + lib for lib in library_files])

    if sys.platform == 'darwin':
        libdir = '/sw/' + "/lib"
        gc_libs_path = '-L%s -ldl' % libdir
    else:
        gc_libs_path = '-static'

    if pyxfile:
        modname = pyxfile.purebasename
        source_files = ["%s.c" % modname]
    else:
        source_files = []

    if not use_gcc:
        cmds.append("llc %s.bc -f -o %s.s" % (b, b))
        cmds.append("as %s.s -o %s.o" % (b, b))

        if exe_name:
            cmd = "gcc -O3 %s.o %s %s -lm -pipe -o %s" % (b, gc_libs_path, gc_libs, exe_name)
            cmds.append(cmd)
        object_files.append("%s.o" % b)
    else:
        cmds.append("llc %s.bc -march=c -f -o %s.c" % (b, b))
        if exe_name:
            if genllvm.config.translation.profopt is not None:
                cmd = "gcc -fprofile-generate %s.c -c -O3 -pipe -o %s.o" % (b, b)
                cmds.append(cmd)
                cmd = "gcc -fprofile-generate %s.o %s %s -lm -pipe -o %s_gen" % \
                      (b, gc_libs_path, gc_libs, exe_name)
                cmds.append(cmd)
                cmds.append("./%s_gen %s"%(exe_name, genllvm.config.translation.profopt))
                cmd = "gcc -fprofile-use %s.c -c -O3 -pipe -o %s.o" % (b, b)
                cmds.append(cmd)
                cmd = "gcc -fprofile-use %s.o %s %s -lm -pipe -o %s" % \
                      (b, gc_libs_path, gc_libs, exe_name)
            else:
                cmd = "gcc %s.c -c -O3 -pipe" % b
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
        # compress file
        if upx and not upx.startswith('which'): 
            cmds.append('upx ' + exe_name)

    try:
        c = stdoutcapture.Capture(mixed_out_err = True)
        log.build("working in", py.path.local())
        try:
            try:
                for cmd in cmds:
                    log.build(cmd)
                    py.process.cmdexec(cmd)
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
    finally:
        os.chdir(str(lastdir))

    if pyxfile:
        return modname, str(dirpath)

    if exe_name:
        exe_path = str(llvmfile.dirpath().join(exe_name))
        return exe_path
