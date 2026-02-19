# User Guide

FinchBot provides a rich Command Line Interface (CLI) for interacting with the agent. This document details all available commands and interaction modes.

## 1. Startup & Basic Interaction

### Start FinchBot

```bash
uv run finchbot chat
```

### Specify Session

You can specify a session ID to continue a previous conversation or start a new one:

```bash
uv run finchbot chat --session-id "project-alpha"
```

If not specified, the system will automatically load the last active session.

### Interactive Mode

Once in the chat interface, you can type natural language to talk to the Agent.

- **Input**: Type text and press Enter.
- **Newline**: The CLI is currently single-line input. For long text, consider sending in segments or using file reading tools.
- **Exit**: Type `exit`, `quit`, `:q` or `q` to exit.

---

## 2. Slash Commands

In the chat interface, inputs starting with `/` are treated as special commands.

### `/history`

View history messages of the current session.

- **Function**: Displays all messages (User, AI, Tool calls) from the beginning of the session.
- **Usage**: Review context or check message indices (for rollback).

### `/rollback <index> [new_session_id]`

Time Travel: Rollback the conversation state to a specific message index.

- **Parameters**:
    - `<index>`: The target message index (view via `/history`).
    - `[new_session_id]` (Optional): If provided, creates a new branch session, keeping the original one intact. If not, overwrites the current session.
- **Examples**:
    - `/rollback 5`: Rollback to the state after message 5 (deletes all messages with index > 5).
    - `/rollback 5 branch-b`: Create a new session `branch-b` based on the state at message 5.

### `/back <n>`

Undo the last n messages.

- **Parameters**:
    - `<n>`: Number of messages to undo.
- **Examples**:
    - `/back 1`: Undo the last message (useful for correcting a typo).
    - `/back 2`: Undo the last turn of conversation (User query + AI response).

---

## 3. Session Manager

FinchBot provides a full-screen interactive session manager.

### Enter Manager

Use the `--manage` flag at startup:

```bash
uv run finchbot chat --manage
```

Or start without arguments when no history sessions exist.

### Controls

- **↑ / ↓**: Navigate sessions.
- **Enter**: Enter selected session.
- **r**: Rename selected session.
- **d**: Delete selected session.
- **n**: Create new session.
- **q**: Quit manager.

---

## 4. Global Options

The `finchbot` command supports the following global options:

- `--help`: Show help message.
- `--version`: Show version number.
- `--verbose` / `-v`: Enable verbose logging (debug mode).
- `--quiet` / `-q`: Quiet mode, output errors only.

**Example**:

```bash
# Start in debug mode to see detailed thought processes and network requests
uv run finchbot chat -v
```
