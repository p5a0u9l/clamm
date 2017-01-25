#!/usr/bin/env zsh

prog="./action.py"

tester() {
    if $prog $1 > /dev/null; then echo $1: success; fi
}

tester "get_arrangement_set"
tester "verify_artists_set"
