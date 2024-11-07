# Edit Guru

**Latest Version:** 0.2.0

## Installation

You can install this CLI Tool using pipx:

```bash
pipx install git+https://github.com/msull/EditGuru.git
```

## Additional Information

### Environment Variable Setup

Before using this tool, please ensure that you have set your `OPENAI_API_KEY` environment variable. You can do this by
executing the following command in your terminal (for Unix-based systems):

```bash
export OPENAI_API_KEY='your_api_key_here'
```

For Windows, use:

```bash
set OPENAI_API_KEY='your_api_key_here'
```

Replace `'your_api_key_here'` with your actual OpenAI API key.

## Usage

To use the Edit Guru CLI tool, invoke it in your terminal as follows:

```bash
eg <task> [options]
```

### Options

- `--approve`: Pre-approve the generated plan and execute it automatically.
- `--approve-tools`: Pre-approve all tool usage.
- `-f`: Shortcut for `--approve` and `--approve-tools`.

### Example Command

```bash
eg "your task here" --approve
```

## Features

- **Task Automation**: Generate plans for tasks and execute them efficiently.
- **User Interaction**: Engage with the AI agent to track task completion and receive prompt responses.
- **Usage Statistics**: View completion statistics and costs after executing tasks.

## License

This project is licensed under the MIT License.
