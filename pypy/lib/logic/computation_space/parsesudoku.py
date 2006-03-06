import sys

file = open(sys.argv[1])
c = []
row = 1
for line in file.readlines():
    for col in range(1,10):
        if line[col-1] != ' ':
            c.append(('v%d%d' % (col, row), int(line[col-1])))
print c
    
