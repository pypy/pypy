"""
Rendering nodes for the JVM.  I suspect that a lot of this could be
made to be common between CLR and JVM.
"""


from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.typesystem import jStringArray, jVoid, jThrowable
from pypy.translator.jvm.typesystem import jvm_for_class
import pypy.translator.jvm.generator as jvmgen
from pypy.translator.jvm.opcodes import opcodes

class Node(object):
    def render(self, db, generator):
        unimplemented

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

    def render(self, db, gen):
        gen.begin_class('pypy.Main')
        gen.begin_function('main', (), [jStringArray], jVoid, static=True)

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
        gen.emit(db.method_for_graph(self.graph, static=True))
        
        gen.end_function()
        gen.end_class()

class Function(object):
    
    """ Represents a function to be emitted.  *Note* that it is not a
    descendant of Node: it cannot be entered into the database
    worklist.  This is because in Java, all functions occur w/in a
    class: therefore classes as a whole must be placed on the
    worklist. """
    
    def __init__(self, classobj, name, jargtypes, jrettype, graph, is_static):
        """
        classobj: the Class object this is a part of (even static
        functions have a class)
        name: the name of the function
        jargtypes: JvmType of each argument
        jrettype: JvmType this function returns
        graph: the graph representing the body of the function
        is_static: boolean flag indicate whether func is static (!)
        """
        self.classnm = classnm
        self.name = name
        self.graph = graph
        self.jargtypes = jargtypes
        self.jrettype = jrettype
        self.is_static = is_static

    def method(self):
        """ Returns a jvmgen.Method that can invoke this function """
        if self.is_static: opcode = jvmgen.INVOKESTATIC
        else: opcode = jvmgen.INVOKEVIRTUAL
        mdesc = jvm_method_desc(self.jargtypes, self.jrettype)
        return jvmgen.Method(classnm, self.func_name, mdesc, opcode=opcode)

    def render_func(self, db, gen):
        if getattr(self.graph.func, 'suggested_primitive', False):
            assert False, 'Cannot render a suggested_primitive'

        # Prepare argument lists for begin_function call
        jargvars = []
        jargtypes = []
        for arg in self.graph.getargs():
            if arg.concretetype is ootype.Void: continue
            jargvars.append(arg)
            jargtypes.append(db.type_system.ootype_to_jvm(arg.concretetype))

        # Determine return type
        jrettype = db.type_system.ootype_to_jvm(
            self.graph.getreturnvar().concretetype)

        # Start the function definition
        gen.begin_function(self.name, jargvars, jargtypes, jrettype,
                           static=self.is_static)

        # Go through each block and create a label for it; if the
        # block will be used to catch an exception, add a second label
        # to catch_labels
        block_labels = {}
        #catch_labels = {}
        for ctr, block in enumerate(graph.iterblocks()):
            blbl = gen.unique_label('Block_'+ctr)
            block_labels[block] = blbl

            ## Go through the blocks we may toss exceptions to
            #if block.exitswitch == flowmodel.c_last_exception:
            #    for link in block.exits:
            #        if link.exitcase is None: continue # return
            #        if link.target not in catch_labels:
            #            catch_labels[link.target] = gen.unique_label('catch')

        # Iterate through the blocks and generate code for them
        return_blocks = []
        for block in graph.iterblocks():
            
            # Mark the beginning of the block, render all the ops, and
            # then mark the end.
            gen.mark(block_labels[block][0])

            # Determine whether the last oper in this block may raise an exc
            handle_exc = (block.exitswitch == flowmodel.c_last_exception)

            # Render the operations; create labels for a try/catch
            # region around the last operation
            if block.operations:
                for op in block.operations[:-1]:
                    self._render_op(op)
                if handle_exc: trybeglbl = gen.unique_label('try', mark=True)
                self._render_op(block.operations[-1])
                if handle_exc: tryendlbl = gen.unique_label('try', mark=True)

            # Handle 'return' blocks: in this case, we return the
            # variable specified
            if self._is_return_block(block):
                return_var = block.inputargs[0]
                return_ty = ootype_to_jvm(return_var.concretetype)
                if return_var.concretetype is not Void:
                    self.load(return_var)
                gen.return_val(return_ty)

            # Handle 'raise' blocks: in this case, we just throw the
            # variable specified
            if self._is_raise_block(block):
                exc = block.inputargs[1]
                self.load(exc)
                gen.throw()

            if handle_exc:
                # search for the "default" block to be executed when
                # no exception is raised
                for link in block.exits:
                    if link.exitcase is None:
                        self._copy_link_vars(gen, link)
                        gen.goto(block_labels[link.target])

                # TODO: proper exception handling; we may not want to
                # use the same model as CLR
            else:
                # no exception handling, determine correct link to follow
                for link in block.exits:
                    self._copy_link_vars(gen, link)
                    target_label = block_labels[link.target]
                    if link.exitcase is None or link is block.exits[-1]:
                        gen.goto(target_label)
                    else:
                        assert type(link.exitcase is bool)
                        assert block.exitswitch is not None
                        gen.load(block.exitswitch)
                        gen.goto_if_true(target_label)

        gen.end_function()

    def _render_op(self, op):
        instr_list = opcodes.get(op.opname, None)
        assert getoption('nostop') or instr_list is not None
        if instr_list: instr_list.render(self, op)

    def _copy_link_vars(self, gen, link):
        target = link.target
        for to_load, to_store in zip(link.args, target.inputargs):
            if to_load.concretetype is not Void:
                gen.load(to_load)
                gen.store(to_store)
                
    def _is_return_block(self, block):
        return (not block.exits) and len(block.inputargs) == 1

    def _is_raise_block(self, block):
        return (not block.exits) and len(block.inputargs) == 2        

class Class(Node):

    """ Represents a class to be emitted.  Note that currently, classes
    are emitted all in one shot, not piecemeal. """

    def __init__(self, name):
        """
        'name' should be a fully qualified Java class name like
        "java.lang.String"
        """
        self.name = name
        self.fields = []
        self.methods = {}      # Maps graph -> Function
        self.rendered = False

    def jvm_type(self):
        return jvm_for_class(self.name)

    def add_field(self, fieldty, fieldnm):
        """ Creates a new field in this with type 'fieldty' (a
        JvmType) and with the name ;fieldnm; (a String).  Must be called
        before render()."""
        assert not self.rendered
        self.fields.append((fieldty, fieldnm))

    def has_method_for(self, graph):
        return graph in self.methods
        
    def add_method(self, func):
        """ Creates a new method in this class, represented by the
        Function object 'func'.  Must be called before render();
        intended to be invoked by the database."""
        assert not self.rendered
        self.methods[func.graph] = func

    def render(self, db, gen):
        self.rendered = True
        gen.begin_class(self.name)

        for fieldty, fieldnm in self.fields:
            gen.add_field(fieldty, fieldnm)

        for method in self.methods.values():
            method.render_func(db, gen)
        
        gen.end_class(self.name)
