"""
Nodes describe Java structures that we are building.  They know how to
render themselves so as to build the java structure they describe.
They are entered onto the database worklist as we go.

Some nodes describe parts of the JVM structure that already exist ---
for example, there are nodes that are used to describe built-in JVM
types like String, etc.  In this case, they are never placed on the
database worklist, and don't know how to render themselves (since they
don't have to).

Nodes representing classes that we will build also implement the JvmType
interface defined by database.JvmType.
"""


from pypy.objspace.flow import \
     model as flowmodel
from pypy.rpython.lltypesystem import \
     lltype
from pypy.rpython.ootypesystem import \
     ootype, rclass
from pypy.translator.jvm.typesystem import \
     JvmClassType, jString, jStringArray, jVoid, jThrowable, jInt, jPyPyMain, \
     jObject, JvmType, jStringBuilder, jPyPyInterlink
from pypy.translator.jvm.opcodes import \
     opcodes
from pypy.translator.jvm.option import \
     getoption
from pypy.translator.jvm.methods import \
     BaseDumpMethod, InstanceDumpMethod, RecordDumpMethod, ConstantStringDumpMethod
from pypy.translator.oosupport.function import \
     Function as OOFunction
from pypy.translator.oosupport.constant import \
     push_constant

import pypy.translator.jvm.generator as jvmgen

class Node(object):
    def set_db(self, db):
        self.db = db
    def dependencies(self):
        pass

class EntryPoint(Node):

    """
    A special node that generates the pypy.Main class which has a static
    main method.  Can be configured with a number of options for internal
    testing (see __init__)
    """

    def __init__(self, graph, expandargs, printresult):
        """
        'graph' --- The initial graph to invoke from main()
        'expandargs' --- controls whether the arguments passed to main()
        are passed as a list, or expanded to match each argument to the graph
        'printresult' --- controls whether the result is printed to stdout
        when the program finishes

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
        self.print_result = printresult
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
        ootype.Char:jvmgen.PYPYSTRTOCHAR,
        ootype.UniChar:jvmgen.PYPYSTRTOCHAR,
        ootype.String:None
        }

    def render(self, gen):
        gen.begin_class(jPyPyMain, jObject)
        gen.begin_function(
            'main', (), [jStringArray], jVoid, static=True)

        # First thing we do is setup the PyPy helper.  For now this is
        # a static variable of the PyPy class, though that precludes
        # running multiple translations.
        gen.new_with_jtype(gen.db.interlink_class)
        jvmgen.PYPYINTERLINK.store(gen)

        if self.print_result:
            gen.begin_try()

        # Handle arguments:
        if self.expand_arguments:
            # Convert each entry into the array to the desired type by
            # invoking an appropriate helper function on each one
            for i, arg in enumerate(self.graph.getargs()):
                jty = self.db.lltype_to_cts(arg.concretetype)
                gen.load_jvm_var(jStringArray, 0)
                gen.emit(jvmgen.ICONST, i)
                gen.load_from_array(jString)
                conv = self._type_conversion_methods[arg.concretetype]
                if conv: gen.emit(conv)
        else:
            # Convert the array of strings to a List<String> as the
            # python method expects
            arg0 = self.graph.getargs()[0]
            assert isinstance(arg0.concretetype, ootype.List), str(arg0.concretetype)
            assert arg0.concretetype._ITEMTYPE is ootype.String
            gen.load_jvm_var(jStringArray, 0)
            gen.emit(jvmgen.PYPYARRAYTOLIST)

        # Generate a call to this method
        gen.emit(self.db.pending_function(self.graph))

        # Print result?
        #
        #   Use the dump method for non-exceptional results
        #
        #   For exceptions, just print the runtime type
        #
        if self.print_result:
            done_printing = gen.unique_label('done_printing')
            RESOOTYPE = self.graph.getreturnvar().concretetype
            dumpmethod = self.db.toString_method_for_ootype(RESOOTYPE)
            gen.add_comment('Invoking dump method for result of type '
                            +str(RESOOTYPE))
            gen.emit(dumpmethod)      # generate the string
            gen.emit(jvmgen.PYPYDUMP) # dump to stdout
            gen.goto(done_printing)
            gen.end_try()

            gen.begin_catch(jObject)
            gen.emit(jvmgen.PYPYDUMPEXCWRAPPER) # dumps to stdout
            gen.end_catch()

            gen.mark(done_printing)

        # And finish up
        gen.return_val(jVoid)
        
        gen.end_function()
        gen.end_class()

class Function(object):

    """ A generic interface for Function objects; these objects can
    be added as methods of classes and rendered.  This class serves
    only as documentation. """

    # A "name" attribute must be defined
    name = None                       
    
    def render(self, gen):
        """ Uses the gen argument, a jvmgen.Generator, to create the
        appropriate JVM assembly for this method. """
        raise NotImplementedError
    
    def method(self):
        """ Returns a jvmgen.Method object that would allow this
        function to be invoked. """
        raise NotImplementedError
    
class GraphFunction(OOFunction, Function):
    
    """ Represents a function that is generated from a graph. """
    
    def __init__(self, db, classty, name, jargtypes,
                 jrettype, graph, is_static):
        """
        classty: the JvmClassType object this is a part of (even static
        functions have a class)
        name: the name of the function
        jargtypes: JvmType of each argument
        jrettype: JvmType this function returns
        graph: the graph representing the body of the function
        is_static: boolean flag indicate whether func is static (!)
        """
        OOFunction.__init__(self, db, graph, name, not is_static)
        self.classty = classty
        self.jargtypes = jargtypes
        self.jrettype = jrettype
        self._block_labels = {}

    def method(self):
        """ Returns a jvmgen.Method that can invoke this function """
        if not self.is_method:
            ctor = jvmgen.Method.s
            startidx = 0
        else:
            ctor = jvmgen.Method.v
            startidx = 1
        return ctor(self.classty, self.name,
                    self.jargtypes[startidx:], self.jrettype)

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

    def end_try(self, exit_label):
        self.ilasm.branch_unconditionally(exit_label)
        self.ilasm.end_try()

    def begin_catch(self, llexitcase):
        ll_meta_exc = llexitcase
        ll_exc = ll_meta_exc._inst.class_._INSTANCE
        cts_exc = self.cts.lltype_to_cts(ll_exc)
        self.ilasm.begin_catch(cts_exc)

    def end_catch(self, exit_lbl):
        self.ilasm.goto(exit_lbl)
        self.ilasm.end_catch()

    def store_exception_and_link(self, link):
        if self._is_raise_block(link.target):
            # the exception value is on the stack, use it as the 2nd target arg
            assert len(link.args) == 2
            assert len(link.target.inputargs) == 2
            self.ilasm.store(link.target.inputargs[1])
        else:
            # the exception value is on the stack, store it in the proper place
            if isinstance(link.last_exception, flowmodel.Variable):
                self.ilasm.emit(jvmgen.DUP)
                self.ilasm.store(link.last_exc_value)
                fld = jvmgen.Field(
                    self.db.lltype_to_cts(rclass.OBJECT).name,
                    'meta',
                    self.db.lltype_to_cts(rclass.CLASSTYPE),
                    False,
                    rclass.OBJECT)
                self.ilasm.emit(fld)
                self.ilasm.store(link.last_exception)
            else:
                self.ilasm.store(link.last_exc_value)
            self._setup_link(link)

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

    def _trace(self, str):
        jvmgen.SYSTEMERR.load(self.generator)
        self.generator.load_string(str)
        jvmgen.PRINTSTREAMPRINTSTR.invoke(self.generator)

    def _is_printable(self, res):

        if res.concretetype in (
            ootype.Instance,
            ootype.Signed,
            ootype.Unsigned,
            ootype.SignedLongLong,
            ootype.UnsignedLongLong,
            ootype.Bool,
            ootype.Float,
            ootype.Char,
            ootype.UniChar,
            ootype.String,
            ootype.StringBuilder,
            ootype.Class):
            return True

        if isinstance(res.concretetype, (
            ootype.Instance,
            ootype.Record,
            ootype.List,
            ootype.Dict,
            ootype.DictItemsIterator)):
            return True

        return False

    def _trace_value(self, prompt, res):
        if res and self._is_printable(res):
            jmethod = self.db.toString_method_for_ootype(
                res.concretetype)
            
            self._trace("  "+prompt+": ")
            self.generator.emit(jvmgen.SYSTEMERR)
            self.generator.load(res)
            self.generator.emit(jmethod)
            self.generator.emit(jvmgen.PRINTSTREAMPRINTSTR)
            self._trace("\n")

    def _render_op(self, op):
        self.generator.add_comment(str(op))
        
        if getoption('trace'):
            self._trace(str(op)+"\n")

            for i, arg in enumerate(op.args):
                self._trace_value('Arg %02d' % i, arg)

        OOFunction._render_op(self, op)

        if getoption('trace'):
            self._trace_value('Result', op.result)

class StaticMethodInterface(Node, JvmClassType):
    """
    We generate an abstract base class when we need function pointers,
    which correspond to constants of StaticMethod ootype.  We need a
    different interface for each different set of argument/return
    types. These abstract base classes look like:

    abstract class Foo {
      public abstract ReturnType invoke(Arg1, Arg2, ...);
    }
    
    """
    def __init__(self, name, STATIC_METHOD, jargtypes, jrettype):
        """
        argtypes: list of JvmTypes
        rettype: JvmType
        """
        JvmClassType.__init__(self, name)
        self.STATIC_METHOD = STATIC_METHOD
        assert isinstance(jrettype, JvmType)
        self.java_argument_types = [self] + list(jargtypes)
        self.java_return_type = jrettype
        self.dump_method = ConstantStringDumpMethod(
            self, "StaticMethodInterface")
        
    def lookup_field(self, fieldnm):
        """ Given a field name, returns a jvmgen.Field object """
        raise KeyError(fieldnm) # no fields
    def lookup_method(self, methodnm):
        """ Given the method name, returns a jvmgen.Method object """
        assert isinstance(self.java_return_type, JvmType)
        if methodnm == 'invoke':
            return jvmgen.Method.v(
                self, 'invoke',
                self.java_argument_types[1:], self.java_return_type)
        raise KeyError(methodnm) # only one method
    def render(self, gen):
        assert isinstance(self.java_return_type, JvmType)
        gen.begin_class(self, jObject, abstract=True)
        gen.begin_constructor()
        gen.end_constructor()
        gen.begin_function('invoke', [], self.java_argument_types,
                           self.java_return_type, abstract=True)
        gen.end_function()
        gen.end_class()

class StaticMethodImplementation(Node, JvmClassType):
    """
    In addition to the StaticMethodInterface, we must generate an
    implementation for each specific method that is called.  These
    implementation objects look like:

    class Bar extends Foo {
        public ReturnType invoke(Arg1, Arg2) {
          return SomeStaticClass.StaticMethod(Arg1, Arg2);
        }
    }
    """
    def __init__(self, name, interface, impl_method):
        JvmClassType.__init__(self, name)        
        self.super_class = interface
        self.impl_method = impl_method
        self.dump_method = ConstantStringDumpMethod(
            self, "StaticMethodImplementation")
    def lookup_field(self, fieldnm):
        """ Given a field name, returns a jvmgen.Field object """
        return self.super_class.lookup_field(fieldnm)
    def lookup_method(self, methodnm):
        """ Given the method name, returns a jvmgen.Method object """
        return self.super_class.lookup_method(methodnm)
    def render(self, gen):
        gen.begin_class(self, self.super_class)
        gen.begin_constructor()
        gen.end_constructor()
        gen.begin_function('invoke', [],
                           self.super_class.java_argument_types,
                           self.super_class.java_return_type)
        for i in range(len(self.super_class.java_argument_types)):
            if not i: continue # skip the this ptr
            gen.load_function_argument(i)
        gen.emit(self.impl_method)
        gen.return_val(self.super_class.java_return_type)
        gen.end_function()
        gen.end_class()

class Class(Node, JvmClassType):

    """ Represents a class to be emitted.  Note that currently, classes
    are emitted all in one shot, not piecemeal. """

    def __init__(self, name, supercls=None, initialize_fields=True):
        """
        'name' should be a fully qualified Java class name like
        "java.lang.String", supercls is a Class object
        """
        JvmClassType.__init__(self, name)
        self.super_class = supercls # JvmType; if None, must use set_super_class
        self.rendered = False       # has rendering occurred?
        self.abstract = False       # is this an abstract class?
        self.fields = {}            # maps field name to jvmgen.Field object
        self.interfaces = []        # list of JvmTypes
        self.methods = {}           # maps method name to a Function object*
        self.abstract_methods = {}  # maps method name to jvmgen.Method object

        # * --- actually maps to an object that defines the
        # attributes: name, method() and render().  Usually, this is a
        # Function object, but in some subclasses it is not.

    def set_super_class(self, supercls):
        self.super_class = supercls

    def add_field(self, fieldobj, fielddef):
        """ Creates a new field accessed via the jvmgen.Field
        descriptor 'fieldobj'.  Must be called before render()."""
        assert not self.rendered and isinstance(fieldobj, jvmgen.Field)
        self.fields[fieldobj.field_name] = (fieldobj, fielddef)

    def add_interface(self, inter):
        assert not self.rendered and isinstance(inter, JvmType)
        self.interfaces.append(inter)

    def lookup_field(self, fieldnm):
        """ Given a field name, returns a jvmgen.Field object """
        if fieldnm in self.fields:
            return self.fields[fieldnm][0]
        return self.super_class.lookup_field(fieldnm)

    def lookup_method(self, methodnm):
        """ Given the method name, returns a jvmgen.Method object """
        if methodnm in self.methods:
            return self.methods[methodnm].method()
        if methodnm in self.abstract_methods:
            return self.abstract_methods[methodnm]
        return self.super_class.lookup_method(methodnm)

    def add_method(self, func):
        """ Creates a new method in this class, represented by the
        Function object 'func'.  Must be called before render();
        intended to be invoked by the database.  Note that some of these
        'methods' may actually represent static functions. """
        self.methods[func.name] = func

    def add_abstract_method(self, jmethod):
        """ Adds an abstract method to our list of methods; jmethod should
        be a jvmgen.Method object """
        assert jmethod.method_name not in self.methods
        self.abstract = True
        self.abstract_methods[jmethod.method_name] = jmethod

    def render(self, gen):
        self.rendered = True
        gen.begin_class(self, self.super_class, abstract=self.abstract)

        for inter in self.interfaces:
            gen.implements(inter)

        for field, fielddef in self.fields.values():
            gen.add_field(field)

        # Emit the constructor:
        gen.begin_constructor()
        # set default values for fields
        for field, f_default in self.fields.values():
            if field.jtype is not jVoid:
                gen.load_jvm_var(self, 0) # load this ptr
                # load default value of field
                push_constant(gen.db, field.OOTYPE, f_default, gen)
                field.store(gen)           # store value into field
        gen.end_constructor()

        for method in self.methods.values():
            method.render(gen)

        for method in self.abstract_methods.values():
            gen.begin_function(
                method.method_name, None, method.argument_types,
                method.return_type, abstract=True)
            gen.end_function()
        
        gen.end_class()

class InterlinkFunction(Function):

    """
    Used for methods of the interlink helper class that we generate.
    Generates a method which takes no arguments and which invokes
    a given static helper function.
    """

    def __init__(self, interlink, name, helper):
        """
        interlink:  the JvmType of the Interlink implementation
        name:       the name of the method
        helper:     a jvmgen.Method object for the helper func we should invoke
        """
        self.interlink = interlink
        self.name = name
        self.helper = helper
        self.method_obj = jvmgen.Method.v(interlink, self.name, [], jVoid)

    def method(self):
        return self.method_obj

    def render(self, gen):
        gen.begin_function(self.name, (), [self.interlink], jVoid)
        gen.emit(self.helper)
        gen.return_val(jVoid)
        gen.end_function()

