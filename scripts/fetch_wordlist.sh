#!/usr/bin/env sh
# LDNOOBW English list: the naive banned-word baseline.
set -e
mkdir -p data/wordlists
curl -sSL "https://raw.githubusercontent.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/master/en" -o data/wordlists/en.txt
echo "$(wc -l < data/wordlists/en.txt) words -> data/wordlists/en.txt"
