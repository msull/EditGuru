#!/usr/bin/env bash

#cmd="time eg \"update the README command examples to include one with the new --use-cwd flag, perhaps organizing some pictures or something (can read main.py and tools.py for details )\" --model gpt-4o -f --max-cost .15"
cmd="time eg \"setup a new directory called myapp and create a skeleton flask app inside with src/ and pyproject.toml\" -f"

asciinema rec recording.cast -i 1 --overwrite  -c bash -c "echo '$cmd'; eval '$cmd'"
