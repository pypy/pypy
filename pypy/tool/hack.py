import autopath

import new, sys

if sys.version_info > (2, 2):

    def func_with_new_name(func, newname):
        return new.function(func.func_code, func.func_globals,
                            newname, func.func_defaults,
                            func.func_closure)

else:

    def func_with_new_name(func, newname):
        return func

if __name__ == '__main__':
    def f(): pass
    g = func_with_new_name(f, 'g')
    print g.__name__
