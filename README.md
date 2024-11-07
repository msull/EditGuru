# Edit Guru

**Latest Version:** 0.4.0

Edit Guru is a CLI tool powered by Large Language Models (LLMs) that enables intelligent file manipulation and editing
through natural language commands. It acts as an AI-powered file system operator that can understand and execute complex
file operations.

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

Before using Edit Guru, set up your OpenAI API key in your environment:

**Unix/Linux/MacOS:**

```bash
export OPENAI_API_KEY='your_api_key_here'
```

**Windows:**

```bash
set OPENAI_API_KEY='your_api_key_here'
```

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

### Example Commands

```bash
# Interactive mode with approval steps
eg "rename all python files to have a _v2 suffix"

# Automatic execution with pre-approval
eg "update version numbers in all configuration files" -f
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
