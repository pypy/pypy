from pypy.translator.cli.carbonpython import export

@export(int, int)
def sum(a, b):
    return a+b
