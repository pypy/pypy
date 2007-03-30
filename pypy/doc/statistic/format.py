import py
import datetime
import dateutil
from dateutil import parser

import pylab
import matplotlib

greyscale = False

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
    if first[0] == '"':
        return [elt[1:-1] for elt in row]
    return [parsedate(elt) for elt in row]

def parsedate(s):
    if len(s) <= 7:
        year, month = s.split("-")
        result = datetime.datetime(int(year), int(month), 15)
    else:
        result = parser.parse(s)
    return pylab.date2num(result)

if greyscale:
    colors = ["k", "k--", "k."]
else:
    colors = "brg"

def csv2png(p):
    print p
    title, axis, data = get_data(p)
    dates = data[0]

    release_title, release_axis, release_data = get_data( py.path.local("release_dates.dat") )
    release_dates, release_names = release_data
 
    sprint_title, sprint_axis, sprint_data = get_data( py.path.local("sprint_dates.dat") )
    sprint_locations, sprint_begin_dates, sprint_end_dates = sprint_data
 
    ax = pylab.subplot(111)
    for i, d in enumerate(data[1:]):
        args = [dates, d, colors[i]]
        pylab.plot_date(linewidth=0.8, *args)

    ymax = max(pylab.yticks()[0]) #just below the legend
    for i, release_date in enumerate(release_dates):
        release_name = release_names[i]
        if greyscale:
            color = 0.3
        else:
            color = "g"
        pylab.axvline(release_date, linewidth=0.8, color=color, alpha=0.5)
        ax.text(release_date, ymax * 0.4, release_name,
                fontsize=10,
                horizontalalignment='right',
                verticalalignment='top',
                rotation='vertical')
    for i, location in enumerate(sprint_locations):
        begin = sprint_begin_dates[i]
        end   = sprint_end_dates[i]
        if float(begin) >= float(min(dates[0],dates[-1])):
            if greyscale:
                color = 0.8
            else:
                color = "y"
            pylab.axvspan(begin, end, linewidth=0, facecolor=color, alpha=0.5)
            ax.text(begin, ymax * 0.85, location,
                    fontsize=10,
                    horizontalalignment='right',
                    verticalalignment='top',
                    rotation='vertical')
    pylab.legend(axis[1:], "upper left")
    pylab.ylabel(axis[0])
    pylab.xlabel("")
    ticklabels = ax.get_xticklabels()
    pylab.setp(ticklabels, 'rotation', 45, size=9)
#    ax.autoscale_view()
    ax.grid(True)
    pylab.title(title)

    pylab.savefig(p.purebasename + ".png")
    pylab.savefig(p.purebasename + ".eps")
    py.process.cmdexec("epstopdf %s" % (p.purebasename + ".eps", ))
 
if __name__ == '__main__':
    args = py.std.sys.argv
    if len(args) == 1:
        print "usage: %s <filenames> <--all>" % args[0]
        py.std.sys.exit()
    for arg in args[1:]:
        if arg == "--all":
            for p in py.path.local().listdir("*.csv"):
                py.std.os.system("python %s %s" % (args[0], p.basename))
        else:
            csv2png(py.path.local(arg))
