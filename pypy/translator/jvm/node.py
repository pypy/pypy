"""
Rendering nodes for the JVM.  I suspect that a lot of this could be
made to be common between CLR and JVM.
"""


from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.typesystem import jStringArray, jVoid, jThrowable
from pypy.translator.jvm.typesystem import jvm_for_class, jvm_method_desc
from pypy.translator.jvm.opcodes import opcodes
from pypy.translator.oosupport.function import Function as OOFunction
import pypy.translator.jvm.generator as jvmgen

class Node(object):
    def set_db(self, db):
        self.db = db

class EntryPoint(Node):

    """
    A special node that generates the pypy.Main class which has a static
    main method.  Can be configured with a number of options for internal
    testing (see __init__)
    """

    def __init__(self, graph, expandargs):
        """
        'graph' --- The initial graph to invoke from main()
        'expandargs' --- controls whether the arguments passed to main()
        are passed as a list, or expanded to match each argument to the graph

        The 'expandargs' option deserves explanation:
        
          it will be false for a standalone build, because in that
          case we want to convert the String[] array that main() receives
          into a corresponding python List of string objects.

          it will (generally) be true when compiling individual
          functions, in which case we might be compiling an entry
          point with a signature like (a:int,b:float) in which case
          argv[1] should be converted to an integer, and argv[2]
          should be converted to a float.
        """
        self.graph = graph
        self.expand_arguments = expandargs
        pass

    # XXX --- perhaps this table would be better placed in typesystem.py
    # so as to constrain the knowledge of lltype and ootype
    _type_conversion_methods = {
        ootype.Signed:jvmgen.PYPYSTRTOINT,
        ootype.Unsigned:jvmgen.PYPYSTRTOUINT,
        lltype.SignedLongLong:jvmgen.PYPYSTRTOLONG,
        lltype.UnsignedLongLong:jvmgen.PYPYSTRTOULONG,
        ootype.Bool:jvmgen.PYPYSTRTOBOOL,
        ootype.Float:jvmgen.PYPYSTRTODOUBLE,
        ootype.Char:jvmgen.PYPYSTRTOCHAR
        }

    def render(self, gen):
        gen.begin_class('pypy.Main')
        gen.begin_function(
            'main', (), [jStringArray], jVoid, static=True)

        # Handle arguments:
        if self.expand_arguments:
            # Convert each entry into the array to the desired type by
            # invoking an appropriate helper function on each one
            for i, arg in enumerate(self.graph.getargs()):
                gen.emit(jvmgen.ICONST, i)
                gen.emit(self._type_conversion_methods[arg.concretetype])
        else:
            # Convert the array of strings to a List<String> as the
            # python method expects
            arg0 = self.graph.getargs()[0]
            assert isinstance(arg0.concretetype, ootype.List), str(arg0.concretetype)
            assert arg0._ITEMTYPE is ootype.String
            gen.load_jvm_var(0)
            gen.emit(jvmgen.PYPYARRAYTOLIST)

        # Generate a call to this method
        gen.emit(self.db.pending_function(self.graph))
        
        gen.end_function()
        gen.end_class()

class Function(OOFunction):
    
    """ Represents a function to be emitted. """
    
    def __init__(self, db, classobj, name, jargtypes,
                 jrettype, graph, is_static):
        """
        classobj: the Class object this is a part of (even static
        functions have a class)
        name: the name of the function
        jargtypes: JvmType of each argument
        jrettype: JvmType this function returns
        graph: the graph representing the body of the function
        is_static: boolean flag indicate whether func is static (!)
        """
        OOFunction.__init__(self, db, graph, name, not is_static)
        self.classnm = classobj.name
        self.jargtypes = jargtypes
        self.jrettype = jrettype
        self._block_labels = {}

    def method(self):
        """ Returns a jvmgen.Method that can invoke this function """
        if not self.is_method: opcode = jvmgen.INVOKESTATIC
        else: opcode = jvmgen.INVOKEVIRTUAL
        mdesc = jvm_method_desc(self.jargtypes, self.jrettype)
        return jvmgen.Method(self.classnm, self.name, mdesc, opcode=opcode)

    def begin_render(self):
        # Prepare argument lists for begin_function call
        lltype_to_cts = self.db.lltype_to_cts
        jargvars = []
        jargtypes = []
        for arg in self.graph.getargs():
            if arg.concretetype is ootype.Void: continue
            jargvars.append(arg)
            jargtypes.append(lltype_to_cts(arg.concretetype))

        # Determine return type
        jrettype = lltype_to_cts(self.graph.getreturnvar().concretetype)
        self.ilasm.begin_function(
            self.name, jargvars, jargtypes, jrettype, static=not self.is_method)

    def end_render(self):
        self.ilasm.end_function()

    def _create_generator(self, ilasm):
        # JVM doesn't distinguish
        return ilasm

    def _get_block_name(self, block):
        if block in self._block_labels:
            return self._block_labels[block]
        blocklbl = self.ilasm.unique_label('BasicBlock')
        self._block_labels[block] = blocklbl
        return blocklbl

    def set_label(self, blocklbl):
        self.ilasm.mark(blocklbl)

    def begin_try(self):
        self.ilasm.begin_try()

    def end_try(self):
        self.ilasm.end_try()

    def begin_catch(self, llexitcase):
        unimplemented

    def end_catch(self, llexitcase):
        unimplemented

    def store_exception_and_link(self, link):
        unimplemented

    def render_return_block(self, block):
        return_var = block.inputargs[0]
        return_ty = self.db.lltype_to_cts(return_var.concretetype)
        if return_var.concretetype is not ootype.Void:
            self.ilasm.load(return_var)
        self.ilasm.return_val(return_ty)

    def render_raise_block(self, block):
        exc = block.inputargs[1]
        self.ilasm.load(exc)
        self.ilasm.throw()

    def _setup_link(self, link):
        target = link.target
        for to_load, to_store in zip(link.args, target.inputargs):
            if to_load.concretetype is not ootype.Void:
                self.ilasm.load(to_load)
                self.ilasm.store(to_store)

class Class(Node):

    """ Represents a class to be emitted.  Note that currently, classes
    are emitted all in one shot, not piecemeal. """

    def __init__(self, name):
        """
        'name' should be a fully qualified Java class name like
        "java.lang.String"
        """
        self.name = name        # public attribute
        self.fields = []
        self.methods = []
        self.rendered = False

    def jvm_type(self):
        return jvm_for_class(self.name)

    def add_field(self, fieldty, fieldnm):
        """ Creates a new field in this with type 'fieldty' (a
        JvmType) and with the name ;fieldnm; (a String).  Must be called
        before render()."""
        assert not self.rendered
        self.fields.append((fieldty, fieldnm))

    def add_method(self, func):
        """ Creates a new method in this class, represented by the
        Function object 'func'.  Must be called before render();
        intended to be invoked by the database.  Note that some of these
        'methods' may actually represent static functions. """
        self.methods.append(func)

    def render(self, gen):
        self.rendered = True
        gen.begin_class(self.name)

        for fieldty, fieldnm in self.fields:
            gen.add_field(fieldty, fieldnm)

        for method in self.methods:
            method.render(gen)
        
        gen.end_class()
