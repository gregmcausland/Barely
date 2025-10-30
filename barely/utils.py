"""
FILE: barely/utils.py
PURPOSE: Shared utility functions for CLI and REPL
EXPORTS:
  - improve_title_with_ai(title) -> Optional[dict] with 'title' and optional 'description'
DEPENDENCIES:
  - subprocess (for calling Claude CLI)
  - tempfile (for creating temporary prompt file)
  - os (for file cleanup)
  - sys (for platform detection)
  - shutil (for finding executables in PATH)
NOTES:
  - Used by both CLI and REPL for AI title/description improvement
  - Handles cross-platform command execution (cat vs type)
"""

import sys
import subprocess
import tempfile
import os
import shutil
import json
import re
from typing import Optional, Dict


def improve_title_with_ai(title: str) -> Optional[Dict[str, str]]:
    """
    Use local Claude CLI to improve a task title and optionally generate a description.
    
    Args:
        title: The original task title to improve
        
    Returns:
        Dictionary with 'title' (required) and optionally 'description' (if Claude generates one),
        or None if Claude call fails
        
    Notes:
        Uses command: cat prompt | claude -p "<title>"
        Creates a temporary prompt file with instructions for Claude
    """
    # Prompt instructions for Claude
    prompt_instructions = """You are a task management assistant. Your job is to take messy, garbled, or poorly written task titles and transform them into clear, concise, and actionable task titles.

TITLE GUIDELINES:
- Keep titles concise (typically under 60 characters)
- Use action verbs (e.g., "Write", "Fix", "Update", "Review")
- Be specific about what needs to be done
- Remove filler words and unnecessary details
- Maintain the core intent of the original task
- Write in imperative mood (e.g., "Write docs" not "Writing docs")

DESCRIPTION GUIDELINES:
- If the original task contains multiple ideas or needs clarification, generate a helpful description
- Description should expand on context, requirements, or steps needed
- Keep descriptions concise but informative (typically 1-3 sentences)
- If the title is clear and self-explanatory, you may omit the description field

CRITICAL: You must respond with ONLY a valid JSON object in this exact format:
{
  "title": "improved title here",
  "description": "optional helpful description here - only include if useful"
}

The "title" field is REQUIRED. The "description" field is OPTIONAL - only include it if it adds value.
If no description is needed, omit the "description" field entirely.

Do not include any explanations, conversational text, markdown formatting, or code blocks. Output ONLY the raw JSON object."""
    
    try:
        # Find claude executable in PATH first
        # This handles cases where PATH isn't properly inherited by subprocess
        claude_path = shutil.which("claude")
        
        # If not found, try querying the shell directly (especially on Windows)
        if not claude_path and sys.platform == "win32":
            # On Windows, try using 'where' command to find claude
            try:
                where_result = subprocess.run(
                    ["where.exe", "claude"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if where_result.returncode == 0 and where_result.stdout.strip():
                    claude_path = where_result.stdout.strip().split('\n')[0].strip()
            except Exception:
                pass
        
        # If still not found, try getting PATH from shell environment
        if not claude_path:
            # On Windows, try to get PATH from environment variable
            # Sometimes PATH is set in shell profile but not inherited
            env_path = os.environ.get("PATH", "")
            if env_path:
                # Try each directory in PATH manually
                for path_dir in env_path.split(os.pathsep):
                    potential_path = os.path.join(path_dir, "claude.exe")
                    if os.path.exists(potential_path):
                        claude_path = potential_path
                        break
                    # Also try without .exe extension
                    potential_path = os.path.join(path_dir, "claude")
                    if os.path.exists(potential_path):
                        claude_path = potential_path
                        break
        
        # On Windows, if we're going to use shell=True, we can use "claude" directly
        # since the shell will have access to the full PATH
        use_shell = sys.platform == "win32"
        if use_shell:
            claude_cmd_name = "claude"  # Let shell resolve it
        elif claude_path:
            claude_cmd_name = claude_path
        else:
            # Don't print here - let caller handle error messages
            return None
        
        # Create temporary prompt file with instructions + original title
        full_prompt = prompt_instructions + f"""


ORIGINAL TASK TITLE TO IMPROVE:
{title}

Analyze this task title. Generate an improved title and, if helpful, a description. Return ONLY the JSON object with the improved title and optional description."""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as prompt_file:
            prompt_file.write(full_prompt)
            prompt_path = prompt_file.name
        
        try:
            # Build command: cat prompt | claude -p "<title>" --model haiku
            # On Windows, use type instead of cat
            if sys.platform == "win32":
                cat_cmd = ["type", prompt_path]
                # On Windows, use shell=True to get proper PATH access
                # Build the full command as a shell string
                shell_cmd = f'type "{prompt_path}" | "{claude_cmd_name}" -p "{title}" --model haiku'
                
                # Run through shell so PATH is properly resolved
                result = subprocess.run(
                    shell_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=30
                )
                
                if result.returncode != 0:
                    return None
                
                raw_output = result.stdout.strip()
            else:
                cat_cmd = ["cat", prompt_path]
                
                # Use the full path to claude with haiku model for lower token usage
                claude_cmd = [claude_cmd_name, "-p", title, "--model", "haiku"]
                
                # Run: cat prompt | claude -p "<title>" --model haiku
                # Pipe the prompt file contents into claude
                cat_process = subprocess.Popen(
                    cat_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8'
                )
                
                claude_process = subprocess.run(
                    claude_cmd,
                    stdin=cat_process.stdout,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=30  # Timeout after 30 seconds
                )
                
                # Wait for cat process to finish and close stdout so claude gets EOF
                cat_process.wait()
                cat_process.stdout.close()
                
                if claude_process.returncode != 0:
                    return None
                
                raw_output = claude_process.stdout.strip()
            
            # Try to parse JSON first (preferred structured format)
            result_dict = None
            
            # Strategy 1: Try parsing the entire output as JSON (best case)
            try:
                parsed = json.loads(raw_output)
                if isinstance(parsed, dict) and "title" in parsed:
                    result_dict = parsed
            except json.JSONDecodeError:
                pass
            
            # Strategy 2: Extract JSON from markdown code blocks (common case)
            if not result_dict:
                # Look for JSON in code blocks (```json ... ``` or ``` ... ```)
                code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_output, re.DOTALL)
                if code_block_match:
                    try:
                        json_str = code_block_match.group(1)
                        parsed = json.loads(json_str)
                        if isinstance(parsed, dict) and "title" in parsed:
                            result_dict = parsed
                    except json.JSONDecodeError:
                        pass
            
            # Strategy 3: Find JSON object in the text (handles escaped quotes and nested structures)
            if not result_dict:
                # Find the first { and try to extract a complete JSON object
                # This handles cases where JSON is embedded in text
                start_idx = raw_output.find('{')
                if start_idx != -1:
                    # Try to find a matching closing brace
                    brace_count = 0
                    for i in range(start_idx, len(raw_output)):
                        if raw_output[i] == '{':
                            brace_count += 1
                        elif raw_output[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                # Found a complete JSON object
                                try:
                                    json_str = raw_output[start_idx:i+1]
                                    parsed = json.loads(json_str)
                                    if isinstance(parsed, dict) and "title" in parsed:
                                        result_dict = parsed
                                        break
                                except json.JSONDecodeError:
                                    pass
                                # Continue searching for another JSON object
                                start_idx = raw_output.find('{', i + 1)
                                if start_idx == -1:
                                    break
                                brace_count = 0
            
            # Fallback: if no JSON found, try to extract title from conversational response
            if not result_dict:
                # Try to find quoted title in the response
                title_match = re.search(r'"title"\s*:\s*"([^"]+)"', raw_output)
                if title_match:
                    result_dict = {"title": title_match.group(1)}
                    # Try to find description too
                    desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', raw_output)
                    if desc_match:
                        result_dict["description"] = desc_match.group(1)
                else:
                    # Fallback to first non-empty line (strip quotes)
                    lines = raw_output.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('You') and not line.startswith('Here') and not line.startswith('I'):
                            # Remove markdown formatting and quotes
                            line = re.sub(r'^```[a-z]*\s*', '', line)
                            line = re.sub(r'\s*```$', '', line)
                            if line.startswith('"') and line.endswith('"'):
                                line = line[1:-1]
                            elif line.startswith("'") and line.endswith("'"):
                                line = line[1:-1]
                            if line and len(line) >= 2:
                                result_dict = {"title": line}
                                break
            
            # Validate we got something useful
            if not result_dict or "title" not in result_dict:
                return None
            
            title_value = result_dict["title"].strip()
            if not title_value or len(title_value) < 2:
                return None
            
            # Build result dict with title (required) and description (optional)
            result = {"title": title_value}
            
            # Include description if present and non-empty
            if "description" in result_dict:
                desc_value = result_dict["description"].strip()
                if desc_value and len(desc_value) >= 2:
                    result["description"] = desc_value
            
            return result
            
        finally:
            # Clean up temp file
            try:
                os.unlink(prompt_path)
            except Exception:
                pass  # Ignore cleanup errors
                
    except FileNotFoundError:
        # Don't print here - let caller handle error messages
        return None
    except subprocess.TimeoutExpired:
        # Don't print here - let caller handle error messages
        return None
    except Exception:
        # Don't print here - let caller handle error messages
        return None

