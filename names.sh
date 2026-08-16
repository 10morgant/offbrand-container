#!/bin/bash

cd collector

# fetch list of names from server
uv run fetch 

# add list of names from file to database
uv run names 