#!/bin/bash

rm -rf logs/*.txt

romPath=~/Ausbildung/08_UNIBE_FS/bachelor/docs/roms
executable=gameboy_evaluation_target.py

python2.5 $executable $romPath/Megaman.gb         >> logs/megaman.txt 
python2.5 $executable $romPath/KirbysDreamLand.gb >> logs/kirbysDreamland.txt
python2.5 $executable $romPath/SuperMarioLand.gb  >> logs/superMario.txt
python2.5 $executable              			      >> logs/rom9.txt


python evaluation_test_parser.py