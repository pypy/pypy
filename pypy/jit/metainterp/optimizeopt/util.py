import py
from pypy.rlib.objectmodel import r_dict, compute_identity_hash
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp import resoperation, history
from pypy.rlib.debug import make_sure_not_resized
from pypy.jit.metainterp.resoperation import rop

# ____________________________________________________________
# Misc. utilities

def _findall(Class, name_prefix, op_prefix=None):
    result = []
    for name in dir(Class):
        if name.startswith(name_prefix):
            opname = name[len(name_prefix):]
            if opname.isupper():
                assert hasattr(resoperation.rop, opname)
    for value, name in resoperation.opname.items():
        if op_prefix and not name.startswith(op_prefix):
            continue
        if hasattr(Class, name_prefix + name):
            opclass = resoperation.opclasses[getattr(rop, name)]
            assert name in opclass.__name__
            result.append((value, opclass, getattr(Class, name_prefix + name)))
    return unrolling_iterable(result)

def make_dispatcher_method(Class, name_prefix, op_prefix=None, default=None):
    ops = _findall(Class, name_prefix, op_prefix)
    def dispatch(self, op, *args):
        opnum = op.getopnum()
        for value, cls, func in ops:
            if opnum == value:
                assert isinstance(op, cls)
                return func(self, op, *args)
        if default:
            return default(self, op, *args)
    dispatch.func_name = "dispatch_" + name_prefix
    return dispatch


def partition(array, left, right):
    last_item = array[right]
    pivot = last_item.sort_key()
    storeindex = left
    for i in range(left, right):
        if array[i].sort_key() <= pivot:
            array[i], array[storeindex] = array[storeindex], array[i]
            storeindex += 1
    # Move pivot to its final place
    array[storeindex], array[right] = last_item, array[storeindex]
    return storeindex

def quicksort(array, left, right):
    # sort array[left:right+1] (i.e. bounds included)
    if right > left:
        pivotnewindex = partition(array, left, right)
        quicksort(array, left, pivotnewindex - 1)
        quicksort(array, pivotnewindex + 1, right)

def sort_descrs(lst):
    quicksort(lst, 0, len(lst)-1)


def descrlist_hash(l):
    res = 0x345678
    for descr in l:
        y = compute_identity_hash(descr)
        res = intmask((1000003 * res) ^ y)
    return res

def descrlist_eq(l1, l2):
    if len(l1) != len(l2):
        return False
    for i in range(len(l1)):
        if l1[i] is not l2[i]:
            return False
    return True

def descrlist_dict():
    return r_dict(descrlist_eq, descrlist_hash)

# ____________________________________________________________

def args_eq(args1, args2):
    make_sure_not_resized(args1)
    make_sure_not_resized(args2)
    if len(args1) != len(args2):
        return False
    for i in range(len(args1)):
        arg1 = args1[i]
        arg2 = args2[i]
        if arg1 is None:
            if arg2 is not None:
                return False
        elif not arg1.same_box(arg2):
            return False
    return True

def args_hash(args):
    make_sure_not_resized(args)
    res = 0x345678
    for arg in args:
        if arg is None:
            y = 17
        else:
            y = arg._get_hash_()
        res = intmask((1000003 * res) ^ y)
    return res

def args_dict():
    return r_dict(args_eq, args_hash)

def args_dict_box():
    return r_dict(args_eq, args_hash)


# ____________________________________________________________

def equaloplists(oplist1, oplist2, strict_fail_args=True, remap={},
                 text_right=None):
    # try to use the full width of the terminal to display the list
    # unfortunately, does not work with the default capture method of py.test
    # (which is fd), you you need to use either -s or --capture=sys, else you
    # get the standard 80 columns width
    totwidth = py.io.get_terminal_width()
    width = totwidth / 2 - 1
    print ' Comparing lists '.center(totwidth, '-')
    text_right = text_right or 'expected'
    print '%s| %s' % ('optimized'.center(width), text_right.center(width))
    for op1, op2 in zip(oplist1, oplist2):
        txt1 = str(op1)
        txt2 = str(op2)
        while txt1 or txt2:
            print '%s| %s' % (txt1[:width].ljust(width), txt2[:width])
            txt1 = txt1[width:]
            txt2 = txt2[width:]
        assert op1.getopnum() == op2.getopnum()
        assert op1.numargs() == op2.numargs()
        for i in range(op1.numargs()):
            x = op1.getarg(i)
            y = op2.getarg(i)
            assert x.same_box(remap.get(y, y))
        if op2.result in remap:
            if op2.result is None:
                assert op1.result == remap[op2.result]
            else:
                assert op1.result.same_box(remap[op2.result])
        else:
            remap[op2.result] = op1.result
        if op1.getopnum() != rop.JUMP:      # xxx obscure
            assert op1.getdescr() == op2.getdescr()
        if op1.getfailargs() or op2.getfailargs():
            assert len(op1.getfailargs()) == len(op2.getfailargs())
            if strict_fail_args:
                for x, y in zip(op1.getfailargs(), op2.getfailargs()):
                    if x is None:
                        assert remap.get(y, y) is None
                    else:
                        assert x.same_box(remap.get(y, y))
            else:
                fail_args1 = set(op1.getfailargs())
                fail_args2 = set([remap.get(y, y) for y in op2.getfailargs()])
                for x in fail_args1:
                    for y in fail_args2:
                        if x.same_box(y):
                            fail_args2.remove(y)
                            break
                    else:
                        assert False
    assert len(oplist1) == len(oplist2)
    print '-'*totwidth
    return True
