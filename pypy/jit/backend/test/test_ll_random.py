import py
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.jit.backend.test import test_random
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.history import ConstInt, ConstPtr, ConstAddr
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.rarithmetic import intmask

class LLtypeOperationBuilder(test_random.OperationBuilder):

    def get_structptr_var(self, r, must_have_vtable=False):
        while True:
            if self.ptrvars and r.random() < 0.8:
                v, S = r.choice(self.ptrvars)
            elif self.prebuilt_ptr_consts and r.random() < 0.7:
                v, S, _ = r.choice(self.prebuilt_ptr_consts)
            else:
                must_have_vtable = must_have_vtable or r.random() < 0.5
                p = self.get_random_structure(r, has_vtable=must_have_vtable)
                S = lltype.typeOf(p).TO
                v = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, p))
                self.prebuilt_ptr_consts.append((v, S, self.field_values(p)))
            if not (must_have_vtable and S._names[0] != 'parent'):
                break
        return v, S

    def get_random_structure_type(self, r, with_vtable=None):
        fields = []
        kwds = {}
        if with_vtable:
            fields.append(('parent', rclass.OBJECT))
            kwds['hints'] = {'vtable': with_vtable._obj}
        for i in range(r.randrange(1, 5)):
            fields.append(('f%d' % i, lltype.Signed))
        S = lltype.GcStruct('S%d' % self.counter, *fields, **kwds)
        self.counter += 1
        return S

    def get_random_structure_type_and_vtable(self, r):
        vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        S = self.get_random_structure_type(r, with_vtable=vtable)
        name = S._name
        vtable.name = lltype.malloc(lltype.Array(lltype.Char), len(name)+1,
                                    immortal=True)
        for i in range(len(name)):
            vtable.name[i] = name[i]
        vtable.name[len(name)] = '\x00'
        return S, vtable

    def get_random_structure(self, r, has_vtable=False):
        if has_vtable:
            S, vtable = self.get_random_structure_type_and_vtable(r)
            p = lltype.malloc(S)
            p.parent.typeptr = vtable
        else:
            S = self.get_random_structure_type(r)
            p = lltype.malloc(S)
        for fieldname in lltype.typeOf(p).TO._names:
            if fieldname != 'parent':
                setattr(p, fieldname, r.random_integer())
        return p

    def field_values(self, p):
        dic = {}
        for fieldname in lltype.typeOf(p).TO._names:
            if fieldname != 'parent':
                dic[fieldname] = getattr(p, fieldname)
        return dic

    def print_loop_prebuilt(self, names, writevar, s):
        written = {}
        for v, S, fields in self.prebuilt_ptr_consts:
            if S not in written:
                print >>s, '    %s = lltype.GcStruct(%r,' % (S._name, S._name)
                for name in S._names:
                    if name == 'parent':
                        print >>s, "              ('parent', rclass.OBJECT),"
                    else:
                        print >>s, '              (%r, lltype.Signed),'%(name,)
                print >>s, '              )'
                if S._names[0] == 'parent':
                    print >>s, '    %s_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)' % (S._name,)
                written[S] = True
            print >>s, '    p = lltype.malloc(%s)' % (S._name,)
            if S._names[0] == 'parent':
                print >>s, '    p.parent.typeptr = %s_vtable' % (S._name,)
            for name, value in fields.items():
                print >>s, '    p.%s = %d' % (name, value)
            writevar(v, 'preb', 'lltype.cast_opaque_ptr(llmemory.GCREF, p)')

# ____________________________________________________________

class GuardClassOperation(test_random.GuardOperation):
    def gen_guard(self, builder, r):
        ptrvars = [(v, S) for (v, S) in builder.ptrvars
                          if S._names[0] == 'parent']
        if not ptrvars:
            raise test_random.CannotProduceOperation
        v, S = r.choice(ptrvars)
        if r.random() < 0.3:
            v2, S2 = v, S
        else:
            v2, S2 = builder.get_structptr_var(r, must_have_vtable=True)
        vtable = S._hints['vtable']._as_ptr()
        vtable2 = S2._hints['vtable']._as_ptr()
        c_vtable2 = ConstAddr(llmemory.cast_ptr_to_adr(vtable2), builder.cpu)
        op = ResOperation(self.opnum, [v, c_vtable2], None)
        return op, (vtable == vtable2)

class GetFieldOperation(test_random.AbstractOperation):
    def field_descr(self, builder, r):
        v, S = builder.get_structptr_var(r)
        names = S._names
        if names[0] == 'parent':
            names = names[1:]
        name = r.choice(names)
        descr = builder.cpu.fielddescrof(S, name)
        descr._random_info = 'cpu.fielddescrof(%s, %r)' % (S._name, name)
        return v, descr

    def produce_into(self, builder, r):
        while True:
            try:
                v, descr = self.field_descr(builder, r)
                self.put(builder, [v], descr)
            except lltype.UninitializedMemoryAccess:
                continue
            break

class SetFieldOperation(GetFieldOperation):
    def produce_into(self, builder, r):
        v, descr = self.field_descr(builder, r)
        if r.random() < 0.3:
            w = ConstInt(r.random_integer())
        else:
            w = r.choice(builder.intvars)
        builder.do(self.opnum, [v, w], descr)

class NewOperation(test_random.AbstractOperation):
    def size_descr(self, builder, S):
        descr = builder.cpu.sizeof(S)
        descr._random_info = 'cpu.sizeof(%s)' % (S._name,)
        return descr

    def produce_into(self, builder, r):
        if self.opnum == rop.NEW_WITH_VTABLE:
            S, vtable = builder.get_random_structure_type_and_vtable(r)
            args = [ConstAddr(llmemory.cast_ptr_to_adr(vtable), builder.cpu)]
        else:
            S = builder.get_random_structure_type(r)
            args = []
        v_ptr = builder.do(self.opnum, args, self.size_descr(builder, S))
        builder.ptrvars.append((v_ptr, S))

class CallOperation(test_random.AbstractOperation):
    def produce_into(self, builder, r):
        subset = builder.subset_of_intvars(r)
        if len(subset) == 0:
            sum = ""
            funcargs = ""
        else:
            funcargs = ", ".join(['arg_%d' % i for i in range(len(subset))])
            sum = "intmask(%s)" % " + ".join(['arg_%d' % i for i in range(len(subset))])
        code = py.code.Source("""
        def f(%s):
           return %s
        """ % (funcargs, sum)).compile()
        d = {'intmask' : intmask}
        exec code in d

        if len(subset) == 0:
            RES = lltype.Void
        else:
            RES = lltype.Signed
        TP = lltype.FuncType([lltype.Signed] * len(subset), RES)
        ptr = llhelper(lltype.Ptr(TP), d['f'])
        c_addr = ConstAddr(llmemory.cast_ptr_to_adr(ptr), builder.cpu)
        args = [c_addr] + subset
        descr = builder.cpu.calldescrof(TP, TP.ARGS, TP.RESULT)
        self.put(builder, args, descr)
        op = ResOperation(rop.GUARD_NO_EXCEPTION, [], None)
        op.suboperations = [ResOperation(rop.FAIL, [], None)]
        builder.loop.operations.append(op)

# ____________________________________________________________

OPERATIONS = test_random.OPERATIONS[:]

for i in range(4):      # make more common
    OPERATIONS.append(GetFieldOperation(rop.GETFIELD_GC))
    OPERATIONS.append(GetFieldOperation(rop.GETFIELD_GC))
    OPERATIONS.append(SetFieldOperation(rop.SETFIELD_GC))
    OPERATIONS.append(NewOperation(rop.NEW))
    OPERATIONS.append(NewOperation(rop.NEW_WITH_VTABLE))

    OPERATIONS.append(GuardClassOperation(rop.GUARD_CLASS))
    OPERATIONS.append(CallOperation(rop.CALL))

LLtypeOperationBuilder.OPERATIONS = OPERATIONS

# ____________________________________________________________

def test_ll_random_function():
    test_random.test_random_function(LLtypeOperationBuilder)
