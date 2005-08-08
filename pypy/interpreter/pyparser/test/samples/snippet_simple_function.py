def f(a, b=1, *args, **kwargs):
    if args:
        a += len(args)
    if kwargs:
        a += len(kwargs)
    return a*b
