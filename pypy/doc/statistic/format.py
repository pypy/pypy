import py
import datetime
import dateutil
from dateutil import parser

import pylab
import matplotlib

def get_data(p):
    data = p.readlines()
    title = data[0].strip()
    axis = data[1].strip().split(',')
    data = [convert_data(t) for t in zip(*[l.strip().split(',') for l in data[2:]])]
    return title, axis, data

def convert_data(row):
    if not row:
        return []
    first = row[0]
    try:
        int(first)
        return [int(elt) for elt in row]
    except ValueError:
        pass
    try:
        float(first)
        return [float(elt) for elt in row]
    except ValueError:
        pass
    parsedate(first)
    return [parsedate(elt) for elt in row]

def parsedate(s):
    if len(s) <= 7:
        year, month = s.split("-")
        result = datetime.datetime(int(year), int(month), 1)
    else:
        result = parser.parse(s)
    return pylab.date2num(result)

def date2str(i, dates):
    l = len(dates)
    if i == 0 or i == l-1 or i == int(l/2):
        d = dates[i]
        return str(pylab.num2date(d))[:7]
    else:
        return ""

colors = "brg"

def txt2png(p):
    print p
    title, axis, data = get_data(p)
    dates = data[0]
    args = []
    ax = pylab.subplot(111)
    for i, d in enumerate(data[1:]):
        args = [dates, d, colors[i]]
        pylab.plot_date(*args)
    pylab.legend(axis[1:], "upper left")
    loc, labels = pylab.xticks()
    pylab.xlabel(axis[0])
    pylab.ylabel(axis[1])
    ticklabels = ax.get_xticklabels()
    pylab.setp(ticklabels, 'rotation', 45, size=9)
    ax.autoscale_view()
    ax.grid(True)
    pylab.title(title)
    pylab.savefig(p.purebasename + ".png")
    pylab.savefig(p.purebasename + ".eps")
 
def main():
    for p in py.path.local().listdir("*.txt"):
        txt2png(p)

if __name__ == '__main__':
    if py.std.sys.argv[1] == "--all":
        for p in py.path.local().listdir():
            if p.ext != ".txt":
                continue
            py.std.os.system("python %s %s" % (py.std.sys.argv[0], p.basename))
    else:
        txt2png(py.path.local(py.std.sys.argv[1]))
