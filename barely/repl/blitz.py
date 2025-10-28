"""
FILE: barely/repl/blitz.py
PURPOSE: Focused task-completion mode with live audio waveform visualizer
EXPORTS:
  - run_blitz_mode() -> None
DEPENDENCIES:
  - core.service (list_today, complete_task)
  - rich (Console, Layout, Panel, Text, Live)
  - numpy (audio processing)
  - pyaudiowpatch (audio capture)
  - keyboard input handling
NOTES:
  - Displays tasks from 'today' scope one at a time
  - Live audio waveform visualization
  - Shows upcoming tasks in list below current task
  - Keyboard controls: d=done, s=skip, q=quit, ?=details
  - Returns to REPL when complete or user quits
"""

import numpy as np
import pyaudiowpatch as pyaudio
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
import time
import sys
import msvcrt  # For Windows keyboard input
import threading

from ..core import service
from ..core.models import Task
from .style import celebrate_bulk


# Audio configuration
SAMPLE_RATE = 44100
CHUNK = 2048
WAVEFORM_WIDTH = 76
UPDATE_FPS = 30
AMPLITUDE_SCALE = 0.8
NUM_ROWS = 5

# Sub-pixel character set for waveform
SUBPIXEL_CHARS = ['‾', '¯', '˗', '-', '─', '-', 'ˍ', '_', '‗']

# Audio state
audio_stream = None
audio_device = None
audio_ready = False


def render_waveform(audio_data, width=WAVEFORM_WIDTH, height=NUM_ROWS):
    """
    Render waveform with sub-pixel resolution.
    Each row shows fractional positions using different characters.
    """
    if len(audio_data) == 0:
        # Draw center line when no audio
        center_row = height // 2
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        for x in range(width):
            grid[center_row][x] = '─'
        return grid_to_text(grid, height)

    # Downsample to fit width
    step = len(audio_data) // width
    if step < 1:
        step = 1
    samples = audio_data[::step][:width]

    # Normalize and scale
    if len(samples) > 0:
        max_val = np.abs(samples).max()
        if max_val > 0:
            samples = samples / max_val * AMPLITUDE_SCALE
            samples = np.clip(samples, -1, 1)

    # Map to vertical positions with sub-pixel precision
    center = (height - 1) / 2.0
    positions = ((-samples) * center + center)
    positions = np.clip(positions, 0, height - 0.001)

    # Create character grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Draw waveform with sub-pixel resolution
    for x, pos in enumerate(positions):
        if x < width:
            row = int(pos)
            fraction = pos - row
            char_index = int(fraction * (len(SUBPIXEL_CHARS) - 1))
            char_index = min(char_index, len(SUBPIXEL_CHARS) - 1)
            grid[row][x] = SUBPIXEL_CHARS[char_index]

    return grid_to_text(grid, height)


def grid_to_text(grid, height):
    """Convert character grid to Rich Text with colors."""
    result = Text()
    center = height // 2

    for row_idx, row in enumerate(grid):
        line = ''.join(row)
        distance = abs(row_idx - center)

        if distance == 0:
            color = "bright_cyan"
        elif distance == 1:
            color = "cyan"
        else:
            color = "blue"

        result.append(line, style=color)
        if row_idx < height - 1:
            result.append("\n")

    return result


def create_upcoming_list(tasks, current_index, completed_ids):
    """
    Create scrolling task list display with absolute numbering.

    Shows a window of 8 tasks centered on current task, with total count.

    Args:
        tasks: List of all tasks
        current_index: Index of current task
        completed_ids: Set of completed task IDs

    Returns:
        Rich Text with scrolling task list window
    """
    upcoming = Text()
    total_tasks = len(tasks)
    window_size = 8  # How many tasks to show

    # Calculate window bounds (keep current task centered when possible)
    half_window = window_size // 2
    start_idx = max(0, current_index - half_window)
    end_idx = min(total_tasks, start_idx + window_size)

    # Adjust start if we hit the end
    if end_idx == total_tasks:
        start_idx = max(0, end_idx - window_size)

    # Show indicator if there are tasks before
    if start_idx > 0:
        upcoming.append(f"  ↑ {start_idx} more above...\n", style="dim italic")

    # Show tasks in window
    for i in range(start_idx, end_idx):
        task = tasks[i]
        # Absolute position number (1-indexed)
        position = i + 1

        # Determine style based on state
        if i == current_index:
            # Current task - highlighted
            upcoming.append(f"→ {position}. ", style="bold cyan")
            upcoming.append(task.title[:48], style="bold white")
            if len(task.title) > 48:
                upcoming.append("...", style="bold white")
        elif task.id in completed_ids:
            # Completed task - strikethrough
            upcoming.append(f"  {position}. ", style="dim")
            upcoming.append(task.title[:48], style="dim strike")
            if len(task.title) > 48:
                upcoming.append("...", style="dim strike")
        else:
            # Future task - normal
            upcoming.append(f"  {position}. ", style="dim")
            upcoming.append(task.title[:48], style="dim white")
            if len(task.title) > 48:
                upcoming.append("...", style="dim white")

        upcoming.append("\n")

    # Show indicator if there are tasks after
    if end_idx < total_tasks:
        remaining = total_tasks - end_idx
        upcoming.append(f"  ↓ {remaining} more below...\n", style="dim italic")

    # Show total count at bottom
    completed_count = len(completed_ids)
    upcoming.append(f"\n  [{completed_count}/{total_tasks} completed]", style="dim cyan")

    return upcoming


def create_blitz_layout(task, tasks, task_index, progress_text, completed_ids, wave_text=None, show_completion=False):
    """Create the blitz mode layout with task, upcoming tasks, and waveform."""

    if show_completion:
        # Show completion state
        completion_text = Text()
        completion_text.append("\n\n")
        completion_text.append("       ✓       \n", style="bold bright_green")
        completion_text.append("  Task Complete!  \n", style="bold cyan")
        completion_text.append("\n")

        task_panel = Panel(
            completion_text,
            title="[bold bright_green]Complete![/bold bright_green]",
            border_style="bright_green",
            padding=(1, 2),
            width=80
        )
    else:
        # Task display
        task_display = Text()
        task_display.append(f"#{task.id} ", style="dim")
        task_display.append(task.title, style="bold white")

        if task.description:
            task_display.append("\n\n", style="dim")
            task_display.append(task.description[:300], style="white")
            if len(task.description) > 300:
                task_display.append("...", style="dim")

        task_display.append("\n\n", style="dim")
        task_display.append(progress_text, style="cyan")

        task_panel = Panel(
            task_display,
            title="[bold]Current Task[/bold]",
            border_style="blue",
            padding=(1, 2),
            width=80
        )

    # Full task list
    task_list = create_upcoming_list(tasks, task_index, completed_ids)
    task_list_panel = Panel(
        task_list,
        title="[bold]Today's Tasks[/bold]",
        border_style="dim blue",
        padding=(0, 1),
        width=80
    )

    # Waveform display
    if wave_text is None:
        wave_text = Text("Connecting to audio...", style="dim")

    wave_panel = Panel(
        wave_text,
        title="[bold]Audio[/bold]",
        border_style="cyan",
        padding=(0, 1),
        width=80
    )

    # Controls
    controls = Text()
    controls.append("d", style="bold green")
    controls.append("=done  ", style="dim")
    controls.append("s", style="bold yellow")
    controls.append("=skip  ", style="dim")
    controls.append("?", style="bold blue")
    controls.append("=details  ", style="dim")
    controls.append("q", style="bold red")
    controls.append("=quit", style="dim")

    controls_panel = Panel(
        controls,
        border_style="dim",
        padding=(0, 1),
        width=80
    )

    # Stack vertically
    layout = Layout()
    layout.split_column(
        Layout(task_panel, size=12),  # Fixed size with room for description
        Layout(task_list_panel, size=10),  # Larger to fit all tasks
        Layout(wave_panel, size=7),
        Layout(controls_panel, size=3)
    )

    return layout


def init_audio_background():
    """Initialize audio in background thread."""
    global audio_stream, audio_device, audio_ready

    try:
        p = pyaudio.PyAudio()
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_output = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        # Find loopback device
        loopback_device = None
        for loopback in p.get_loopback_device_info_generator():
            if default_output["name"] in loopback["name"]:
                loopback_device = loopback
                break

        if loopback_device is None:
            for loopback in p.get_loopback_device_info_generator():
                loopback_device = loopback
                break

        # Open audio stream
        if loopback_device:
            audio_stream = p.open(
                format=pyaudio.paInt16,
                channels=loopback_device["maxInputChannels"],
                rate=int(loopback_device["defaultSampleRate"]),
                frames_per_buffer=CHUNK,
                input=True,
                input_device_index=loopback_device["index"]
            )
            audio_device = loopback_device
            audio_ready = True

    except Exception as e:
        # Silently fail - audio is optional
        pass


def check_keypress():
    """Check if a key has been pressed (non-blocking, Windows)."""
    if msvcrt.kbhit():
        ch = msvcrt.getch()

        # Check for special keys (arrow keys, function keys, etc.)
        # These return two bytes: first is 0x00 or 0xE0, second is the key code
        if ch in (b'\x00', b'\xe0'):
            # Consume the second byte and ignore the special key
            if msvcrt.kbhit():
                msvcrt.getch()
            return None

        # Regular key - decode and return
        try:
            return ch.decode('utf-8').lower()
        except UnicodeDecodeError:
            # If decode fails, ignore the key
            return None

    return None


def run_blitz_mode(project_id=None, scope=None):
    """
    Run blitz mode: focused task completion with audio visualization.

    Args:
        project_id: Optional project ID to filter tasks
        scope: Optional scope to filter tasks (defaults to 'today')

    Displays tasks from specified scope (default: 'today') one at a time.
    Shows live audio waveform for ambient feedback.
    Keyboard controls for task management.
    """
    global audio_stream, audio_device, audio_ready

    console = Console()

    # Determine scope to use (default to 'today')
    target_scope = scope or 'today'

    # Get tasks based on scope
    if target_scope == 'today':
        tasks = service.list_today()
    elif target_scope == 'week':
        tasks = service.list_week()
    elif target_scope == 'backlog':
        tasks = service.list_backlog()
    else:
        # Fallback to today if invalid scope
        tasks = service.list_today()
        target_scope = 'today'

    # Filter by project if specified
    if project_id is not None:
        tasks = [t for t in tasks if t.project_id == project_id]

    if not tasks:
        console.print(f"\n[yellow]No tasks in '{target_scope}' scope![/yellow]")
        if project_id:
            console.print("[dim]No tasks match both the scope and project filter[/dim]")
        else:
            console.print(f"[dim]Use 'pull <id> {target_scope}' to add tasks to {target_scope}[/dim]")
        console.print()
        return

    console.print(f"\n[bold cyan]Entering Blitz Mode[/bold cyan]")
    scope_display = f"[cyan]{target_scope}[/cyan]"
    console.print(f"[dim]{len(tasks)} tasks in {scope_display} scope[/dim]\n")

    # Start audio initialization in background
    audio_thread = threading.Thread(target=init_audio_background, daemon=True)
    audio_thread.start()

    # Blitz loop
    task_index = 0
    completed_count = 0
    completed_ids = set()  # Track completed task IDs for strikethrough

    try:
        with Live(console=console, refresh_per_second=UPDATE_FPS) as live:
            while task_index < len(tasks):
                current_task = tasks[task_index]
                progress_text = f"Task {task_index + 1} of {len(tasks)} • {completed_count} completed"

                # Read audio if available
                wave_text = None
                if audio_ready and audio_stream and audio_device:
                    try:
                        data = audio_stream.read(CHUNK, exception_on_overflow=False)
                        audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)

                        if audio_device["maxInputChannels"] > 1:
                            audio_array = audio_array.reshape(-1, audio_device["maxInputChannels"])
                            audio_array = np.mean(audio_array, axis=1)

                        audio_array = audio_array / 32768.0
                        wave_text = render_waveform(audio_array)
                    except:
                        wave_text = Text("Audio error", style="dim red")
                elif not audio_ready:
                    wave_text = Text("Connecting to audio...", style="dim yellow")
                else:
                    wave_text = Text("No audio device", style="dim")

                # Update display
                live.update(create_blitz_layout(current_task, tasks, task_index, progress_text, completed_ids, wave_text))

                # Check for keypress
                key = check_keypress()

                if key == 'd':
                    # Mark done
                    service.complete_task(current_task.id)
                    completed_count += 1
                    completed_ids.add(current_task.id)  # Track completion

                    # Show completion state momentarily
                    live.update(create_blitz_layout(
                        current_task, tasks, task_index, progress_text, completed_ids, wave_text, show_completion=True
                    ))
                    time.sleep(0.4)

                    # Move to next task
                    task_index += 1

                elif key == 's':
                    # Skip to next
                    task_index += 1

                elif key == '?':
                    # Show full details (pause)
                    live.stop()
                    console.print(f"\n[bold]Task #{current_task.id}[/bold]")
                    console.print(f"Title: {current_task.title}")
                    if current_task.description:
                        console.print(f"Description: {current_task.description}")
                    console.print(f"Created: {current_task.created_at}")
                    console.print("\n[dim]Press any key to continue...[/dim]")
                    msvcrt.getch()
                    live.start()

                elif key == 'q':
                    # Quit blitz mode
                    break

                time.sleep(1.0 / UPDATE_FPS)

        # Cleanup audio
        if audio_stream:
            audio_stream.stop_stream()
            audio_stream.close()

        # Summary
        console.print(f"\n[bold green]Blitz Mode Complete![/bold green]")
        console.print(f"Completed {completed_count} of {len(tasks)} tasks\n")

        if completed_count > 0:
            celebrate_bulk(completed_count, "completed")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Blitz mode interrupted[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]Error in blitz mode: {e}[/red]\n")
    finally:
        # Reset audio state
        audio_stream = None
        audio_device = None
        audio_ready = False
