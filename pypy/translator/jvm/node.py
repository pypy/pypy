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
     JvmGeneratedClassType, jString, jStringArray, jVoid, jThrowable, jInt, \
     jObject, JvmType, jStringBuilder, jPyPyInterlink, jCallbackInterfaces, \
     JvmGeneratedInterfaceType, jPyPy, jPyPyAbstractMethodException, \
     jPyPyThrowable, OBJECTGETCLASS
from pypy.translator.jvm.opcodes import \
     opcodes
from pypy.translator.jvm.option import \
     getoption
from pypy.translator.jvm.methods import \
     BaseDumpMethod, InstanceDumpMethod, RecordDumpMethod, \
     ConstantStringDumpMethod
from pypy.translator.oosupport.function import \
     Function as OOFunction
from pypy.translator.oosupport.constant import \
     push_constant
from pypy.translator.oosupport.treebuilder import \
     SubOperation
from pypy.translator.jvm.cmpopcodes import \
     can_branch_directly, branch_if

import pypy.translator.jvm.typesystem as jvm
import pypy.translator.jvm.typesystem as jvmtype
from pypy.translator.jvm.log import log

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
        ootype.Signed:jvm.PYPYSTRTOINT,
        ootype.Unsigned:jvm.PYPYSTRTOUINT,
        lltype.SignedLongLong:jvm.PYPYSTRTOLONG,
        lltype.UnsignedLongLong:jvm.PYPYSTRTOULONG,
        ootype.Bool:jvm.PYPYSTRTOBOOL,
        ootype.Float:jvm.PYPYSTRTODOUBLE,
        ootype.Char:jvm.PYPYSTRTOCHAR,
        ootype.UniChar:jvm.PYPYSTRTOCHAR,
        ootype.String:None
        }

    def render(self, gen):
        gen.begin_class(gen.db.jPyPyMain, jObject)
        gen.add_field(gen.db.pypy_field)
        gen.add_field(gen.db.interlink_field)

        # Initialization:
        # 
        #    1. Create an Interlink instance and a PyPy helper class, and
        #    store them in the appropriate static fields.
        #
        #    2. Run the initialization method for the constant class.
        #
        gen.begin_function('<clinit>', (), [], jVoid, static=True)
        gen.emit(jvm.NEW, jPyPy)
        gen.emit(jvm.DUP)
        gen.new_with_jtype(gen.db.jInterlinkImplementation)
        gen.emit(jvm.DUP)
        gen.db.interlink_field.store(gen)
        gen.emit(jvm.Method.c(jPyPy, [jPyPyInterlink]))
        gen.db.pypy_field.store(gen)
        gen.db.constant_generator.runtime_init(gen)
        gen.return_val(jVoid)
        gen.end_function()
        
        # Main method:
        # 
        #    1. Parse the arguments and create Python objects.
        #    2. Invoke the main function.
        #    3. Print the result to stdout if self.print_result is true
        #
        gen.begin_function(
            'main', (), [jStringArray], jVoid, static=True)

        if self.print_result:
            gen.begin_try()

        # Handle arguments:
        if self.expand_arguments:
            # Convert each entry into the array to the desired type by
            # invoking an appropriate helper function on each one
            for i, arg in enumerate(self.graph.getargs()):
                jty = self.db.lltype_to_cts(arg.concretetype)
                conv = self._type_conversion_methods[arg.concretetype]
                if conv: gen.push_pypy()
                gen.load_jvm_var(jStringArray, 0)
                gen.emit(jvm.ICONST, i)
                gen.load_from_array(jString)
                if conv: gen.emit(conv)
        else:
            # Convert the array of strings to a List<String> as the
            # python method expects
            arg0 = self.graph.getargs()[0]
            assert isinstance(arg0.concretetype, ootype.List), str(arg0.concretetype)
            assert arg0.concretetype.ITEM is ootype.String
            gen.load_jvm_var(jStringArray, 0)
            gen.emit(jvm.PYPYARRAYTOLIST)

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
            gen.emit(jvm.PYPYDUMP) # dump to stdout
            gen.goto(done_printing)
            gen.end_try()

            gen.begin_catch(jPyPyThrowable)
            gen.emit(jvm.PYPYDUMPEXCWRAPPER) # dumps to stdout
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
        """ Uses the gen argument, a jvm.Generator, to create the
        appropriate JVM assembly for this method. """
        raise NotImplementedError
    
    def method(self):
        """ Returns a jvm.Method object that would allow this
        function to be invoked. """
        raise NotImplementedError

class GetterFunction(Function):
    def __init__(self, db, cls_obj, method_obj, field_obj):
        self.db = db
        self.name = method_obj.method_name
        self.cls_obj = cls_obj
        self.method_obj = method_obj
        self.field_obj = field_obj

    def method(self):
        return self.method_obj

    def render(self, gen):
        gen.begin_function(
            self.method_obj.method_name, [],
            [self.cls_obj], self.field_obj.jtype)
        gen.load_this_ptr()
        self.field_obj.load(gen)
        gen.return_val(self.field_obj.jtype)
        gen.end_function()
    
class PutterFunction(Function):
    def __init__(self, db, cls_obj, method_obj, field_obj):
        self.db = db
        self.cls_obj = cls_obj
        self.method_obj = method_obj
        self.field_obj = field_obj

    def method(self):
        return self.method_obj

    def render(self, gen):
        gen.begin_function(
            self.method_obj.method_name, [],
            [self.cls_obj, self.field_obj.jtype], jVoid)
        gen.load_this_ptr()
        gen.load_function_argument(1)
        self.field_obj.store(gen)
        gen.return_val(jVoid)
        gen.end_function()

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

    def next_label(self, prefix='label'):
        return self.generator.unique_label(prefix)

    def method(self):
        """ Returns a jvm.Method that can invoke this function """
        if not self.is_method:
            ctor = jvm.Method.s
            startidx = 0
        else:
            ctor = jvm.Method.v
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

    def begin_try(self, cond):
        if cond:
            self.ilasm.begin_try()

    def end_try(self, exit_label, cond):
        self.ilasm.branch_unconditionally(exit_label)
        if cond:
            self.ilasm.end_try()

    def introduce_exception_conversions(self, llexitcases):

        # These are exceptions thrown internally by the JVM.
        # If the user is catching an RPython exception that corresponds
        # to one of these cases, we introduce a translation block which
        # catches the corresponding JVM exception and re-throwns the
        # RPython one.  A better solution would be to find a way to
        # make the RPython class the same as the JVM class, but that is
        # currently hindered by the presence of a few fields (meta) on
        # the Object class.
        translation_table = [
            (ZeroDivisionError, jvmtype.jArithmeticException),
            (RuntimeError, jvmtype.jStackOverflowError),
            (MemoryError, jvmtype.jOutOfMemoryError),
            ]

        for pyexccls, jexcty in translation_table:
            for llexitcase in llexitcases:
                # llexitcase is an exception class, like ZeroDivisionError
                if issubclass(llexitcase, pyexccls):
                    # Generate some converter code like:
                    #   try { ... }
                    #   catch (OutOfStackError e) {
                    #     jPyPyMain.ilink.throwRuntimeError();
                    #     throw null;
                    #   }
                    # The "throw null" will never execute, it's just
                    # there to make the verifier happy, since it doesn't
                    # realize that Interlink's throwXyzError() methods
                    # never return.  At the end we invoke end_try() again
                    # so as to extend the encompassing try/catch region
                    # to include this code, thus allowing the RPython
                    # exception to be caught by the normal handlers.
                    self.ilasm.begin_catch(jexcty)
                    self.ilasm.push_interlink()
                    interlink_method = jvm.Method.v(
                        jPyPyInterlink, "throw"+pyexccls.__name__, [], jVoid)
                    self.ilasm.emit(interlink_method)
                    self.ilasm.emit(jvm.ACONST_NULL) # "inform" the verifier...
                    self.ilasm.emit(jvm.ATHROW)      # ...that we throw here
                    self.ilasm.end_try()        

    def begin_catch(self, llexitcase):
        ll_meta_exc = llexitcase
        ll_exc = ll_meta_exc._INSTANCE
        jtype = self.cts.lltype_to_cts(ll_exc)
        assert jtype.throwable # SHOULD only try to catch subtypes of Exception
        self.ilasm.begin_catch(jtype)

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
                # if the code that follows is interested in the class
                # of the exception, extract it
                self.ilasm.dup_jtype(jPyPyThrowable)
                self.ilasm.store(link.last_exc_value)
                self.ilasm.emit(OBJECTGETCLASS)
                self.ilasm.store(link.last_exception)
            else:
                self.ilasm.store(link.last_exc_value)
            self._setup_link(link)

    def render_normal_block(self, block):
        """
        Overload OOFunction.render_normal_block: we intercept blocks where the
        exitcase tests a bool variable with one use so as to generate more
        efficient code.  For example, the naive code generation for a test
        like 'if x < y' yields something like:
        
           push x
           push y
           jump_if_less_than true
        false:
           push 0
           jump done
        true:
           push 1
        done:
           store_into_local_var
           load_from_local_var
           jump_if_true true_destination
           jump false_destination

        when it could (should) be

           push x
           push y
           jump_if_less_than true_destination
           jump false_destination
        """

        def not_in_link_args(v):
            for link in block.exits:
                if v in link.args: return False
            return True

        def true_false_exits():
            if block.exits[0].exitcase:
                return block.exits[0], block.exits[1]
            return block.exits[1], block.exits[0]

        if block.operations:
            # Look for a case where the block switches on a bool variable
            # which is produced by the last operation and not used
            # anywhere else, and where the last operation is a comparison.

            # Watch out for a last operation like:
            #   v1 = same_as([int_lt(i, j)])
            last_op = block.operations[-1]
            while (last_op.opname == "same_as" and
                   isinstance(last_op.args[0], SubOperation)):
                last_op = last_op.args[0].op
            
            if (block.exitswitch is not None and
                block.exitswitch.concretetype is ootype.Bool and
                block.operations[-1].result is block.exitswitch and
                can_branch_directly(last_op.opname) and
                not_in_link_args(block.exitswitch)):

                self.generator.add_comment(
                    "short-circuit final comparison on %s, block has %d ops" % (
                    block.exitswitch, len(block.operations)))

                for op in block.operations[:-1]:
                    self._render_op(op)
                    
                self.generator.add_comment(
                    "inlining comparison: %r" % (last_op),)
                for arg in last_op.args:
                    self.ilasm.load(arg)
                truelink, falselink = true_false_exits()
                true_label = self.next_label('link_true')
                branch_if(self.ilasm, last_op.opname, true_label)
                self._follow_link(falselink)
                self.set_label(true_label)
                self._follow_link(truelink)
                return

        return OOFunction.render_normal_block(self, block)

    def render_numeric_switch(self, block):
        if block.exitswitch.concretetype in (ootype.SignedLongLong, ootype.UnsignedLongLong):
            # TODO: it could be faster to check is the values fit in
            # 32bit, and perform a cast in that case
            self.render_numeric_switch_naive(block)
            return

        cases, min_case, max_case, default = self._collect_switch_cases(block)
        is_sparse = self._is_sparse_switch(cases, min_case, max_case)

        if is_sparse:
            log.WARNING('TODO: use lookupswitch to render sparse numeric_switches')
            self.render_numeric_switch_naive(block)
            return

        targets = []
        for i in xrange(min_case, max_case+1):
            link, lbl = cases.get(i, default)
            targets.append(lbl)

        self.generator.load(block.exitswitch)
        self.generator.emit_tableswitch(min_case, targets, default[1])
        
        self.render_switch_case(*default)
        for link, lbl in cases.itervalues():
            self.render_switch_case(link, lbl)

    def render_return_block(self, block):
        return_var = block.inputargs[0]
        return_ty = self.db.lltype_to_cts(return_var.concretetype)
        if return_var.concretetype is not ootype.Void:
            self.ilasm.load(return_var)
        self.ilasm.return_val(return_ty)

    def render_raise_block(self, block):
        exc = block.inputargs[1]
        self.ilasm.load(exc)

        # Check whether the static type is known to be throwable.
        # If not, emit a CHECKCAST to throwable.
        # According to Samuele, no non-Exceptions should be thrown,
        # but this is not enforced by the RTyper or annotator.
        jtype = self.db.lltype_to_cts(exc.concretetype)
        if not jtype.throwable:
            self.ilasm.downcast_jtype(jThrowable)
            
        self.ilasm.throw()

    def _trace(self, str, writeline=False):
        if writeline:
            str += '\n'
        jvm.SYSTEMERR.load(self.generator)
        self.generator.load_string(str)
        jvm.PRINTSTREAMPRINTSTR.invoke(self.generator)

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
            self.generator.emit(jvm.SYSTEMERR)
            self.generator.load(res)
            self.generator.emit(jmethod)
            self.generator.emit(jvm.PRINTSTREAMPRINTSTR)
            self._trace("\n")

    def _trace_enabled(self):
        return getoption('trace')

    def _render_op(self, op):
        self.generator.add_comment(str(op))
        OOFunction._render_op(self, op)


class StaticMethodInterface(Node, JvmGeneratedClassType):
    """
    We generate an abstract base class when we need function pointers,
    which correspond to constants of StaticMethod ootype.  We need a
    different interface for each different set of argument/return
    types. These abstract base classes look like:

    abstract class Foo {
      public abstract ReturnType invoke(Arg1, Arg2, ...);
    }

    Depending on the signature of Arg1, Arg2, and ReturnType, this
    abstract class may have additional methods and may implement
    interfaces such as PyPy.Equals or PyPy.HashCode.  This is to allow
    it to interface with the the standalone Java code.  See
    the pypy.Callback interface for more information.    
    """
    def __init__(self, name, jargtypes, jrettype):
        """
        argtypes: list of JvmTypes
        rettype: JvmType
        """
        JvmGeneratedClassType.__init__(self, name)
        assert isinstance(jrettype, JvmType)
        self.java_argument_types = [self] + list(jargtypes)
        self.java_return_type = jrettype
        self.dump_method = ConstantStringDumpMethod(
            self, "StaticMethodInterface")
        self.invoke_method_obj = jvm.Method.v(
                self, 'invoke',
                self.java_argument_types[1:], self.java_return_type)
        
    def lookup_field(self, fieldnm):
        raise KeyError(fieldnm) # no fields
    
    def lookup_method(self, methodnm):
        """ Given the method name, returns a jvm.Method object """
        assert isinstance(self.java_return_type, JvmType)
        if methodnm == 'invoke':
            return self.invoke_method_obj
        raise KeyError(methodnm) # only one method
    
    def render(self, gen):
        assert isinstance(self.java_return_type, JvmType)

        # Scan through the jCallbackInterfaces and look for any
        # that apply.
        for jci in jCallbackInterfaces:
            if jci.matches(self.java_argument_types[1:], self.java_return_type):
                break
        else:
            jci = None
        
        gen.begin_class(self, jObject, abstract=True)
        if jci: gen.implements(jci)
        gen.begin_constructor()
        gen.end_constructor()
        
        gen.begin_function('invoke', [], self.java_argument_types,
                           self.java_return_type, abstract=True)
        gen.end_function()

        # Because methods in the JVM are identified by both their name
        # and static signature, we need to create a dummy "invoke"
        # method if the Java callback interface argument types don't
        # match the actual types for this method.  For example, the
        # equals interface has the static signature
        # "(Object,Object)=>boolean", but there may be static methods
        # with some signature "(X,Y)=>boolean" where X and Y are other
        # types.  In that case, we create an adaptor method like:
        #
        #   boolean invoke(Object x, Object y) {
        #     return invoke((X)x, (Y)y);
        #   }
        if (jci and
            (jci.java_argument_types != self.java_argument_types[1:] or
             jci.java_return_type != self.java_return_type)):

            jci_jargs = [self] + list(jci.java_argument_types)
            jci_ret = jci.java_return_type
            gen.begin_function('invoke', [], jci_jargs, jci_ret)
            idx = 0
            for jci_arg, self_arg in zip(jci_jargs, self.java_argument_types):
                gen.load_jvm_var(jci_arg, idx)
                if jci_arg != self_arg:
                    gen.prepare_generic_result_with_jtype(self_arg)
                idx += jci_arg.descriptor.type_width()
            gen.emit(self.invoke_method_obj)
            assert jci_ret == self.java_return_type # no variance here currently
            gen.return_val(jci_ret)
            gen.end_function()
            
        gen.end_class()

class StaticMethodImplementation(Node, JvmGeneratedClassType):
    """
    In addition to the StaticMethodInterface, we must generate an
    implementation for each specific method that is called.  These
    implementation objects look like:

    class Bar extends Foo {
        public ReturnType invoke(Arg1, Arg2) {
          return SomeStaticClass.StaticMethod(Arg1, Arg2);
        }
    }

    If the bound_to_jty argument is not None, then this class
    represents a bound method, and looks something like:

    class Bar extends Foo {
        Qux bound_to;
        public static Bar bind(Qux to) {
          Bar b = new Bar();
          b.bound_to = to;
          return b;
        }
        public ReturnType invoke(Arg1, Arg2) {
          return bound_to.SomeMethod(Arg1, Arg2);
        }
    }
    """
    def __init__(self, name, super_class, bound_to_jty, impl_method):
        JvmGeneratedClassType.__init__(self, name)
        self.super_class = super_class
        self.impl_method = impl_method
        self.dump_method = ConstantStringDumpMethod(
            self, "StaticMethodImplementation")

        if bound_to_jty:
            self.bound_to_jty = bound_to_jty
            self.bound_to_fld = jvm.Field(
                self.name, 'bound_to', bound_to_jty, False)
            self.bind_method = jvm.Method.s(
                self, 'bind', (self.bound_to_jty,), self)                
        else:
            self.bound_to_jty = None
            self.bound_to_fld = None
            self.bind_method = None
            
    def lookup_field(self, fieldnm):
        if self.bound_to_fld and fieldnm == self.bound_to_fld.name:
            return self.bound_to_fld
        return self.super_class.lookup_field(fieldnm)
    def lookup_method(self, methodnm):
        if self.bind_method and methodnm == 'bind':
            return self.bind_method
        return self.super_class.lookup_method(methodnm)
    def render(self, gen):
        gen.begin_class(self, self.super_class)

        if self.bound_to_fld:
            gen.add_field(self.bound_to_fld)
            
        gen.begin_constructor()
        gen.end_constructor()

        # Emit the "bind" function which creates an instance if there is
        # a bound field:
        if self.bound_to_jty:
            assert self.bound_to_fld and self.bind_method
            gen.begin_function(
                'bind', [], (self.bound_to_jty,), self, static=True)
            gen.new_with_jtype(self)
            gen.emit(jvm.DUP)
            gen.load_jvm_var(self.bound_to_jty, 0)
            self.bound_to_fld.store(gen)
            gen.return_val(self)
            gen.end_function()

        # Emit the invoke() function, which just re-pushes the
        # arguments and then invokes either the (possibly static)
        # method self.impl_method.  Note that if we are bound to an
        # instance, we push that as the this pointer for
        # self.impl_method.
        gen.begin_function('invoke', [],
                           self.super_class.java_argument_types,
                           self.super_class.java_return_type)
        if self.bound_to_fld:
            gen.load_jvm_var(self, 0)
            gen.emit(self.bound_to_fld)
        for i in range(len(self.super_class.java_argument_types)):
            if not i: continue # skip the this ptr
            gen.load_function_argument(i)
        gen.emit(self.impl_method)
        gen.return_val(self.super_class.java_return_type)
        gen.end_function()
        gen.end_class()

class Interface(Node, JvmGeneratedInterfaceType):
    """
    Represents an interface to be generated.  The only class that we
    currently generate into an interface is ootype.ROOT.
    """
    def __init__(self, name):
        JvmGeneratedInterfaceType.__init__(self, name)
        self.super_class = jObject
        self.rendered = False
        self.properties = {}
        self.methods = {}

    def lookup_field(self, fieldnm):
        # Right now, we don't need inheritance between interfaces.
        return self.properties[fieldnm]

    def lookup_method(self, methodnm):
        # Right now, we don't need inheritance between interfaces.
        return self.methods[methodnm]

    def add_property(self, prop):
        self.properties[prop.field_name] = prop

    def add_method(self, method):
        self.methods[method.name] = method

    def render(self, gen):
        self.rendered = True
        gen.begin_class(self, self.super_class, interface=True)

        def emit_method(method):
            gen.begin_j_function(self, method, abstract=True)
            gen.end_function()
            
        for method in self.methods.values():
            emit_method(method)
        for prop in self.properties.values():
            emit_method(prop.get_method)
            emit_method(prop.put_method)

        gen.end_class()

class Class(Node, JvmGeneratedClassType):

    """ Represents a class to be emitted.  Note that currently, classes
    are emitted all in one shot, not piecemeal. """

    def __init__(self, name, supercls=None):
        """
        'name' should be a fully qualified Java class name like
        "java.lang.String", supercls is a Class object
        """
        JvmGeneratedClassType.__init__(self, name)
        self.rendered = False       # has rendering occurred?
        self.fields = {}            # maps field name to jvm.Field object
        self.interfaces = []        # list of JvmTypes
        self.methods = {}           # maps method name to a Function object*
        self.abstract_methods = {}  # maps method name to jvm.Method object
        self.set_super_class(supercls)

        # * --- actually maps to an object that defines the
        # attributes: name, method() and render().  Usually, this is a
        # Function object, but in some subclasses it is not.

    def simple_name(self):
        dot = self.name.rfind('.')
        if dot == -1: return self.name
        return self.name[dot+1:]

    def set_super_class(self, supercls):
        self.super_class = supercls

        # Throwability is inherited:
        if self.super_class and self.super_class.throwable:
            self.throwable = True

    def add_field(self, fieldobj, fielddef):
        """ Creates a new field accessed via the jvm.Field
        descriptor 'fieldobj'.  Must be called before render()."""
        assert not self.rendered and isinstance(fieldobj, jvm.Field)
        self.fields[fieldobj.field_name] = (fieldobj, fielddef)

    def add_interface(self, inter):
        assert not self.rendered and isinstance(inter, JvmType)
        self.interfaces.append(inter)

    def lookup_field(self, fieldnm):
        if fieldnm in self.fields:
            return self.fields[fieldnm][0]
        return self.super_class.lookup_field(fieldnm)

    def lookup_method(self, methodnm):
        """ Given the method name, returns a jvm.Method object """
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
        be a jvm.Method object """
        assert jmethod.method_name not in self.methods
        self.abstract_methods[jmethod.method_name] = jmethod

    def render(self, gen):
        self.rendered = True
        gen.begin_class(self, self.super_class)

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
            gen.begin_j_function(self, method)
            gen.new_with_jtype(jPyPyAbstractMethodException)
            gen.throw()
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
        helper:     a jvm.Method object for the helper func we should invoke
        """
        self.interlink = interlink
        self.name = name
        self.helper = helper

        # Since the names of classes we generate are not statically
        # known, the functions in Interlink.java simply return
        # Object when they create an instance of one of those types.
        if self.helper.return_type.is_generated():
            self.return_type = jObject
        else:
            self.return_type = self.helper.return_type
            
        self.method_obj = jvm.Method.v(interlink,
                                          self.name,
                                          self.helper.argument_types,
                                          self.return_type)

    def method(self):
        return self.method_obj

    def render(self, gen):
        argtypes = [self.interlink] + list(self.helper.argument_types)
        gen.begin_function(self.name, (), argtypes, self.return_type)
        varindex = 1
        for argty in self.helper.argument_types:
            gen.load_jvm_var(argty, varindex)
            varindex += argty.descriptor.type_width()
        gen.emit(self.helper)
        gen.return_val(self.return_type)
        gen.end_function()
