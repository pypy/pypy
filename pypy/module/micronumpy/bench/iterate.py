
def f():
    sum = 0
    a = numpy.zeros(1000000)
    for i in range(1000000):
        sum += a[i]
    return sum

f()
