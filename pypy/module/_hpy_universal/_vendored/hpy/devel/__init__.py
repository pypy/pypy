from pathlib import Path

BASE_DIR = Path(__file__).parent

def get_base_dir():
    return BASE_DIR

def get_include():
    return BASE_DIR.joinpath('include')

def get_sources():
    res = [str(x) for x in BASE_DIR.joinpath('src', 'runtime').glob('*.c')]
    return res
