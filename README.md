# Edit Guru

**Latest Version:** 0.9.1


> [!WARNING]  
> ⚠️ Warning: Experimental Software Ahead! ⚠️
> This is experimental software that allows AI to modify files on your computer if you choose to use it.
> Do so at your own risk.
>
> This is a small piece of software that leverages AI to modify files on your disk.
> Please be aware that this software is highly experimental and may not function as intended.
> Use it at your own risk. We strongly recommend backing up your data before proceeding,
> as unintended modifications or data loss may occur.
> The creators of this software are not responsible for any damage or loss resulting from its use.
> Proceed with caution and discretion.

Edit Guru is a CLI tool powered by Large Language Models (LLMs) that enables intelligent file manipulation and editing
through natural language commands. It acts as an AI-powered file system operator that can understand and execute complex
file operations.

Example of setting up App scaffolding for a flask repo:

[![asciicast](https://asciinema.org/a/8gA1IqODn57ytDRpIwsbjVvWX.svg)](https://asciinema.org/a/8gA1IqODn57ytDRpIwsbjVvWX?speed=1.5)

(source it generated is in this repo at `misc/myapp`)

Example usage by generating the README for this repo:

[![asciicast](https://asciinema.org/a/VofKYWuifGLijwhQTfr5AH7N1.svg)](https://asciinema.org/a/VofKYWuifGLijwhQTfr5AH7N1?t=5&speed=1.5)

## Key Features

- **Natural Language Task Processing**: Describe your file operations in plain English
- **Intelligent Planning**: Automatically generates and executes plans for complex file operations
- **File System Operations**:
    - Text replacement across multiple files
    - File creation, editing, and deletion
    - Directory management
    - File moving and copying
    - Content search and manipulation
- **Safe Operation**: Built-in safeguards to prevent operations outside repository boundaries
- **Interactive Mode**: Review and approve operations before execution

## Installation

Install Edit Guru using pipx:

```bash
pipx install git+https://github.com/msull/EditGuru.git
```

## Prerequisites

### OpenAI API Key

Before using Edit Guru, set up your OpenAI API key in your environment.

**Unix/Linux/MacOS:**

```bash
export EDITGURU_OPENAI_API_KEY='your_api_key_here'
```

**Windows:**

```bash
set EDITGURU_OPENAI_API_KEY='your_api_key_here'

```

## All Environment Variables

The following environment variables can be used to control the behavior of EditGuru:
- `EDITGURU_OPENAI_API_KEY`: (Required)Your OpenAI API key for accessing the AI functionalities.
- `EDITGURU_ENABLE_BEDROCK`: (Optional) Set this variable to enable the use of additional models from AWS Bedrock for
  the `--plan-model` and `--model` options during tool execution; must have already configured AWS Credentials with
  access to the desired Bedrock models.

## Usage

Invoke Edit Guru using the `eg` command followed by your task description:

```bash
eg "your task description" [options]
```

### Command Options

- `--approve`: Automatically approve the generated plan and execute it
- `--approve-tools`: Pre-approve all tool usage during execution
- `-f`: Shortcut for both `--approve` and `--approve-tools`
- `--plan-model`: Specify a different model for plan generation
- `--model`: Specify the model for task execution (default: gpt-4o-mini)
- `--use-cwd`: Use the current working directory for file listing and operations instead of using the git repo the
  command is executed from

### Example Commands

```bash
# Configuration Management: Update database settings across environments
eg "update the database connection strings in all config/*.json files to use the new hostname db-prod-v2.example.com, but only in files that don't contain 'test' in their name" --approve

# Project Setup: Initialize new feature structure with boilerplate
eg "create a new feature module named 'user_authentication' with standard files: __init__.py, models.py, views.py, and tests/test_*.py files. Add basic boilerplate code in each" -f

# File Listing: Use current directory for operations
eg "please create subdirs and organize the files in this folder" --use-cwd
```

## Features in Detail

### File Operations

- **Text Replacement**: Search and replace text across multiple files
- **File Management**: Create, read, edit, and delete files
- **Directory Operations**: Create and manage directory structures
- **Content Manipulation**: Insert, modify, or remove content at specific locations
- **File Organization**: Move or copy files while maintaining repository structure

### Safety Features

- Repository boundary enforcement
- Operation preview and approval system
- Safe tool execution modes
- Error handling and validation

## License

This project is licensed under the MIT License.
