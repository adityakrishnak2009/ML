import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


class OllamaChat:
    def __init__(self):
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You are a friendly, helpful assistant running locally. Answer conversationally. "
                    "You cannot access or control the user's computer yourself. The separate PC "
                    "Automator handles only the explicit commands it recognizes."
                ),
            }
        ]

    def ask(self, message: str) -> str:
        self.messages.append({"role": "user", "content": message})
        payload = json.dumps(
            {"model": self.model, "messages": self.messages, "stream": False}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            self.messages.pop()
            detail = error.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"Ollama returned HTTP {error.code}: {detail or error.reason}"
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            self.messages.pop()
            raise RuntimeError(
                f"Could not connect to Ollama at {self.host}. "
                "Install Ollama, download a model, and make sure Ollama is running."
            ) from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            self.messages.pop()
            raise RuntimeError("Ollama returned an invalid response.") from error

        if not isinstance(result, dict) or not isinstance(result.get("message"), dict):
            self.messages.pop()
            raise RuntimeError("Ollama returned an invalid response.")

        reply = result.get("message", {}).get("content")
        if not isinstance(reply, str) or not reply.strip():
            self.messages.pop()
            raise RuntimeError("Ollama returned an empty chat response.")

        self.messages.append({"role": "assistant", "content": reply})
        self.messages = self.messages[:1] + self.messages[-12:]
        return reply.strip()


class PCAutomator:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Desktop"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_path(self, target: str) -> Path:
        target = target.strip().strip('"\'')
        if not target:
            raise ValueError("A file path is required.")

        if target.startswith("~"):
            target = str(Path.home()) + target[1:]

        path = Path(target)
        if not path.is_absolute():
            path = (self.base_dir / path).resolve()
        return path

    def _default_content_for(self, extension: str) -> str:
        templates = {
            ".py": "print(\"Hello from PC Automator!\")\n",
            ".txt": "This file was created by PC Automator.\n",
            ".md": "# New Document\n\nCreated by PC Automator.\n",
            ".json": '{\n  "createdBy": "PC Automator"\n}\n',
            ".html": "<!DOCTYPE html>\n<html>\n<head>\n  <meta charset=\"UTF-8\">\n  <title>New Page</title>\n</head>\n<body>\n  <h1>Hello</h1>\n</body>\n</html>\n",
            ".css": "body {\n  font-family: Arial, sans-serif;\n}\n",
            ".js": "console.log(\"Hello from PC Automator!\");\n",
            ".csv": "name,value\nexample,1\n",
            ".ps1": "Write-Host \"Hello from PC Automator!\"\n",
            ".bat": "@echo off\r\necho Hello from PC Automator!\r\n",
            ".yml": "name: example\n",
            ".yaml": "name: example\n",
        }
        return templates.get(extension.lower(), "")

    def create_file(self, name: str, content: str | None = None) -> str:
        path = self._normalize_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.is_dir():
            return f"The destination is a folder, not a file: {path}"

        if not path.exists():
            path.write_text(content or self._default_content_for(path.suffix), encoding="utf-8")
            self.open_file(path)
            return f"Created and opened: {path}"

        return f"File already exists: {path}"

    def create_folder(self, folder_name: str) -> str:
        path = self._normalize_path(folder_name)
        path.mkdir(parents=True, exist_ok=True)
        return f"Folder ready: {path}"

    def open_file(self, file_path_or_name: str | os.PathLike) -> str:
        path = self._normalize_path(str(file_path_or_name)) if isinstance(file_path_or_name, str) else Path(file_path_or_name)
        if not path.exists():
            return f"File does not exist: {path}"

        if sys.platform.startswith("win"):
            try:
                os.startfile(str(path))
            except Exception:
                subprocess.Popen(["cmd", "/c", "start", "", str(path)], shell=True)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

        return f"Opened: {path}"

    def open_app(self, app_name: str) -> str:
        app_name = app_name.strip()
        if not app_name:
            return "No app name provided."

        if sys.platform.startswith("win"):
            try:
                os.startfile(app_name)
                return f"Opened app: {app_name}"
            except Exception:
                pass

            try:
                subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=True)
                return f"Launched app: {app_name}"
            except Exception:
                return f"Could not launch app: {app_name}"

        commands = {
            "vscode": ["code"],
            "visual studio code": ["code"],
            "chrome": ["google-chrome"],
            "browser": ["xdg-open", "https://www.google.com"],
        }

        cmd = commands.get(app_name.lower())
        if cmd:
            subprocess.Popen(cmd)
            return f"Opened app: {app_name}"

        if os.system(f"command -v {shlex.quote(app_name)} >/dev/null 2>&1") == 0:
            subprocess.Popen([app_name])
            return f"Opened app: {app_name}"

        return f"I can open common apps like VS Code, Chrome, or a specific app command if it exists on this system."

    def open_url(self, url: str) -> str:
        clean_url = url.strip()
        if not re.match(r"^[a-zA-Z]+://", clean_url):
            clean_url = "https://" + clean_url
        webbrowser.open(clean_url)
        return f"Opened website: {clean_url}"

    def run_shell_command(self, command: str) -> str:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if stdout:
            return stdout
        if stderr:
            return stderr
        return "Command executed successfully."

    def list_files(self, path: str | None = None) -> str:
        target = self._normalize_path(path or ".") if path else Path.cwd()
        items = sorted([item.name for item in target.iterdir()]) if target.exists() else []
        return "\n".join(items) if items else "No items found."

    def is_local_command(self, instruction: str) -> bool:
        text = (instruction or "").strip()
        lowered = text.lower()
        return bool(
            lowered in {"help", "menu", "commands"}
            or re.search(r"\b(list|show)\s+(files|folder|directory)\b|\bfiles\s*(here|in\s+this\s+folder)?\b", lowered)
            or re.search(r"\bopen\s+(?:the\s+)?(?:file\s+)?[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+\b", text, re.I)
            or re.search(r"\b(?:create|make)\s+(?:a\s+|new\s+)?folder(?:\s+named|\s+called)?\s+", text, re.I)
            or re.search(r"\b(?:create|make)\s+(?:a\s+|new\s+)?(?:(?:python|text|html|css|javascript|js|json|markdown|md|csv|txt|ps1|bat|yml|yaml)\s+)?file(?:\s+(?:named|called))?\s+", text, re.I)
            or re.search(r"\b(?:run|execute)\s+(?:the\s+)?command\s+.+$", text, re.I)
            or re.search(r"\bopen\s+(?:the\s+)?website\s+.+$|\bopen\s+.+?\.(?:com|org|net|io|gov|edu|co|in)\b", text, re.I)
            or re.search(r"\bopen\s+(?:the\s+)?app\s+.+$", text, re.I)
        )

    def handle(self, instruction: str) -> str:
        text = (instruction or "").strip()
        if not text:
            return "Please give me a task."

        lowered = text.lower()

        if lowered in {"help", "menu", "commands"}:
            return (
                "You can say things like:\n"
                "- create python file named hello.py\n"
                "- create folder named scripts\n"
                "- open file hello.py\n"
                "- open website github.com\n"
                "- run command dir\n"
                "- list files\n"
                "- open app vscode"
            )

        if re.search(r"\b(list|show)\s+(files|folder|directory)\b|\bfiles\s*(here|in\s+this\s+folder)?\b", lowered):
            return self.list_files()

        match_create_folder = re.search(r"\b(?:create|make)\s+(?:a\s+|new\s+)?folder(?:\s+named|\s+called)?\s+[\"']?([A-Za-z0-9_.\- /\\]+)[\"']?", text, re.I)
        if match_create_folder:
            return self.create_folder(match_create_folder.group(1))

        match_create_file = re.search(
            r"\b(?:create|make)\s+(?:a\s+|new\s+)?(?:(python|text|html|css|javascript|js|json|markdown|md|csv|txt|ps1|bat|yml|yaml)\s+)?file(?:\s+(?:named|called))?\s+[\"']?([A-Za-z0-9_.\- /\\]+)[\"']?",
            text,
            re.I,
        )
        if match_create_file:
            ext = match_create_file.group(1)
            raw_name = match_create_file.group(2)
            filename = raw_name.strip()
            if ext:
                ext_map = {
                    "python": ".py",
                    "text": ".txt",
                    "html": ".html",
                    "css": ".css",
                    "javascript": ".js",
                    "js": ".js",
                    "json": ".json",
                    "markdown": ".md",
                    "md": ".md",
                    "csv": ".csv",
                    "txt": ".txt",
                    "ps1": ".ps1",
                    "bat": ".bat",
                    "yml": ".yml",
                    "yaml": ".yaml",
                }
                if not filename.lower().endswith(tuple(ext_map.values())):
                    filename = filename + ext_map.get(ext.lower(), "")
            if not re.search(r"\.[A-Za-z0-9]+$", filename):
                filename = filename + ".txt"
            return self.create_file(filename)

        match_run_command = re.search(r"\b(?:run|execute)\s+(?:the\s+)?command\s+(.+)$", text, re.I)
        if match_run_command:
            return self.run_shell_command(match_run_command.group(1).strip())

        match_open_url = re.search(r"\bopen\s+(?:the\s+)?website\s+(.+)$|\bopen\s+(.+?\.(?:com|org|net|io|gov|edu|co|in))\b", text, re.I)
        if match_open_url:
            url = match_open_url.group(1) or match_open_url.group(2)
            return self.open_url(url)

        match_open_app = re.search(r"\bopen\s+(?:the\s+)?app\s+(.+)$", text, re.I)
        if match_open_app:
            return self.open_app(match_open_app.group(1).strip())

        match_open_file = re.search(r"\bopen\s+(?:the\s+)?(?:file\s+)?([A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+)\b", text, re.I)
        if match_open_file:
            return self.open_file(match_open_file.group(1))

        return (
            "I can help with common local tasks. Try examples like:\n"
            "- create python file named hello.py\n"
            "- open file hello.py\n"
            "- create folder named scripts\n"
            "- open website github.com\n"
            "- run command dir\n"
            "- list files"
        )


def run_command_loop(automator):
    print("PC Automator is ready. Type 'help' for commands. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("\nCommand: ")
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

        if user_input.strip().lower() in {"exit", "quit", "bye"}:
            print("Goodbye.")
            break

        print(automator.handle(user_input))


def run_chat_loop(automator):
    chat = OllamaChat()
    print(
        f"PC Automator chat is ready (local model: {chat.model}). "
        "Type 'help' for computer commands or 'exit' to quit."
    )
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

        if user_input.lower() in {"exit", "quit", "bye"}:
            print("Goodbye.")
            break
        if not user_input:
            continue

        if automator.is_local_command(user_input):
            if re.match(r"^(?:create|make|open|run|execute)\b", user_input, re.I):
                confirmation = input(
                    "This will perform a computer action. Type 'yes' to continue: "
                )
                if confirmation.strip().lower() not in {"yes", "y"}:
                    print("Action cancelled.")
                    continue
            print(f"PC Automator: {automator.handle(user_input)}")
            continue

        try:
            print(f"Assistant: {chat.ask(user_input)}")
        except RuntimeError as error:
            print(f"Chat unavailable: {error}")
            print(
                f"To set it up, install Ollama and run: ollama run {chat.model}"
            )


def main():
    automator = PCAutomator()
    args = sys.argv[1:]
    if args and args[0] == "--command":
        if len(args) > 1:
            print(automator.handle(" ".join(args[1:])))
        else:
            run_command_loop(automator)
        return 0

    if args and args[0] == "--chat":
        run_chat_loop(automator)
        return 0

    if args:
        print(automator.handle(" ".join(args)))
        return 0

    run_chat_loop(automator)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
