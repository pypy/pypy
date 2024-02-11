import os
import subprocess
import sys
import sysconfig

def test_venv_of_venv(tmpdir):
    exe = os.path.split(sys.executable)[-1]
    subprocess.run([sys.executable, '-mvenv', str(tmpdir / 'venv1')])
    # 'bin' or 'Script'
    path = os.path.split(sysconfig.get_path('scripts'))[-1]
    subprocess.run([str(tmpdir / 'venv1' / path / exe),
                    '-mvenv', str(tmpdir / 'venv2')])


def test_multiprocessing(tmpdir):
    # issue 4876
    subprocess.run([sys.executable, '-mvenv', str(tmpdir / 'venv')])
    # 'bin' or 'Script'
    path = os.path.split(sysconfig.get_path('scripts'))[-1]
    exe = str(tmpdir / 'venv' / path / os.path.split(sys.executable)[-1])
    result = subprocess.run([exe, '-c',
                             'from multiprocessing import Pool; ' +
                             'print(Pool(1).apply_async(eval, ("__import__(\'sys\').executable",)).get(3))'],
                            capture_output=True)
    result.check_returncode()
    assert result.stdout.strip() == exe.encode()
