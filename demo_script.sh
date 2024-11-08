#!/usr/bin/env bash

rm recording.cast
cmd="time eg \"update the README command examples to include one with the new --use-cwd flag, perhaps organizing some pictures or something (can read main.py and tools.py for details )\" --model gpt-4o -f --max-cost .15"

#read -r cmd

asciinema rec recording.cast -i 1  -c bash -c "echo '$cmd'; eval '$cmd'"
