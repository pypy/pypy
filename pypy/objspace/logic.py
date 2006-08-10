from pypy.objspace.proxy import patch_space_in_place
from pypy.interpreter import gateway, baseobjspace

#-- THE BUILTINS ----------------------------------------------------------------------

# this collects all multimethods to be made part of the Space
all_mms = {}
W_Root = baseobjspace.W_Root


#-- MISC ----------------------------------------------------

from pypy.objspace.cclp.misc import app_interp_id, app_switch_debug_info

#-- THREADING/COROUTINING -----------------------------------

from pypy.objspace.cclp.thread import app_future, app_stacklet, app_this_thread

from pypy.objspace.cclp.scheduler import Scheduler,  app_sched_info, \
     app_schedule, app_reset_scheduler, app_sched_all

from pypy.objspace.cclp.global_state import scheduler

#-- COMP. SPACE --------------------------------------------

from pypy.objspace.cclp.space import app_newspace, app_choose, W_CSpace, app_tell

#-- VARIABLE ------------------------------------------------

from pypy.objspace.cclp.variable import app_newvar, wait, app_wait, app_wait_needed, \
     app_is_aliased, app_is_free, app_is_bound, app_alias_of, alias_of, app_bind, \
     app_unify, W_Var, W_CVar, W_Future, app_domain, all_mms as variable_mms, app_entail

from pypy.objspace.cclp.types import app_domain_of

all_mms.update(variable_mms)

#-- CONSTRAINTS ----------------------------------------------

## #------ domains ------------------ 
from pypy.objspace.cclp.constraint import domain 
all_mms.update(domain.all_mms)

W_FiniteDomain = domain.W_FiniteDomain

## # ---- constraints ----------------
from pypy.objspace.cclp.constraint import constraint
all_mms.update(constraint.all_mms)

## #----- distributors ---------------
## from pypy.objspace.constraint import distributor


#-- THE SPACE ---------------------------------------

#class UnificationError(w_RuntimeError):
#    pass


#-- SPACE HELPERS -------------------------------------

nb_forcing_args = {}

def setup():
    nb_forcing_args.update({
        'setattr': 2,   # instead of 3
        'setitem': 2,   # instead of 3
        'get': 2,       # instead of 3
        # ---- irregular operations ----
        'wrap': 0,
        'str_w': 1,
        'int_w': 1,
        'float_w': 1,
        'uint_w': 1,
        'interpclass_w': 1,
        'unwrap': 1,
        'is_true': 1,
        'is_w': 2,
        'newtuple': 0,
        'newlist': 0,
        'newstring': 0,
        'newunicode': 0,
        'newdict': 0,
        'newslice': 0,
        'call_args': 1,
        'marshal_w': 1,
        'log': 1,
        })
    for opname, _, arity, _ in baseobjspace.ObjSpace.MethodTable:
        nb_forcing_args.setdefault(opname, arity)
    for opname in baseobjspace.ObjSpace.IrregularOpTable:
        assert opname in nb_forcing_args, "missing %r" % opname

setup()
del setup

def eqproxy(space, parentfn):
    """shortcuts wait filtering"""
    def eq(w_obj1, w_obj2):
        assert isinstance(w_obj1, W_Root)
        assert isinstance(w_obj2, W_Root)
        # check identity
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(True)
        # check aliasing
        if space.is_true(space.is_free(w_obj1)):
            if space.is_true(space.is_free(w_obj2)):
                if space.is_true(alias_of(space, w_obj1, w_obj2)):
                    return space.newbool(True) # and just go on ...
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return eq

def isproxy(space, parentfn):
    def is_(w_obj1, w_obj2):
        assert isinstance(w_obj1, W_Root)
        assert isinstance(w_obj2, W_Root)
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(True)
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return is_

def cmpproxy(space, parentfn):
    def cmp(w_obj1, w_obj2):
        assert isinstance(w_obj1, W_Root)
        assert isinstance(w_obj2, W_Root)
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(0)
        if space.is_true(space.is_free(w_obj1)):
            if space.is_true(space.is_free(w_obj2)):
                if space.is_true(alias_of(space, w_obj1, w_obj2)):
                    return space.newbool(0) # and just go on ...
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return cmp

def neproxy(space, parentfn):
    def ne(w_obj1, w_obj2):
        assert isinstance(w_obj1, W_Root)
        assert isinstance(w_obj2, W_Root)
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(False)
        if space.is_true(space.is_free(w_obj1)):
            if space.is_true(space.is_free(w_obj2)):
                if space.is_true(alias_of(space, w_obj1, w_obj2)):
                    return space.newbool(False) # and just go on ...
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return ne

def proxymaker(space, opname, parentfn):
    if opname == "eq":
        return eqproxy(space, parentfn)
    if opname == "is_": # FIXME : is_, is_w ?
        return isproxy(space, parentfn)
    if opname == "ne":
        return neproxy(space, parentfn)
    if opname == "cmp":
        return cmpproxy(space, parentfn)
    nb_args = nb_forcing_args[opname]
    if nb_args == 0:
        proxy = None
    elif nb_args == 1:
        def proxy(w1, *extra):
            w1 = wait(space, w1)
            return parentfn(w1, *extra)
    elif nb_args == 2:
        def proxy(w1, w2, *extra):
            w1 = wait(space, w1)
            w2 = wait(space, w2)
            return parentfn(w1, w2, *extra)
    elif nb_args == 3:
        def proxy(w1, w2, w3, *extra):
            w1 = wait(space, w1)
            w2 = wait(space, w2)
            w3 = wait(space, w3)
            return parentfn(w1, w2, w3, *extra)
    else:
        raise NotImplementedError("operation %r has arity %d" %
                                  (opname, nb_args))
    return proxy


from pypy.objspace.std import stdtypedef 
from pypy.tool.sourcetools import func_with_new_name


def Space(*args, **kwds):
    # for now, always make up a wrapped StdObjSpace
    from pypy.objspace import std
    space = std.Space(*args, **kwds)

    # multimethods hack
    space.model.typeorder[W_Var] = [(W_Var, None), (W_Root, None)] # None means no conversion
    space.model.typeorder[W_Future] = [(W_Future, None), (W_Var, None)]
    space.model.typeorder[W_CVar] = [(W_CVar, None), (W_Var, None)]
    space.model.typeorder[W_CSpace] = [(W_CSpace, None), (baseobjspace.Wrappable, None)]
    space.model.typeorder[W_FiniteDomain] = [(W_FiniteDomain, None), (W_Root, None)] 


    for name in all_mms.keys():
        exprargs, expr, miniglobals, fallback = (
            all_mms[name].install_not_sliced(space.model.typeorder, baked_perform_call=False))
        func = stdtypedef.make_perform_trampoline('__mm_' + name,
                                                  exprargs, expr, miniglobals,
                                                  all_mms[name])
        # e.g. add(space, w_x, w_y)
        def make_boundmethod(func=func):
            def boundmethod(*args):
                return func(space, *args)
            return func_with_new_name(boundmethod, 'boundmethod_'+name)
        boundmethod = make_boundmethod()
        setattr(space, name, boundmethod)  # store into 'space' instance
    # /multimethods hack

    #-- variable -------
    space.setitem(space.builtin.w_dict, space.wrap('newvar'),
                  space.wrap(app_newvar))
    space.setitem(space.builtin.w_dict, space.wrap('domain'),
                  space.wrap(app_domain))
    space.setitem(space.builtin.w_dict, space.wrap('domain_of'),
                  space.wrap(app_domain_of))
    space.setitem(space.builtin.w_dict, space.wrap('is_free'),
                  space.wrap(app_is_free))
    space.setitem(space.builtin.w_dict, space.wrap('is_bound'),
                  space.wrap(app_is_bound))
    space.setitem(space.builtin.w_dict, space.wrap('alias_of'),
                  space.wrap(app_alias_of))
    space.setitem(space.builtin.w_dict, space.wrap('is_aliased'),
                  space.wrap(app_is_aliased))
    space.setitem(space.builtin.w_dict, space.wrap('bind'),
                 space.wrap(app_bind))
    space.setitem(space.builtin.w_dict, space.wrap('entail'),
                 space.wrap(app_entail))
    space.setitem(space.builtin.w_dict, space.wrap('unify'),
                 space.wrap(app_unify))
    #-- domain -------
    space.setitem(space.builtin.w_dict, space.wrap('FiniteDomain'),
                 space.wrap(domain.app_make_fd))
    space.setitem(space.builtin.w_dict, space.wrap('intersection'),
                 space.wrap(domain.app_intersection))
    #-- constraints ----
    space.setitem(space.builtin.w_dict, space.wrap('make_expression'),
                  space.wrap(constraint.app_make_expression))
    space.setitem(space.builtin.w_dict, space.wrap('all_diff'),
                 space.wrap(constraint.app_make_alldistinct))
##     #-- distributor --
##     space.setitem(space.builtin.w_dict, space.wrap('NaiveDistributor'),
##                  space.wrap(distributor.app_make_naive_distributor))
##     space.setitem(space.builtin.w_dict, space.wrap('SplitDistributor'),
##                  space.wrap(distributor.app_make_split_distributor))
##     space.setitem(space.builtin.w_dict, space.wrap('DichotomyDistributor'),
##                  space.wrap(distributor.app_make_dichotomy_distributor))
    #-- threading --
    space.setitem(space.builtin.w_dict, space.wrap('future'),
                 space.wrap(app_future))
    space.setitem(space.builtin.w_dict, space.wrap('stacklet'),
                 space.wrap(app_stacklet))
    space.setitem(space.builtin.w_dict, space.wrap('wait'),
                 space.wrap(app_wait))
    space.setitem(space.builtin.w_dict, space.wrap('wait_needed'),
                  space.wrap(app_wait_needed))
    space.setitem(space.builtin.w_dict, space.wrap('sched_info'),
                  space.wrap(app_sched_info))
    space.setitem(space.builtin.w_dict, space.wrap('sched_all'),
                  space.wrap(app_sched_all))
    space.setitem(space.builtin.w_dict, space.wrap('schedule'),
                  space.wrap(app_schedule))
    space.setitem(space.builtin.w_dict, space.wrap('this_thread'),
                  space.wrap(app_this_thread))
    space.setitem(space.builtin.w_dict, space.wrap('reset_scheduler'),
                  space.wrap(app_reset_scheduler))
    #-- comp. spaces --
    space.setitem(space.builtin.w_dict, space.wrap('newspace'),
                  space.wrap(app_newspace))
    space.setitem(space.builtin.w_dict, space.wrap('choose'),
                  space.wrap(app_choose))
    space.setitem(space.builtin.w_dict, space.wrap('tell'),
                  space.wrap(app_tell))

    #-- misc -----
    space.setitem(space.builtin.w_dict, space.wrap('interp_id'),
                  space.wrap(app_interp_id))
    space.setitem(space.builtin.w_dict, space.wrap('switch_debug_info'),
                  space.wrap(app_switch_debug_info))

    #-- path to the applevel modules --
    import pypy.objspace.constraint
    import os
    dir = os.path.dirname(pypy.objspace.constraint.__file__)
    dir = os.path.join(dir, 'applevel')
    space.call_method(space.sys.get('path'), 'append', space.wrap(dir))

    # make sure that _stackless is imported
    w_modules = space.getbuiltinmodule('_stackless')
    # cleanup func called from space.finish()
    def exitfunc():
        pass
    
    app_exitfunc = gateway.interp2app(exitfunc, unwrap_spec=[])
    space.setitem(space.sys.w_dict, space.wrap("exitfunc"), space.wrap(app_exitfunc))

    # capture one non-blocking op
    space.is_nb_ = space.is_

    # do the magic
    patch_space_in_place(space, 'logic', proxymaker)

    # instantiate singleton scheduler
    scheduler.append(Scheduler(space))
    return space
