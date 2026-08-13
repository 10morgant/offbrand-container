#!/bin/bash

cd collector

# fetch list of names from server
uv run fetch http://0.0.0.0:5000

# add list of names from file to database
uv run names http://0.0.0.0:5000