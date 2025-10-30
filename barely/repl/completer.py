"""
FILE: barely/repl/completer.py
PURPOSE: Autocomplete logic for REPL commands and arguments
EXPORTS:
  - BarelyCompleter (Completer for command/arg completion)
  - create_completer() -> BarelyCompleter
DEPENDENCIES:
  - prompt_toolkit.completion (Completer, Completion)
  - typing (type hints)
  - barely.core.service (for dynamic project name completion)
NOTES:
  - Suggests command names when at start of line
  - Suggests project subcommands after "project" command
  - Suggests flags after commands (--json, --raw, --status, --project)
  - Suggests status values after --status flag
  - Suggests pull scopes after "pull" command
  - Suggests project names after "assign" command
  - Suggests project names and clear options ("none", "clear") after "use" command
  - Suggests scope values (today, week, backlog, archived, all) after "scope" command
  - Suggests task IDs for commands expecting IDs; suggests column names for mv
  - Case-insensitive matching
"""

from typing import Iterable
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class BarelyCompleter(Completer):
    """
    Custom completer for Barely REPL.

    Provides context-aware autocomplete:
    - Command names at start of input
    - Flags after command names
    - Status values after --status flag
    """

    # Available commands
    COMMANDS = [
        "add", "assign", "ls", "done", "rm", "edit", "desc", "show", "view",
        "mv", "today", "week", "backlog", "archive", "pull", "use", "scope",
        "project", "blitz", "help", "clear", "undo", "exit", "quit"
    ]

    # Project subcommands
    PROJECT_SUBCOMMANDS = ["add", "ls", "rm"]

    # Pull scopes (includes archived for reactivating tasks)
    PULL_SCOPES = ["backlog", "week", "today", "archived"]

    # Common flags for all commands (none in REPL - it's interactive, not for scripting)
    COMMON_FLAGS = []

    # Command-specific flags
    COMMAND_FLAGS = {
        "ls": ["--archived", "--project"],
        "add": [],  # Note: --project could be added here if we want project support in add
        "done": [],
        "rm": [],
        "edit": [],
        "mv": [],
        "today": [],
        "week": [],
        "backlog": [],
        "pull": [],  # pull uses positional args, not flags
    }

    # Status values for --status flag (deprecated, kept for backwards compatibility)
    STATUS_VALUES = []  # No longer used - scope-based instead

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """
        Generate completions based on current input.

        Args:
            document: Current document with cursor position
            complete_event: Event that triggered completion

        Yields:
            Completion objects for matching suggestions

        Logic:
            1. If at start or only whitespace -> suggest commands
            2. If command is "project" -> suggest subcommands
            3. If after command -> suggest flags or specific values
            4. If after --status flag -> suggest status values
            5. Otherwise -> no suggestions
        """
        # Get text before cursor and split into words
        text_before_cursor = document.text_before_cursor
        words = text_before_cursor.split()

        # Case 1: Empty input or just whitespace -> suggest commands
        if not words or (not text_before_cursor.endswith(" ") and len(words) == 1):
            word = words[0] if words else ""
            yield from self._complete_commands(word)
            return

        # Case 2: "project" command -> suggest subcommands
        command = words[0].lower()
        if command == "project":
            # After "project " suggest subcommands
            if len(words) == 1 and text_before_cursor.endswith(" "):
                yield from self._complete_project_subcommands("")
                return
            # Typing a subcommand
            elif len(words) == 2 and not text_before_cursor.endswith(" "):
                yield from self._complete_project_subcommands(words[1])
                return

        # Case 2b: "pull" command -> suggest scopes after task ID(s)
        if command == "pull":
            # After "pull <task_id(s)> " suggest scopes
            if len(words) >= 2 and text_before_cursor.endswith(" "):
                yield from self._complete_pull_scopes("")
                return
            # Typing a scope (third word or later)
            elif len(words) >= 3 and not text_before_cursor.endswith(" "):
                yield from self._complete_pull_scopes(words[-1])
                return

        # Case 2bb: Commands expecting a task ID as first arg -> suggest IDs
        id_first_cmds = {"done", "rm", "edit", "show", "view", "mv", "assign"}
        if command in id_first_cmds:
            # Right after command and a space -> suggest IDs
            if len(words) == 1 and text_before_cursor.endswith(" "):
                yield from self._complete_task_ids("")
                return
            # Typing the first argument (task id)
            if len(words) == 2 and not text_before_cursor.endswith(" "):
                yield from self._complete_task_ids(words[1])
                return

        # Case 2c: "assign" command -> suggest project names after task ID(s)
        if command == "assign":
            # After "assign <task_id(s)> " suggest project names
            if len(words) >= 2 and text_before_cursor.endswith(" "):
                yield from self._complete_project_names("")
                return
            # Typing a project name (third word or later)
            elif len(words) >= 3 and not text_before_cursor.endswith(" "):
                yield from self._complete_project_names(words[-1])
                return

        # Case 2d: "mv" second arg -> suggest column names
        if command == "mv":
            # After "mv <id> " suggest column names
            if len(words) >= 2 and text_before_cursor.endswith(" "):
                yield from self._complete_column_names("")
                return
            # Typing a column name
            if len(words) >= 3 and not text_before_cursor.endswith(" "):
                yield from self._complete_column_names(words[-1])
                return

        # Case 2d: "use" command -> suggest project names and clear options
        if command == "use":
            # After "use " suggest project names and clear options
            if len(words) == 1 and text_before_cursor.endswith(" "):
                yield from self._complete_project_names("", include_clear_options=True)
                return
            # Typing a project name or clear option
            elif len(words) == 2 and not text_before_cursor.endswith(" "):
                yield from self._complete_project_names(words[1], include_clear_options=True)
                return

        # Case 2e: "scope" command -> suggest scope values
        if command == "scope":
            # After "scope " suggest scope values
            if len(words) == 1 and text_before_cursor.endswith(" "):
                yield from self._complete_scope_values("")
                return
            # Typing a scope value
            elif len(words) == 2 and not text_before_cursor.endswith(" "):
                yield from self._complete_scope_values(words[1])
                return

        # Case 3: After a command -> check for flag values or suggest flags
        last_word = words[-1] if words else ""

        # Check if we're typing after --status flag
        if len(words) >= 2 and words[-2] == "--status":
            # Suggest status values
            yield from self._complete_status_values(last_word)
            return

        # If last word is incomplete and not a flag, don't suggest anything
        # (could be task title or ID being typed)
        if not last_word.startswith("--") and not text_before_cursor.endswith(" "):
            return

        # Suggest flags for this command
        yield from self._complete_flags(command, last_word)

    def _complete_commands(self, word: str) -> Iterable[Completion]:
        """
        Complete command names.

        Args:
            word: Partial command being typed

        Yields:
            Completion objects for matching commands
        """
        word_lower = word.lower()
        for command in self.COMMANDS:
            if command.startswith(word_lower):
                # Calculate how many chars to remove (the partial word)
                yield Completion(
                    command,
                    start_position=-len(word),
                    display=command,
                    display_meta=self._get_command_description(command),
                )

    def _complete_flags(self, command: str, word: str) -> Iterable[Completion]:
        """
        Complete flag names for a given command.

        Args:
            command: The command being executed
            word: Partial flag being typed

        Yields:
            Completion objects for matching flags
        """
        # Get command-specific flags
        command_flags = self.COMMAND_FLAGS.get(command, [])
        all_flags = self.COMMON_FLAGS + command_flags

        word_lower = word.lower()
        for flag in all_flags:
            if flag.startswith(word_lower):
                yield Completion(
                    flag,
                    start_position=-len(word),
                    display=flag,
                    display_meta=self._get_flag_description(flag),
                )

    def _complete_status_values(self, word: str) -> Iterable[Completion]:
        """
        Complete status values for --status flag.

        Args:
            word: Partial status value being typed

        Yields:
            Completion objects for matching status values
        """
        word_lower = word.lower()
        for status in self.STATUS_VALUES:
            if status.startswith(word_lower):
                yield Completion(
                    status,
                    start_position=-len(word),
                    display=status,
                )

    def _complete_project_subcommands(self, word: str) -> Iterable[Completion]:
        """
        Complete project subcommands.

        Args:
            word: Partial subcommand being typed

        Yields:
            Completion objects for matching subcommands
        """
        word_lower = word.lower()
        for subcommand in self.PROJECT_SUBCOMMANDS:
            if subcommand.startswith(word_lower):
                yield Completion(
                    subcommand,
                    start_position=-len(word),
                    display=subcommand,
                    display_meta=self._get_project_subcommand_description(subcommand),
                )

    def _complete_pull_scopes(self, word: str) -> Iterable[Completion]:
        """
        Complete pull command scopes.

        Args:
            word: Partial scope being typed

        Yields:
            Completion objects for matching scopes
        """
        word_lower = word.lower()
        for scope in self.PULL_SCOPES:
            if scope.startswith(word_lower):
                yield Completion(
                    scope,
                    start_position=-len(word),
                    display=scope,
                    display_meta=self._get_pull_scope_description(scope),
                )

    def _complete_scope_values(self, word: str) -> Iterable[Completion]:
        """
        Complete scope command values.

        Args:
            word: Partial scope value being typed

        Yields:
            Completion objects for matching scope values

        Notes:
            - Includes scope values: today, week, backlog, archived
            - Also includes clear options: all, none, clear
        """
        word_lower = word.lower()
        
        # Scope values (same as pull scopes)
        for scope in self.PULL_SCOPES:
            if scope.startswith(word_lower):
                yield Completion(
                    scope,
                    start_position=-len(word),
                    display=scope,
                    display_meta=self._get_pull_scope_description(scope),
                )
        
        # Clear options
        clear_options = [
            ("all", "Clear scope filter (show all scopes)"),
            ("none", "Clear scope filter (show all scopes)"),
            ("clear", "Clear scope filter (show all scopes)"),
        ]
        for option, description in clear_options:
            if option.startswith(word_lower):
                yield Completion(
                    option,
                    start_position=-len(word),
                    display=option,
                    display_meta=description,
                )

    def _complete_project_names(self, word: str, include_clear_options: bool = False) -> Iterable[Completion]:
        """
        Complete project names for assign/use commands.

        Args:
            word: Partial project name being typed
            include_clear_options: If True, also suggest "none", "clear" options (for use command)

        Yields:
            Completion objects for matching project names

        Notes:
            - Automatically quotes project names with spaces
            - Handles partial matches even when user is typing inside quotes
        """
        # Import here to avoid circular dependency
        from ..core import service

        # Strip quotes from word if user is already typing them
        word_stripped = word.strip('"').strip("'")
        word_lower = word_stripped.lower()

        # Add special clear options for 'use' command
        if include_clear_options:
            clear_options = [
                ("none", "Clear project context"),
                ("clear", "Clear project context"),
            ]
            for option, description in clear_options:
                if option.startswith(word_lower):
                    yield Completion(
                        option,
                        start_position=-len(word),
                        display=option,
                        display_meta=description,
                    )

        # Add actual project names
        try:
            projects = service.list_projects()
            for project in projects:
                if project.name.lower().startswith(word_lower):
                    # Quote project names that contain spaces
                    if ' ' in project.name:
                        completion_text = f'"{project.name}"'
                        display_text = f'"{project.name}"'
                    else:
                        completion_text = project.name
                        display_text = project.name

                    yield Completion(
                        completion_text,
                        start_position=-len(word),
                        display=display_text,
                        display_meta=f"Project #{project.id}",
                    )
        except Exception:
            # Silently fail if we can't fetch projects
            pass

    @staticmethod
    def _get_command_description(command: str) -> str:
        """Get description for a command (shown in autocomplete menu)."""
        descriptions = {
            "add": "Create a new task",
            "assign": "Assign task to project",
            "ls": "List tasks",
            "done": "Mark task as complete",
            "rm": "Delete task",
            "edit": "Update task title",
            "view": "View full task details",
            "mv": "Move task to column",
            "today": "List today's tasks",
            "week": "List this week's tasks",
            "backlog": "List backlog tasks",
            "archive": "View archived/completed tasks",
            "pull": "Pull tasks into scope",
            "use": "Set current working project",
            "scope": "Set current scope filter",
            "project": "Manage projects",
            "help": "Show available commands",
            "clear": "Clear the screen",
            "undo": "Undo last operation",
            "exit": "Exit REPL",
            "quit": "Exit REPL",
        }
        return descriptions.get(command, "")

    @staticmethod
    def _get_flag_description(flag: str) -> str:
        """Get description for a flag (shown in autocomplete menu)."""
        descriptions = {
            "--json": "Output as JSON",
            "--raw": "Plain text output",
            "--status": "Filter by status",
            "--project": "Filter by project",
        }
        return descriptions.get(flag, "")

    @staticmethod
    def _get_project_subcommand_description(subcommand: str) -> str:
        """Get description for a project subcommand (shown in autocomplete menu)."""
        descriptions = {
            "add": "Create a new project",
            "ls": "List all projects",
            "rm": "Delete a project",
        }
        return descriptions.get(subcommand, "")

    @staticmethod
    def _get_pull_scope_description(scope: str) -> str:
        """Get description for a pull scope (shown in autocomplete menu)."""
        descriptions = {
            "backlog": "Unscheduled tasks (the inbox)",
            "week": "This week's commitment",
            "today": "Today's focus list",
            "archived": "Archived/completed tasks",
        }
        return descriptions.get(scope, "")

    def _complete_task_ids(self, word: str) -> Iterable[Completion]:
        """
        Complete task IDs with helpful labels (title + scope).
        """
        from ..core import service

        word_lower = word.lower()
        try:
            tasks = service.list_tasks(include_done=True)
        except Exception:
            tasks = []

        for t in tasks[:200]:  # cap for responsiveness
            id_str = str(t.id)
            if id_str.startswith(word_lower):
                scope = t.scope or ""
                title = (t.title or "").strip()
                display_title = title if len(title) <= 40 else title[:37] + "..."
                meta = f"{display_title} [{scope}]"
                yield Completion(
                    id_str,
                    start_position=-len(word),
                    display=id_str,
                    display_meta=meta,
                )

    def _complete_column_names(self, word: str) -> Iterable[Completion]:
        """Complete column names for mv command."""
        from ..core import service

        word_lower = word.lower()
        try:
            columns = service.list_columns()
        except Exception:
            columns = []

        for col in columns:
            name = col.name
            if name.lower().startswith(word_lower):
                yield Completion(
                    name,
                    start_position=-len(word),
                    display=name,
                    display_meta=f"Column #{col.id}",
                )


def create_completer() -> BarelyCompleter:
    """
    Create and return a BarelyCompleter instance.

    Returns:
        BarelyCompleter configured for Barely commands

    Usage:
        completer = create_completer()
        session = PromptSession(completer=completer)
    """
    return BarelyCompleter()
