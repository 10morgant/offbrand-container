#!/bin/bash

cd collector

# fetch tags from the server using the images fetched
uv run fetch process http://0.0.0.0:5000 --downloaders 50 --skip-existing