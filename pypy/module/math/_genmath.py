# ONESHOT SCRIPT (probably can go away soon)
# to generate the mixed module 'math' (see same directory) 
import py
import math
import re
import sys
rex_arg = re.compile(".*\((.*)\).*")

if __name__ == '__main__': 
    print py.code.Source("""
        import math 
        from pypy.interpreter.gateway import ObjSpace

    """)
    names = []
    for name, func in math.__dict__.items(): 
        if not callable(func): 
            continue
        sig = func.__doc__.split('\n')[0].strip()
        sig = sig.split('->')[0].strip()
        m = rex_arg.match(sig) 
        assert m
        args = m.group(1)
        args = ", ".join(args.split(','))
        sig = sig.replace('(', '(space,')
        sig = ", ".join(sig.split(','))
        argc = len(args.split(','))
        unwrap_spec = ['ObjSpace']
        unwrap_spec += ['float'] * argc 
        unwrap_spec = ", ".join(unwrap_spec)
        doc = func.__doc__.replace('\n', '\n       ')
        
        print py.code.Source('''
            def %(sig)s: 
                """%(doc)s
                """
                return space.wrap(math.%(name)s(%(args)s))
            %(name)s.unwrap_spec = [%(unwrap_spec)s]
        ''' % locals())
        names.append(name) 

    print >>sys.stderr, py.code.Source("""
        # Package initialisation
        from pypy.interpreter.mixedmodule import MixedModule

        class Module(MixedModule):
            appleveldefs = {
            }
            interpleveldefs = {
    """)
        
    for name in names: 
        space = " " * (15-len(name))
        print >>sys.stderr, (
            "       %(name)r%(space)s: 'interp_math.%(name)s'," % locals())
    print >>sys.stderr, py.code.Source("""
        }
    """) 
            
        
        
        
