#!/usr/bin/env bash

rm recording.cast
cmd="eg \"update the readme with documentation and an example about the new --use-cwd flag when it is provided the tool works from the cwd and can be used outside of a git repo; without it the tool automatically works from the git repo where the tool is executed in, and can only see and interact with files added to the git repo (can read main.py and tools.py for more info )\" --plan-model anthropic.claude-3-5-sonnet-20241022-v2:0 -f"

#read -r cmd

asciinema rec recording.cast -i 1  -c bash -c "echo '$cmd'; eval '$cmd'"
