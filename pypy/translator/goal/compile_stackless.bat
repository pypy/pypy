python -c "import time; print time.ctime(), 'compile start'" >> compile.log
translate_pypy.py --batch --stackless
python -c "import time; print time.ctime(), 'compile stop'" >> compile.log
