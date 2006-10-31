"""
Backend for the JVM.
"""

import os, os.path, subprocess

import py
from pypy.tool.udir import udir
from pypy.translator.translator import TranslationContext
from pypy.translator.oosupport.genoo import GenOO

from pypy.translator.jvm.generator import JasminGenerator
from pypy.translator.jvm.option import getoption
from pypy.translator.jvm.database import Database
from pypy.translator.jvm.log import log
from pypy.translator.jvm.node import EntryPoint, Function
from pypy.translator.jvm.opcodes import opcodes

class JvmError(Exception):
    """ Indicates an error occurred in the JVM runtime """
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
        """
        self.tmpdir = tmpdir
        self.package = package
        self.compiled = False

        # Compute directory where .java files are
        self.javadir = self.tmpdir
        for subpkg in package.split('.'):
            self.javadir = self.javadir.join(subpkg)

        # Compute directory where .class files should go
        self.classdir = self.javadir

    def compile(self):
        """
        Compiles the .java sources into .class files, ready for execution.
        Raises a JvmError if compilation fails.
        """
        javac = getoption('javac')
        javafiles = [f for f in self.javadir.listdir()
                     if f.endswith('.java')]
        res = subprocess.call([javac] + javafiles)
        if res: raise JvmError('Failed to compile!')
        else: self.compiled = True

    def execute(self, args):
        """
        Executes the compiled sources in a separate process.  Returns the
        output as a string.  The 'args' are provided as arguments,
        and will be converted to strings.
        """
        assert self.compiled
        strargs = [str(a) for a in args]
        cmd = [getoption('java'), '%s.Main' % self.package]
        pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
        return pipe.read()
        
def generate_source_for_function(func, annotation):
    
    """
    Given a Python function and some hints about its argument types,
    generates JVM sources.  Returns the JvmGeneratedSource object.
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
    jvm = GenJvm(tmpdir, t, EntryPoint(main_graph, True))
    return jvm.generate_source()

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
    
    def __init__(self, tmpdir, translator, entrypoint):
        """
        'tmpdir' --- where the generated files will go.  In fact, we will
        put our binaries into the directory pypy/jvm
        'translator' --- a TranslationContext object
        'entrypoint' --- if supplied, an object with a render method
        """
        GenOO.__init__(self, tmpdir, translator, entrypoint)
        self.jvmsrc = JvmGeneratedSource(tmpdir, getoption('package'))

    def generate_source(self):
        """ Creates the sources, and returns a JvmGeneratedSource object
        for manipulating them """
        GenOO.generate_source(self)
        return self.jvmsrc

    def create_assembler(self):
        """ Creates and returns a Generator object according to the
        configuration.  Right now, however, there is only one kind of
        generator: JasminGenerator """
        return JasminGenerator(
            self.db, self.jvmsrc.javadir, self.jvmsrc.package)
        
        
