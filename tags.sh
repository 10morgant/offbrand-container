#!/bin/bash

cd collector

# fetch tags from the server using the images fetched
uv run process --downloaders 50 --skip-existing