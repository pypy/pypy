import py

chunks = 7

p = py.path.local(py.std.sys.argv[1])

data = [l.strip() for l in p.readlines()]

result = data[:2]
data = data[2:]

acc = 0
for i, line in enumerate(data):
    print line
    line = line.split(',')
    acc += int(line[1])
    if i % chunks == chunks - 1:
        line[1] = str(acc)
        result.append(", ".join(line))
        acc = 0

p.write("\n".join(result))
