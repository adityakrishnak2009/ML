# ML — Local AI PC Assistant

A small Python desktop assistant that combines conversational AI with a handful of explicit PC automation commands. Chat is powered by [Ollama](https://ollama.com/) and a model running locally on your computer, so the app does not require a paid AI API key.

> **Project scope:** This is a learning project and an extensible starter—not a universal computer-control agent. The chat model answers questions; it does not independently operate the computer.

## Features

- Chat locally with an Ollama model and retain a short conversation history for the current run.
- Create files and folders in the user's Desktop directory.
- Open files in the operating system's default application.
- Open websites and launch apps.
- Run a command when requested through the supported command syntax.
- Ask for confirmation before supported create, open, and run actions.

## Requirements

- Windows, macOS, or Linux
- Python 3.10 or later
- [Ollama](https://ollama.com/) installed and running for AI chat
- A model downloaded in Ollama; the default is `qwen2.5:3b`

The model download requires an internet connection and disk space. After download, inference runs locally; speed and memory use depend on the selected model and your hardware.

## Setup

Download a model using Ollama:

```shell
ollama pull qwen2.5:3b
```

From the project directory, start the assistant:

```shell
python pc_automator.py
```

On Windows, you can also double-click `run_pc_automator.bat`.

To use the command-only interface:

```shell
python pc_automator.py --command
```

To choose another model that you have already downloaded, set `OLLAMA_MODEL` before starting the assistant:

**PowerShell**

```powershell
$env:OLLAMA_MODEL = "qwen2.5:3b"
python pc_automator.py
```

**macOS/Linux**

```shell
OLLAMA_MODEL=qwen2.5:3b python pc_automator.py
```

The default Ollama address is `http://localhost:11434`; override it with the `OLLAMA_HOST` environment variable if your local Ollama server uses another address.

## Examples

Ask a general question:

```text
What is the difference between a Python list and a tuple?
```

Use one of the supported PC commands:

```text
create python file named hello.py
create folder named scripts
open file hello.py
open website github.com
open app vscode
run command dir
list files
```

The assistant asks for confirmation before supported create, open, and run actions. Type `yes` to continue or anything else to cancel. Type `exit` to leave the chat.

## Privacy and safety

- Chat requests go to the local Ollama server; this app does not send them to a hosted AI API.
- The model itself is downloaded separately through Ollama.
- Supported file creation and relative file paths use the current user's Desktop as the base directory.
- Shell commands can have significant effects on your computer. Only run commands you understand and trust.

## Current limitations

- PC actions are limited to commands recognized by the application; natural-language chat does not grant the model direct computer access.
- The available commands use simple text matching and may not understand every phrasing.
- App launch behavior depends on the operating system and installed applications.
- This project does not currently provide voice input, a graphical interface, or broad autonomous desktop control.

## Development

The project uses only the Python standard library. Run a syntax check with:

```shell
python -m py_compile pc_automator.py
```
