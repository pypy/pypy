import py
from pypy.objspace.flow.model import Block, Constant, Variable, Link
from pypy.objspace.flow.model import flatten, mkentrymap, traverse
from pypy.rpython import lltype
from pypy.translator.backendoptimization import remove_same_as 
from pypy.translator.unsimplify import remove_double_links                     
from pypy.translator.llvm2.node import LLVMNode
from pypy.translator.llvm2.log import log 
log = log.funcnode


class FuncTypeNode(LLVMNode):
    func_type_node_counter = 0

    def __init__(self, db, type_):
        self.db = db
        assert isinstance(type_, lltype.FuncType)
        self.type_ = type_
        ref = '"ft.%s.%s"' % (type_, FuncTypeNode.func_type_node_counter)
        self.ref = ref.replace(" ", "")
        FuncTypeNode.func_type_node_counter += 1
        
    def __str__(self):
        return "<FuncTypeNode %r>" % self.ref

    def setup(self):
        self.db.prepare_repr_arg_type(self.type_.RESULT)
        self.db.prepare_repr_arg_type_multi(self.type_._trueargs())

    def writedatatypedecl(self, codewriter):
        returntype = self.db.repr_arg_type(self.type_.RESULT)
        inputargtypes = self.db.repr_arg_type_multi(self.type_._trueargs())
        decl = "%s type %s (%s)*" % (self.ref, returntype,
                                     ", ".join(inputargtypes))
        codewriter.funcdef(self.ref, returntype, inputargtypes)


class FuncNode(LLVMNode):
    _issetup = False 

    def __init__(self, db, const_ptr_func):
        self.db = db
        self.ref = "%" + const_ptr_func.value._obj._name
        self.graph = const_ptr_func.value._obj.graph 
        remove_same_as(self.graph) 
        remove_double_links(self.db._translator, self.graph) 
        
    def __str__(self):
        return "<FuncNode %r>" %(self.ref,)
    
    def setup(self):
        log("setup", self)
        def visit(node):
            if isinstance(node, Link):
                map(self.db.prepare_arg, node.args)
            elif isinstance(node, Block):
                map(self.db.prepare_arg, node.inputargs)
                for op in node.operations:
                    map(self.db.prepare_arg, op.args)
                    self.db.prepare_arg(op.result)
        assert self.graph, "cannot traverse"
        traverse(visit, self.graph)
        self._issetup = True
    # ______________________________________________________________________
    # main entry points from genllvm 
    def writedecl(self, codewriter): 
        codewriter.declare(self.getdecl())

    def writeimpl(self, codewriter):
        assert self._issetup 
        graph = self.graph
        log.writeimpl(graph.name)
        codewriter.openfunc(self.getdecl())
        nextblock = graph.startblock
        args = graph.startblock.inputargs 
        l = [x for x in flatten(graph) if isinstance(x, Block)]
        self.block_to_name = {}
        for i, block in enumerate(l):
            self.block_to_name[block] = "block%s" % i
        for block in l:
            codewriter.label(self.block_to_name[block])
            for name in 'startblock returnblock exceptblock'.split():
                if block is getattr(graph, name):
                    getattr(self, 'write_' + name)(codewriter, block)
                    break
            else:
                self.write_block(codewriter, block)
        codewriter.closefunc()

    # ______________________________________________________________________
    # writing helpers for entry points

    def getdecl(self):
        assert self._issetup 
        startblock = self.graph.startblock
        returnblock = self.graph.returnblock
        inputargs = self.db.repr_arg_multi(startblock.inputargs)
        inputargtypes = self.db.repr_arg_type_multi(startblock.inputargs)
        returntype = self.db.repr_arg_type(self.graph.returnblock.inputargs[0])
        result = "%s %s" % (returntype, self.ref)
        args = ["%s %s" % item for item in zip(inputargtypes, inputargs)]
        result += "(%s)" % ", ".join(args)
        return result 

    def write_block(self, codewriter, block):
        self.write_block_phi_nodes(codewriter, block)
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)


    def write_block_phi_nodes(self, codewriter, block):
        entrylinks = mkentrymap(self.graph)[block]
        entrylinks = [x for x in entrylinks if x.prevblock is not None]
        inputargs = self.db.repr_arg_multi(block.inputargs)
        inputargtypes = self.db.repr_arg_type_multi(block.inputargs)
        for i, (arg, type_) in enumerate(zip(inputargs, inputargtypes)):
            names = self.db.repr_arg_multi([link.args[i] for link in entrylinks])
            blocknames = [self.block_to_name[link.prevblock]
                              for link in entrylinks]
            if type_ != "void":
                codewriter.phi(arg, type_, names, blocknames) 

    def write_block_branches(self, codewriter, block):
        if len(block.exits) == 1:
            codewriter.br_uncond(self.block_to_name[block.exits[0].target])
        elif len(block.exits) == 2:
            switch = self.db.repr_arg(block.exitswitch)
            codewriter.br(switch, self.block_to_name[block.exits[0].target],
                          self.block_to_name[block.exits[1].target])

    def write_block_operations(self, codewriter, block):
        opwriter = OpWriter(self.db, codewriter)
        for op in block.operations:
            opwriter.write_operation(op)
    def write_startblock(self, codewriter, block):
        self.write_block_operations(codewriter, block)
        self.write_block_branches(codewriter, block)

    def write_returnblock(self, codewriter, block):
        assert len(block.inputargs) == 1
        self.write_block_phi_nodes(codewriter, block)
        inputargtype = self.db.repr_arg_type(block.inputargs[0])
        inputarg = self.db.repr_arg(block.inputargs[0])
        if inputargtype != "void":
            codewriter.ret(inputargtype, inputarg)
        else:
            codewriter.ret_void()

class OpWriter(object):
    binary_operations = {'int_mul': 'mul',
                         'int_add': 'add',
                         'int_sub': 'sub',
                         'int_floordiv': 'div',
                         'int_mod': 'rem',
                         'int_lt': 'setlt',
                         'int_le': 'setle',
                         'int_eq': 'seteq',
                         'int_ne': 'setne',
                         'int_ge': 'setge',
                         'int_gt': 'setgt',

                         'uint_mul': 'mul',
                         'uint_add': 'add',
                         'uint_sub': 'sub',
                         'uint_floordiv': 'div',
                         'uint_mod': 'rem',
                         'uint_lt': 'setlt',
                         'uint_le': 'setle',
                         'uint_eq': 'seteq',
                         'uint_ne': 'setne',
                         'uint_ge': 'setge',
                         'uint_gt': 'setgt',

                         'float_mul': 'mul',
                         'float_add': 'add',
                         'float_sub': 'sub',
                         'float_truediv': 'div',
                         'float_mod': 'rem',
                         'float_lt': 'setlt',
                         'float_le': 'setle',
                         'float_eq': 'seteq',
                         'float_ne': 'setne',
                         'float_ge': 'setge',
                         'float_gt': 'setgt',
                         }

    def __init__(self, db, codewriter):
        self.db = db
        self.codewriter = codewriter

    def write_operation(self, op):
        if op.opname in self.binary_operations:
            self.binaryop(op)
        else:
            meth = getattr(self, op.opname, None)
            assert meth is not None, "operation %r not found" %(op.opname,)
            meth(op)    

    def binaryop(self, op):
        name = self.binary_operations[op.opname]
        assert len(op.args) == 2
        self.codewriter.binaryop(name,
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]),
                                 self.db.repr_arg(op.args[1]))

    def cast_primitive(self, op): #works for all primitives
        assert len(op.args) == 1
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        fromvar = self.db.repr_arg(op.args[0])
        fromtype = self.db.repr_arg_type(op.args[0])
        self.codewriter.cast(targetvar, fromtype, fromvar, targettype)

    cast_bool_to_int = cast_primitive
    cast_bool_to_uint = uint_is_true = cast_primitive

    def int_is_true(self, op):
        self.codewriter.binaryop("setne",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]),
                                 "0")

    uint_is_true = int_is_true

    def float_is_true(self, op):
        self.codewriter.binaryop("setne",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]),
                                 "0.0")
    
    def direct_call(self, op):
        assert len(op.args) >= 1
        targetvar = self.db.repr_arg(op.result)
        returntype = self.db.repr_arg_type(op.result)
        functionref = self.db.repr_arg(op.args[0])
        argrefs = self.db.repr_arg_multi(op.args[1:])
        argtypes = self.db.repr_arg_type_multi(op.args[1:])
        if returntype != "void":
            self.codewriter.call(targetvar, returntype, functionref, argrefs,
                                 argtypes)
        else:
            self.codewriter.call_void(functionref, argrefs, argtypes)

    def malloc(self, op): 
        targetvar = self.db.repr_arg(op.result) 
        arg = op.args[0]
        assert (isinstance(arg, Constant) and 
                isinstance(arg.value, lltype.Struct))
        #XXX unclean
        type = self.db.obj2node[arg.value].ref
        self.codewriter.malloc(targetvar, type) 

    def malloc_varsize(self, op):
        targetvar = self.db.repr_arg(op.result)
        arg_type = op.args[0]
        assert (isinstance(arg_type, Constant) and 
                isinstance(arg_type.value, lltype.Array))
        #XXX unclean
        struct_type = self.db.obj2node[arg_type.value].ref
        struct_cons = self.db.obj2node[arg_type.value].constructor_ref
        argrefs = self.db.repr_arg_multi(op.args[1:])
        argtypes = self.db.repr_arg_type_multi(op.args[1:])
        self.codewriter.call(targetvar, struct_type + "*", struct_cons,
                             argrefs, argtypes)

    def getfield(self, op): 
        tmpvar = self.db.repr_tmpvar()
        typ = self.db.repr_arg_type(op.args[0]) 
        typevar = self.db.repr_arg(op.args[0])
        fieldnames = list(op.args[0].concretetype.TO._names)
        index = fieldnames.index(op.args[1].value)
        self.codewriter.getelementptr(tmpvar, typ, typevar, ("uint", index))
        
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        assert targettype != "void"
        #XXX This doesnt work - yet
        #if isinstance(op.result.concretetype, lltype.Ptr):        
        #    self.codewriter.cast(targetvar, targettype, tmpvar, targettype)
        #else:
            # Moving to correct result variable
            #self.codewriter.load(targetvar, targettype, tmpvar)
        self.codewriter.load(targetvar, targettype, tmpvar)    
    getsubstruct = getfield

    def setfield(self, op): 
        tmpvar = self.db.repr_tmpvar()
        type = self.db.repr_arg_type(op.args[0]) 
        typevar = self.db.repr_arg(op.args[0]) 
        fieldnames = list(op.args[0].concretetype.TO._names)
        index = fieldnames.index(op.args[1].value)
        self.codewriter.getelementptr(tmpvar, type, typevar, ("uint", index))
        valuevar = self.db.repr_arg(op.args[2]) 
        valuetype = self.db.repr_arg_type(op.args[2])
        assert valuetype != "void"
        self.codewriter.store(valuetype, valuevar, tmpvar) 

    def getarrayitem(self, op):
        var = self.db.repr_arg(op.args[0])
        vartype = self.db.repr_arg_type(op.args[0])
        index = self.db.repr_arg(op.args[1])
        indextype = self.db.repr_arg_type(op.args[1])

        tmpvar = self.db.repr_tmpvar()
        self.codewriter.getelementptr(tmpvar, vartype, var,
                                      ("uint", 1), (indextype, index))

        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)

        # Ditto see getfield
        if not isinstance(op.result.concretetype, lltype.Ptr):        
            self.codewriter.load(targetvar, targettype, tmpvar)
        else:
            # XXX noop
            self.codewriter.cast(targetvar, targettype, tmpvar, targettype)

    def setarrayitem(self, op):
        array = self.db.repr_arg(op.args[0])
        arraytype = self.db.repr_arg_type(op.args[0])
        index = self.db.repr_arg(op.args[1])
        indextype = self.db.repr_arg_type(op.args[1])

        tmpvar = self.db.repr_tmpvar()
        self.codewriter.getelementptr(tmpvar, arraytype, array,
                                      ("uint", 1), (indextype, index))

        valuevar = self.db.repr_arg(op.args[2]) 
        valuetype = self.db.repr_arg_type(op.args[2])
        self.codewriter.store(valuetype, valuevar, tmpvar) 

    def getarraysize(self, op):
        var = self.db.repr_arg(op.args[0])
        vartype = self.db.repr_arg_type(op.args[0])
        tmpvar = self.db.repr_tmpvar()
        self.codewriter.getelementptr(tmpvar, vartype, var, ("uint", 0))
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        self.codewriter.load(targetvar, targettype, tmpvar)
