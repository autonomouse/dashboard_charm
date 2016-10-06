#!/bin/bash

#install any deps:
dpkg -l libffi-dev || sudo apt-get install libffi-dev

pip3 wheel -r wheels.txt
