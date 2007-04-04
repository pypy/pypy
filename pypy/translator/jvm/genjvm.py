"""
Backend for the JVM.
"""

import os, os.path, sys

import py
from py.compat import subprocess
from pypy.tool.udir import udir
from pypy.translator.translator import TranslationContext
from pypy.translator.oosupport.genoo import GenOO

from pypy.translator.jvm.generator import JasminGenerator
from pypy.translator.jvm.option import getoption
from pypy.translator.jvm.database import Database
from pypy.translator.jvm.log import log
from pypy.translator.jvm.node import EntryPoint, Function
from pypy.translator.jvm.opcodes import opcodes
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.constant import \
     JVMConstantGenerator, JVMStaticMethodConst, JVMCustomDictConst
from pypy.translator.jvm.prebuiltnodes import create_interlink_node

class JvmError(Exception):
    """ Indicates an error occurred in JVM backend """

    def pretty_print(self):
        print str(self)
    pass

class JvmSubprogramError(JvmError):
    """ Indicates an error occurred running some program """
    def __init__(self, res, args, stdout, stderr):
        self.res = res
        self.args = args
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return "Error code %d running %s" % (self.res, repr(self.args))
        
    def pretty_print(self):
        JvmError.pretty_print(self)
        print "vvv Stdout vvv\n"
        print self.stdout
        print "vvv Stderr vvv\n"
        print self.stderr
        
    pass

class JvmGeneratedSource(object):
    
    """
    An object which represents the generated sources. Contains methods
    to find out where they are located, to compile them, and to execute
    them.

    For those interested in the location of the files, the following
    attributes exist:
    tmpdir --- root directory from which all files can be found (py.path obj)
    javadir --- the directory containing *.java (py.path obj)
    classdir --- the directory where *.class will be generated (py.path obj)
    package --- a string with the name of the package (i.e., 'java.util')

    The following attributes also exist to find the state of the sources:
    compiled --- True once the sources have been compiled successfully
    """

    def __init__(self, tmpdir, package):
        """
        'tmpdir' --- the base directory where the sources are located
        'package' --- the package the sources are in; if package is pypy.jvm,
        then we expect to find the sources in $tmpdir/pypy/jvm
        'jfiles' --- list of files we need to run jasmin on
        """
        self.tmpdir = tmpdir
        self.package = package
        self.compiled = False
        self.jasmin_files = None

        # Compute directory where .j files are
        self.javadir = self.tmpdir
        for subpkg in package.split('.'):
            self.javadir = self.javadir.join(subpkg)

        # Compute directory where .class files should go
        self.classdir = self.javadir

    def set_jasmin_files(self, jfiles):
        self.jasmin_files = jfiles

    def _invoke(self, args, allow_stderr):
        subp = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = subp.communicate()
        res = subp.wait()
        if res or (not allow_stderr and stderr):
            raise JvmSubprogramError(res, args, stdout, stderr)
        return stdout, stderr

    def _compile_helper(self, clsnms):
        # HACK: compile the Java helper class.  Should eventually
        # use rte.py
        tocompile = []
        for clsnm in clsnms:
            pypycls = self.classdir.join(clsnm + '.class')
            if not os.path.exists(str(pypycls)):
                tocompile.append(clsnm)
        if tocompile:
            sl = __file__.rindex('/')
            javasrcs = [__file__[:sl]+("/src/pypy/%s.java" % clsnm) for
                        clsnm in tocompile]
            self._invoke([getoption('javac'),
                          '-nowarn',
                          '-d', str(self.classdir)]+
                         javasrcs,
                         True)
        

    def compile(self):
        """
        Compiles the .java sources into .class files, ready for execution.
        """
        jascmd = [getoption('jasmin'), '-d', str(self.javadir)]

        print "Invoking jasmin on %s" % self.jasmin_files
        self._invoke(jascmd+list(self.jasmin_files), False)
        print "... completed!"
                           
        self.compiled = True
        self._compile_helper(('Callback',
                              'CustomDict',
                              'DictItemsIterator',
                              'Equals',
                              'ExceptionWrapper',
                              'Filter',
                              'FilterIterator',
                              'FilterSet',
                              'HashCode',
                              'Interlink',
                              'PyPy',
                              ))

    def _make_str(self, a):
        if isinstance(a, ootype._string):
            return a._str
        return str(a)

    def execute(self, args):
        """
        Executes the compiled sources in a separate process.  Returns the
        output as a string.  The 'args' are provided as arguments,
        and will be converted to strings.
        """
        assert self.compiled
        strargs = [self._make_str(a) for a in args]
        cmd = [getoption('java'),
               '-cp',
               str(self.javadir),
               self.package+".Main"] + strargs
        print "Invoking java to run the code"
        stdout, stderr = self._invoke(cmd, True)
        print "...done!"
        sys.stderr.write(stderr)
        return stdout
        
def generate_source_for_function(func, annotation):
    
    """
    Given a Python function and some hints about its argument types,
    generates JVM sources that call it and print the result.  Returns
    the JvmGeneratedSource object.
    """
    
    if hasattr(func, 'im_func'):
        func = func.im_func
    t = TranslationContext()
    ann = t.buildannotator()
    ann.build_types(func, annotation)
    t.buildrtyper(type_system="ootype").specialize()
    main_graph = t.graphs[0]
    if getoption('view'): t.view()
    if getoption('wd'): tmpdir = py.path.local('.')
    else: tmpdir = udir
    jvm = GenJvm(tmpdir, t, EntryPoint(main_graph, True, True))
    return jvm.generate_source()

def detect_missing_support_programs():
    def check(exechelper):
        if py.path.local.sysfind(exechelper) is None:
            py.test.skip("%s is not on your path" % exechelper)
    check(getoption('jasmin'))
    check(getoption('javac'))
    check(getoption('java'))

class GenJvm(GenOO):

    """ Master object which guides the JVM backend along.  To use,
    create with appropriate parameters and then invoke
    generate_source().  *You can not use one of these objects more than
    once.* """

    TypeSystem = lambda X, db: db # TypeSystem and Database are the same object 
    Function = Function
    Database = Database
    opcodes = opcodes
    log = log

    ConstantGenerator = JVMConstantGenerator
    CustomDictConst   = JVMCustomDictConst
    StaticMethodConst = JVMStaticMethodConst
    
    def __init__(self, tmpdir, translator, entrypoint):
        """
        'tmpdir' --- where the generated files will go.  In fact, we will
        put our binaries into the directory pypy/jvm
        'translator' --- a TranslationContext object
        'entrypoint' --- if supplied, an object with a render method
        """
        GenOO.__init__(self, tmpdir, translator, entrypoint)
        create_interlink_node(self.db)
        self.jvmsrc = JvmGeneratedSource(tmpdir, getoption('package'))

    def generate_source(self):
        """ Creates the sources, and returns a JvmGeneratedSource object
        for manipulating them """
        GenOO.generate_source(self)
        self.jvmsrc.set_jasmin_files(self.db.jasmin_files())
        return self.jvmsrc

    def create_assembler(self):
        """ Creates and returns a Generator object according to the
        configuration.  Right now, however, there is only one kind of
        generator: JasminGenerator """
        print "Uh...?"
        return JasminGenerator(
            self.db, self.jvmsrc.javadir, self.jvmsrc.package)
        
        
