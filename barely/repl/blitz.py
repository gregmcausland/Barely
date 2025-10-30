"""
FILE: barely/repl/blitz.py
PURPOSE: Focused task-completion mode with live audio waveform visualizer
EXPORTS:
  - run_blitz_mode() -> None
DEPENDENCIES:
  - core.service (list_today, complete_task, uncomplete_task)
  - rich (Console, Layout, Panel, Text, Live)
  - numpy (audio processing)
  - pyaudiowpatch (audio capture)
  - keyboard input handling
NOTES:
  - Displays tasks from 'today' scope one at a time
  - Live audio waveform visualization
  - Shows upcoming tasks in list below current task
  - Keyboard controls: d=done, u=un-complete, ↑/↓=navigate, q=quit, ?=details
  - Completed tasks show with different styling when navigated to
  - Returns to REPL when user quits
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
from .parser import ParseResult


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
audio_pyaudio = None  # Store PyAudio instance for cleanup
audio_ready = False
audio_lock = threading.Lock()  # Protect audio state access
audio_init_timeout = 5.0  # Maximum time to wait for audio initialization


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

    is_completed = task.id in completed_ids or task.scope == "archived"

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
    elif is_completed:
        # Completed task display - different styling
        task_display = Text()
        task_display.append(f"#{task.id} ", style="dim")
        task_display.append("✓ ", style="bold bright_green")
        task_display.append(task.title, style="bold strike bright_green")
        
        if task.description:
            task_display.append("\n\n", style="dim")
            task_display.append(task.description[:300], style="strike dim white")
            if len(task.description) > 300:
                task_display.append("...", style="strike dim")

        task_display.append("\n\n", style="dim")
        task_display.append(progress_text, style="dim cyan")
        task_display.append("\n\n", style="dim")
        task_display.append("[Press 'u' to un-complete]", style="dim italic yellow")

        task_panel = Panel(
            task_display,
            title="[bold bright_green]Completed Task[/bold bright_green]",
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
    controls.append("u", style="bold yellow")
    controls.append("=un-complete  ", style="dim")
    controls.append("↑/↓", style="bold yellow")
    controls.append("=navigate  ", style="dim")
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
    """Initialize audio in background thread with timeout protection."""
    global audio_stream, audio_device, audio_ready, audio_pyaudio

    try:
        # Create PyAudio instance
        p = pyaudio.PyAudio()
        with audio_lock:
            audio_pyaudio = p  # Store for cleanup

        # Get WASAPI info with timeout protection
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            # WASAPI not available - audio won't work
            with audio_lock:
                audio_ready = True  # Mark as "ready" (failed) so we don't wait forever
                audio_pyaudio = None
            if p:
                try:
                    p.terminate()
                except:
                    pass
            return

        try:
            default_output = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        except (KeyError, OSError):
            # No default device
            with audio_lock:
                audio_ready = True
                audio_pyaudio = None
            if p:
                try:
                    p.terminate()
                except:
                    pass
            return

        # Find loopback device with timeout protection
        loopback_device = None
        try:
            for loopback in p.get_loopback_device_info_generator():
                if default_output["name"] in loopback["name"]:
                    loopback_device = loopback
                    break

            if loopback_device is None:
                for loopback in p.get_loopback_device_info_generator():
                    loopback_device = loopback
                    break
        except (StopIteration, OSError):
            # No loopback devices available
            with audio_lock:
                audio_ready = True
                audio_pyaudio = None
            if p:
                try:
                    p.terminate()
                except:
                    pass
            return

        # Open audio stream with error handling
        if loopback_device:
            try:
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=loopback_device["maxInputChannels"],
                    rate=int(loopback_device["defaultSampleRate"]),
                    frames_per_buffer=CHUNK,
                    input=True,
                    input_device_index=loopback_device["index"],
                    stream_callback=None  # Use blocking reads
                )
                with audio_lock:
                    audio_stream = stream
                    audio_device = loopback_device
                    audio_ready = True
            except (OSError, ValueError) as e:
                # Stream creation failed
                with audio_lock:
                    audio_ready = True
                    audio_pyaudio = None
                if p:
                    try:
                        p.terminate()
                    except:
                        pass
        else:
            with audio_lock:
                audio_ready = True
                audio_pyaudio = None
            if p:
                try:
                    p.terminate()
                except:
                    pass

    except Exception as e:
        # Any other error - mark as ready (failed) so we don't wait forever
        with audio_lock:
            audio_ready = True
            audio_pyaudio = None
        try:
            if 'p' in locals() and p:
                p.terminate()
        except:
            pass


def check_keypress():
    """Check if a key has been pressed (non-blocking, Windows)."""
    if msvcrt.kbhit():
        ch = msvcrt.getch()

        # Check for special keys (arrow keys, function keys, etc.)
        # These return two bytes: first is 0x00 or 0xE0, second is the key code
        if ch in (b'\x00', b'\xe0'):
            # Consume the second byte to get the actual key code
            if msvcrt.kbhit():
                key_code = msvcrt.getch()
                # Arrow key codes: H=Up, P=Down, K=Left, M=Right
                if key_code == b'H':
                    return 'up'
                elif key_code == b'P':
                    return 'down'
                # Ignore other special keys
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

    # Reset audio state
    with audio_lock:
        audio_stream = None
        audio_device = None
        audio_pyaudio = None
        audio_ready = False

    # Start audio initialization in background
    audio_thread = threading.Thread(target=init_audio_background, daemon=True)
    audio_thread.start()

    # Wait for audio initialization with timeout
    start_time = time.time()
    while not audio_ready and (time.time() - start_time) < audio_init_timeout:
        time.sleep(0.1)

    # Blitz loop
    task_index = 0
    completed_count = 0
    completed_ids = set()  # Track completed task IDs for strikethrough
    audio_error_count = 0  # Track consecutive audio errors
    max_audio_errors = 5  # Disable audio after this many errors

    try:
        with Live(console=console, refresh_per_second=UPDATE_FPS) as live:
            while True:
                # Clamp task_index to valid range
                task_index = max(0, min(task_index, len(tasks) - 1))
                current_task = tasks[task_index]
                progress_text = f"Task {task_index + 1} of {len(tasks)} • {completed_count} completed"

                # Read audio if available (with guardrails)
                wave_text = None
                with audio_lock:
                    stream_ready = audio_ready and audio_stream and audio_device

                if stream_ready and audio_error_count < max_audio_errors:
                    try:
                        # Get stream reference safely
                        with audio_lock:
                            stream_ref = audio_stream
                            device_ref = audio_device

                        if stream_ref is None:
                            wave_text = Text("Audio disconnected", style="dim")
                            audio_error_count += 1
                        else:
                            # Check if stream is active (protected)
                            try:
                                is_active = stream_ref.is_active()
                            except (OSError, AttributeError):
                                # Stream is in bad state
                                is_active = False

                            if is_active:
                                try:
                                    # Try to read audio data (non-blocking with exception_on_overflow=False)
                                    # This will return immediately if no data available
                                    data = stream_ref.read(CHUNK, exception_on_overflow=False)
                                    
                                    if len(data) > 0:
                                        audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)

                                        if device_ref and device_ref.get("maxInputChannels", 1) > 1:
                                            audio_array = audio_array.reshape(-1, device_ref["maxInputChannels"])
                                            audio_array = np.mean(audio_array, axis=1)

                                        audio_array = audio_array / 32768.0
                                        wave_text = render_waveform(audio_array)
                                        audio_error_count = 0  # Reset error count on success
                                    else:
                                        # No data available - skip this frame
                                        wave_text = Text("Waiting for audio...", style="dim")
                                except (OSError, IOError, ValueError) as e:
                                    # Stream read error - increment counter
                                    raise
                            else:
                                # Stream not active
                                wave_text = Text("Audio inactive", style="dim")
                                audio_error_count += 1
                    except (OSError, IOError, ValueError) as e:
                        # Audio read error - increment counter
                        audio_error_count += 1
                        if audio_error_count >= max_audio_errors:
                            wave_text = Text("Audio disabled (errors)", style="dim red")
                            # Disable audio stream
                            with audio_lock:
                                if audio_stream:
                                    try:
                                        if audio_stream.is_active():
                                            audio_stream.stop_stream()
                                        audio_stream.close()
                                    except:
                                        pass
                                    audio_stream = None
                        else:
                            wave_text = Text(f"Audio error ({audio_error_count}/{max_audio_errors})", style="dim yellow")
                    except Exception as e:
                        # Unexpected error - disable audio
                        audio_error_count = max_audio_errors
                        wave_text = Text("Audio error", style="dim red")
                        # Try to clean up stream
                        with audio_lock:
                            if audio_stream:
                                try:
                                    if audio_stream.is_active():
                                        audio_stream.stop_stream()
                                    audio_stream.close()
                                except:
                                    pass
                                audio_stream = None
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

                    # Move to next task (if available)
                    if task_index < len(tasks) - 1:
                        task_index += 1

                elif key == 'u':
                    # Un-complete task
                    if current_task.id in completed_ids or current_task.status == "done":
                        uncompleted_task_id = current_task.id
                        service.uncomplete_task(uncompleted_task_id)
                        completed_count -= 1
                        completed_ids.discard(uncompleted_task_id)  # Remove from completed set
                        # Refresh task list to get updated status
                        if target_scope == 'today':
                            tasks = service.list_today()
                        elif target_scope == 'week':
                            tasks = service.list_week()
                        elif target_scope == 'backlog':
                            tasks = service.list_backlog()
                        # Re-filter by project if specified
                        if project_id is not None:
                            tasks = [t for t in tasks if t.project_id == project_id]
                        # Find the uncompleted task in the refreshed list to maintain position
                        new_index = None
                        for i, t in enumerate(tasks):
                            if t.id == uncompleted_task_id:
                                new_index = i
                                break
                        if new_index is not None:
                            task_index = new_index
                            current_task = tasks[task_index]
                        else:
                            # Task not found in refreshed list (shouldn't happen), clamp index
                            task_index = max(0, min(task_index, len(tasks) - 1))
                            if task_index < len(tasks):
                                current_task = tasks[task_index]
                        progress_text = f"Task {task_index + 1} of {len(tasks)} • {completed_count} completed"

                elif key == 'up':
                    # Navigate to previous task
                    if task_index > 0:
                        task_index -= 1

                elif key == 'down':
                    # Navigate to next task
                    if task_index < len(tasks) - 1:
                        task_index += 1

                elif key == '?':
                    # Show full details using view command for consistency
                    live.stop()
                    console.print()  # Add spacing
                    # Import here to avoid circular import with main.py
                    from .main import handle_show_command
                    # Create ParseResult with task ID to invoke view command
                    parse_result = ParseResult(
                        command="view",
                        args=[str(current_task.id)],
                        flags={},
                        raw_input=f"view {current_task.id}"
                    )
                    handle_show_command(parse_result)
                    console.print("\n[dim]Press any key to continue...[/dim]")
                    msvcrt.getch()
                    live.start()

                elif key == 'q':
                    # Quit blitz mode
                    break

                time.sleep(1.0 / UPDATE_FPS)

        # Summary
        console.print(f"\n[bold green]Blitz Mode Complete![/bold green]")
        console.print(f"Completed {completed_count} of {len(tasks)} tasks\n")

        if completed_count > 0:
            celebrate_bulk(completed_count, "completed")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Blitz mode interrupted[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]Error in blitz mode: {e}[/red]\n")
        import traceback
        console.print("[dim]" + traceback.format_exc() + "[/dim]")
    finally:
        # Cleanup audio resources (with protection)
        with audio_lock:
            if audio_stream:
                try:
                    if audio_stream.is_active():
                        audio_stream.stop_stream()
                    audio_stream.close()
                except:
                    pass
                audio_stream = None

            if audio_pyaudio:
                try:
                    audio_pyaudio.terminate()
                except:
                    pass
                audio_pyaudio = None

            audio_device = None
            audio_ready = False
