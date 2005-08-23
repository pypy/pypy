from pypy.translator.c.support import cdecl
from pypy.rpython.lltype import Ptr, PyObject

PyObjPtr = Ptr(PyObject)

class BasicGcPolicy:
    
    def __init__(self, db):
        self.db = db

    def pyobj_incref(self, expr, T):
        if T == PyObjPtr:
            return 'Py_XINCREF(%s);' % expr
        return ''

    def pyobj_decref(self, expr, T):
        return 'Py_XDECREF(%s);' % expr

    def push_alive(self, expr, T):
        if isinstance(T, Ptr) and T._needsgc():
            if expr == 'NULL':    # hum
                return ''
            if T.TO == PyObject:
                return self.pyobj_incref(expr, T)
            else:
                return self.push_alive_nopyobj(expr, T)
        return ''

    def pop_alive(self, expr, T):
        if isinstance(T, Ptr) and T._needsgc():
            if T.TO == PyObject:
                return self.pyobj_decref(expr, T)
            else:
                return self.pop_alive_nopyobj(expr, T)
        return ''


class RefcountingGcPolicy(BasicGcPolicy):

    def push_alive_nopyobj(self, expr, T):
        defnode = self.db.gettypedefnode(T.TO)
        if defnode.gcheader is not None:
            return 'if (%s) %s->%s++;' % (expr, expr, defnode.gcheader)

    def pop_alive_nopyobj(self, expr, T):
        defnode = self.db.gettypedefnode(T.TO)
        if defnode.gcheader is not None:
            dealloc = 'OP_FREE'
            if defnode.gcinfo:
                dealloc = defnode.gcinfo.deallocator or dealloc
            return 'if (%s && !--%s->%s) %s(%s);' % (expr, expr,
                                                     defnode.gcheader,
                                                     dealloc,
                                                     expr)

    def push_alive_op_result(self, opname, expr, T):
        if opname !='direct_call' and T != PyObjPtr:
            return self.push_alive(expr, T)
        return ''

    def write_barrier(self, result, newvalue, T, targetexpr):  
        decrefstmt = self.pop_alive('prev', T)
        increfstmt = self.push_alive(newvalue, T)
        if increfstmt:
            result.append(increfstmt)
        if decrefstmt:
            result.insert(0, '{ %s = %s;' % (
                cdecl(self.db.gettype(T), 'prev'),
                targetexpr))
            result.append(decrefstmt)
            result.append('}')


