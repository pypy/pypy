import py
from pypy.interpreter import gateway, module, error
from pypy.interpreter.optimizer import optimize

class BytecodeHelper(object):
    def __init__(self, pycode):
        self.pycode = pycode

    def has(self, opcode):
        return True # XXX

    def iterate_records(self):
        for record in self.pycode.recorded:
            yield record

class TestVersioning:
    def coderecord(self, source, functionname, args):
        space = self.space

        source = str(py.code.Source(source).strip()) + '\n'

        w = space.wrap
        w_code = space.builtin.call('compile', 
                w(source), w('<string>'), w('exec'), w(0), w(0))

        tempmodule = module.Module(space, w("__temp__"))
        w_glob = tempmodule.w_dict
        space.setitem(w_glob, w("__builtins__"), space.builtin)

        code = space.unwrap(w_code)
        code.exec_code(space, w_glob, w_glob)

        w_args = [w(a) for a in args]
        w_func = space.getitem(w_glob, w(functionname))
        fcode = space.unwrap(space.getattr(w_func, w('__code__')))
        fcode.start_type_recording()
        try:
            w_a = space.call_function(w_func, *w_args)
        except error.OperationError as e:
            #e.print_detailed_traceback(space)
            return '<<<%s>>>' % e.errorstr(space)
        a = space.unwrap(w_a)
        return a, BytecodeHelper(fcode)

    def codetest(self, source, functionname, args):
        space = self.space

        source = str(py.code.Source(source).strip()) + '\n'

        w = space.wrap
        w_code = space.builtin.call('compile', 
                w(source), w('<string>'), w('exec'), w(0), w(0))

        tempmodule = module.Module(space, w("__temp__"))
        w_glob = tempmodule.w_dict
        space.setitem(w_glob, w("__builtins__"), space.builtin)

        code = space.unwrap(w_code)
        code.exec_code(space, w_glob, w_glob)

        w_args = [w(a) for a in args]
        w_func = space.getitem(w_glob, w(functionname))
        fcode = space.unwrap(space.getattr(w_func, w('__code__')))
        fcode.start_type_recording()
        try:
            w_a = space.call_function(w_func, *w_args)
        except error.OperationError as e:
            #e.print_detailed_traceback(space)
            return '<<<%s>>>' % e.errorstr(space)

        opt_fcode = optimize(fcode)
        space.setitem(w_func, w('__code__'), opt_fcode)
        try:
            w_b = space.call_function(w_func, *w_args)
        except error.OperationError as e:
            #e.print_detailed_traceback(space)
            return '<<<%s>>>' % e.errorstr(space)
        a = space.unwrap(w_a)
        b = space.unwrap(w_b)
        return a, BytecodeHelper(fcode), b, BytecodeHelper(opt_fcode)

    def recorded(self, code, gathered):
        needed = sorted(gathered[:], lambda x: (x[0],x[1]))
        it = iter(needed)
        cur = next(it)
        import pdb; pdb.set_trace()
        for i,stackpos,typeinfo in code.iterate_records():
            # for the current byte code consume each entry in
            # gathered
            while True:
                j = cur[0]
                if i == j:
                    if stackpos == cur[1] and typeinfo == cur[2]:
                        # match! move the iterator one step forward
                        try:
                            cur = next(it)
                        except StopIteration:
                            # matched them all!
                            return True
                    continue
                break

        return False

    def test_record_types(self):
        a, acode = self.coderecord("""
        def f(v):
            return v + 1.0
        """, 'f', [1.0])
        assert a == 2.0
        assert self.recorded(acode, [
                (0, 1, 'FLOAT')
            ])

    def test_specialize_float(self):
        code = """
        def f(v):
            return v + 1.0
        """
        a, acode, b, bcode = self.codetest(code, 'f', [1.0])
        assert a == 2.0 == b
        assert not bcode.has(BINARY_ADD)
