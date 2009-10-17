
import autopath
import urllib, urllib2
import subprocess
import sys
import py

BASE = "http://pypybench.appspot.com/upload"

def upload_results(stderr, url=BASE):
    data = urllib.urlencode({'content' : stderr})
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    response.read()

def run_richards(executable='python'):
    richards = str(py.magic.autopath().dirpath().dirpath().join('goal').join('richards.py'))
    pipe = subprocess.Popen([executable, richards], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    return pipe.communicate()

def main(executable):
    stdout, stderr = run_richards(executable)
    upload_results(stderr)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        executable = sys.argv[1]
    else:
        executable = sys.executable
    main(executable)
