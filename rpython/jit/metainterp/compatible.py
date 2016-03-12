from rpython.jit.metainterp.history import newconst

def do_call(cpu, argboxes, descr):
    from rpython.jit.metainterp.history import INT, REF, FLOAT, VOID
    from rpython.jit.metainterp.blackhole import NULL
    # XXX XXX almost copy from executor.py
    rettype = descr.get_result_type()
    # count the number of arguments of the different types
    count_i = count_r = count_f = 0
    for i in range(1, len(argboxes)):
        type = argboxes[i].type
        if   type == INT:   count_i += 1
        elif type == REF:   count_r += 1
        elif type == FLOAT: count_f += 1
    # allocate lists for each type that has at least one argument
    if count_i: args_i = [0] * count_i
    else:       args_i = None
    if count_r: args_r = [NULL] * count_r
    else:       args_r = None
    if count_f: args_f = [longlong.ZEROF] * count_f
    else:       args_f = None
    # fill in the lists
    count_i = count_r = count_f = 0
    for i in range(1, len(argboxes)):
        box = argboxes[i]
        if   box.type == INT:
            args_i[count_i] = box.getint()
            count_i += 1
        elif box.type == REF:
            args_r[count_r] = box.getref_base()
            count_r += 1
        elif box.type == FLOAT:
            args_f[count_f] = box.getfloatstorage()
            count_f += 1
    # get the function address as an integer
    func = argboxes[0].getint()
    # do the call using the correct function from the cpu
    if rettype == INT:
        return newconst(cpu.bh_call_i(func, args_i, args_r, args_f, descr))
    if rettype == REF:
        return newconst(cpu.bh_call_r(func, args_i, args_r, args_f, descr))
    if rettype == FLOAT:
        return newconst(cpu.bh_call_f(func, args_i, args_r, args_f, descr))
    if rettype == VOID:
        # don't even need to call the void function, result will always match
        return None
    raise AssertionError("bad rettype")

class CompatibilityCondition(object):
    """ A collections of conditions that an object needs to fulfil. """
    def __init__(self, ptr):
        self.known_valid = ptr
        self.pure_call_conditions = []

    def record_pure_call(self, op, res):
        self.pure_call_conditions.append((op, res))

    def check_compat(self, cpu, ref):
        for op, correct_res in self.pure_call_conditions:
            calldescr = op.getdescr()
            # change exactly the first argument
            arglist = op.getarglist()
            arglist[1] = newconst(ref)
            res = do_call(cpu, arglist, calldescr)
            if not res.same_constant(correct_res):
                return False
        return True
