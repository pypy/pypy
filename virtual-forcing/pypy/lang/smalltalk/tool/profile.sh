python -m cProfile -o compile_method.txt `which py.test` -k compile_method ../test/test_miniimage.py
python infostats.py
