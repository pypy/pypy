#python imports
try:
    import readline
    import rlcompleter
    have_readline = True

except:
    have_readline = False

import __builtin__ as cpy_builtin
                        
#pypy imports
import autopath
from pypy.objspace.std import Space
from pypy.interpreter.baseobjspace import OperationError

def found_missing(name, attrs, w_obj, space):
    #we cannot do a dir on a pypy wrapped object
    found_attrs = []
    missing_attrs = []

    for a in attrs:
        try:
            try:
                w_name = space.wrap(a)
                t = space.getattr(w_obj, w_name)
                found_attrs.append(a)
            except OperationError: #over-broad?
                missing_attrs.append(a)
                
        except: #something horrible happened
            print 'In builtin: ', name, 'Blew Up Trying to get attr: ', repr(a)
            missing_attrs.append(a)
            
    return found_attrs, missing_attrs

def check_for_attrs(name, space):
    try:
        cpy_attrs = dir(getattr(cpy_builtin, name))
    except AttributeError:
        print "AttributeError: CPython module __builtin__ has no attribute '%s'" % name
        return [], []
    
    try:
        w_obj = space.getitem(space.w_builtins, space.wrap(name))
    except OperationError:
        print "AttributeError: PyPy space %s builtins has no attribute '%s'" % (space, name)
        return [], cpy_attrs
    
    return found_missing(name, cpy_attrs, w_obj, space)


def print_report(names, space):

    for n in names:
        found, missing = check_for_attrs(n, space)
        print
        print "For the Builtin Function or Type: '%s'" % n
        print
        print 'Found Attributes: \t', found
        print
        print 'Missing Attributes: \t', missing
        print
        print '-------------------------'

if __name__ == '__main__':

    from pypy.tool import option
    from pypy.tool import test
    args = option.process_options(option.get_standard_options(),
                                  option.Options)


    # Create objspace...
    objspace = option.objspace()
    
    #names = dir(cpy_builtin)
    names = ['abs', 'xxx', 'unicode', 'enumerate', 'int']

    print_report(names, objspace)
