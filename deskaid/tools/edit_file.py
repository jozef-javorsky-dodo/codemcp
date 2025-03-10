#!/usr/bin/env python3

import difflib
import hashlib
import json
import logging
import os
import re
import stat
from typing import Dict, List, Optional, Tuple

from ..common import commit_changes, get_edit_snippet

# Set up logger
logger = logging.getLogger(__name__)


def detect_file_encoding(file_path: str) -> str:
    """Detect the encoding of a file.

    Args:
        file_path: The path to the file

    Returns:
        The encoding of the file, defaults to 'utf-8'
    """
    # Simple implementation - in a real app, would use chardet or similar
    return "utf-8"


def detect_line_endings(file_path: str) -> str:
    """Detect the line endings of a file.

    Args:
        file_path: The path to the file

    Returns:
        'CRLF' or 'LF'
    """
    with open(file_path, "rb") as f:
        content = f.read()
        if b"\r\n" in content:
            return "CRLF"
        return "LF"


def find_similar_file(file_path: str) -> Optional[str]:
    """Find a similar file with a different extension.

    Args:
        file_path: The path to the file

    Returns:
        The path to a similar file, or None if none found
    """
    # Simple implementation - in a real app, would check for files with different extensions
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        return None

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    for f in os.listdir(directory):
        if f.startswith(base_name + ".") and f != os.path.basename(file_path):
            return os.path.join(directory, f)
    return None


def apply_edit(
    file_path: str, old_string: str, new_string: str
) -> Tuple[List[Dict], str]:
    """Apply an edit to a file.

    Args:
        file_path: The path to the file
        old_string: The text to replace
        new_string: The text to replace it with

    Returns:
        A tuple of (patch, updated_file)
    """
    # Simple patch implementation - in a real app, would use a proper diff library
    if os.path.exists(file_path):
        with open(file_path, "r", encoding=detect_file_encoding(file_path)) as f:
            content = f.read()
    else:
        content = ""
    
    # By the time we reach this function, old_string should be properly
    # matched with the file content - either directly or using the 
    # trailing whitespace stripping fallback in edit_file_content
    updated_file = content.replace(old_string, new_string, 1)

    # Create a simple patch structure
    # This is a simplified version of what the TS code does with the diff library
    patch = []
    if old_string != new_string:
        old_lines = old_string.split("\n")
        new_lines = new_string.split("\n")

        # Find the line number where the change occurs
        before_text = content.split(old_string)[0]
        line_num = before_text.count("\n")

        patch.append(
            {
                "oldStart": line_num + 1,
                "oldLines": len(old_lines),
                "newStart": line_num + 1,
                "newLines": len(new_lines),
                "lines": [f"-{line}" for line in old_lines]
                + [f"+{line}" for line in new_lines],
            }
        )

    return patch, updated_file


def write_text_content(
    file_path: str, content: str, encoding: str = "utf-8", line_endings: str = "LF"
) -> None:
    """Write text content to a file with the specified encoding and line endings.

    Args:
        file_path: The path to the file
        content: The content to write
        encoding: The encoding to use
        line_endings: The line endings to use ('CRLF' or 'LF')
    """
    # Normalize line endings
    if line_endings == "CRLF":
        content = content.replace("\n", "\r\n")
    else:
        content = content.replace("\r\n", "\n")

    with open(file_path, "w", encoding=encoding) as f:
        f.write(content)


def debug_string_comparison(
    s1: str, s2: str, label1: str = "string1", label2: str = "string2"
) -> bool:
    """Thoroughly debug string comparison and identify differences.

    Args:
        s1: First string
        s2: Second string
        label1: Label for the first string
        label2: Label for the second string

    Returns:
        True if strings are different, False if they are the same
    """
    # Basic checks
    length_same = len(s1) == len(s2)
    content_same = s1 == s2

    logger.debug(f"String comparison debug:")
    logger.debug(f"  Length same? {length_same} ({len(s1)} vs {len(s2)})")
    logger.debug(f"  Content same? {content_same}")

    # Hash check
    hash1 = hashlib.md5(s1.encode("utf-8")).hexdigest()
    hash2 = hashlib.md5(s2.encode("utf-8")).hexdigest()
    logger.debug(f"  MD5 hashes: {hash1} vs {hash2}")

    # If strings appear to be the same but should be different
    if content_same:
        # Check for invisible characters or encoding issues
        s1_repr = repr(s1)
        s2_repr = repr(s2)
        logger.debug(f"  Repr comparison: {s1_repr[:100]} vs {s2_repr[:100]}")

        # Check byte by byte
        bytes1 = s1.encode("utf-8")
        bytes2 = s2.encode("utf-8")
        if bytes1 != bytes2:
            logger.debug(
                f"  Strings differ at byte level even though they appear equal as strings!"
            )

            # Find the first differing byte
            for i, (b1, b2) in enumerate(zip(bytes1, bytes2)):
                if b1 != b2:
                    logger.debug(
                        f"  First byte difference at position {i}: {b1} vs {b2}"
                    )
                    break
    else:
        # Find differences
        diff = list(difflib.ndiff(s1.splitlines(), s2.splitlines()))
        changes = [d for d in diff if d.startswith("+ ") or d.startswith("- ")]
        if changes:
            logger.debug(f"  Line differences (first 5):")
            for d in changes[:5]:
                logger.debug(f"    {d}")
                
        # Check if strings are equal after stripping trailing whitespace
        s1_no_trailing = "\n".join([line.rstrip() for line in s1.splitlines()])
        s2_no_trailing = "\n".join([line.rstrip() for line in s2.splitlines()])
        if s1_no_trailing == s2_no_trailing:
            logger.debug("  Strings match when trailing whitespace is stripped from each line!")

    return not content_same


def edit_file_content(
    file_path: str,
    old_string: str,
    new_string: str,
    read_file_timestamps: Optional[Dict[str, float]] = None,
    description: str = "",
) -> str:
    """Edit a file by replacing old_string with new_string.

    Args:
        file_path: The absolute path to the file to edit
        old_string: The text to replace
        new_string: The new text to replace old_string with
        read_file_timestamps: Dictionary mapping file paths to timestamps when they were last read
        description: Short description of the change

    Returns:
        A success message or an error message
    """
    try:
        # Convert to absolute path if needed
        full_file_path = (
            file_path if os.path.isabs(file_path) else os.path.abspath(file_path)
        )

        # Debug string comparison using our thorough utility
        strings_are_different = debug_string_comparison(
            old_string, new_string, "old_string", "new_string"
        )

        if not strings_are_different:
            return "No changes to make: old_string and new_string are exactly the same."

        # Proceed with the edit now that we've confirmed the strings are different

        # Handle creating a new file
        if old_string == "" and os.path.exists(full_file_path):
            return "Cannot create new file - file already exists."

        # Handle creating a new file
        if old_string == "" and not os.path.exists(full_file_path):
            directory = os.path.dirname(full_file_path)
            os.makedirs(directory, exist_ok=True)
            write_text_content(full_file_path, new_string)
            return f"Successfully created {full_file_path}"

        # Check if file exists
        if not os.path.exists(full_file_path):
            # Try to find a similar file
            similar_file = find_similar_file(full_file_path)
            message = f"Error: File does not exist: {full_file_path}"
            if similar_file:
                message += f" Did you mean {similar_file}?"
            return message

        # Check if file is a Jupyter notebook
        if full_file_path.endswith(".ipynb"):
            return "Error: File is a Jupyter Notebook. Use the NotebookEditTool to edit this file."

        # Check if file has been read
        if read_file_timestamps and full_file_path not in read_file_timestamps:
            return (
                "Error: File has not been read yet. Read it first before writing to it."
            )

        # Check if file has been modified since read
        if read_file_timestamps and os.path.exists(full_file_path):
            last_write_time = os.stat(full_file_path).st_mtime
            if last_write_time > read_file_timestamps.get(full_file_path, 0):
                return "Error: File has been modified since read, either by the user or by a linter. Read it again before attempting to write it."

        # Detect encoding and line endings
        encoding = detect_file_encoding(full_file_path)
        line_endings = detect_line_endings(full_file_path)

        # Read the original file
        with open(full_file_path, "r", encoding=encoding) as f:
            content = f.read()

        # Check if old_string exists in the file
        if old_string and old_string not in content:
            # Fallback: Try matching after stripping trailing whitespace from each line
            content_no_trailing_whitespace = "\n".join([line.rstrip() for line in content.split("\n")])
            old_string_no_trailing_whitespace = "\n".join([line.rstrip() for line in old_string.split("\n")])
            
            if old_string_no_trailing_whitespace in content_no_trailing_whitespace:
                # Find the actual text in the original content that matches when trailing whitespace is stripped
                content_lines = content.split("\n")
                old_string_lines = old_string.split("\n")
                
                for i in range(len(content_lines) - len(old_string_lines) + 1):
                    matched = True
                    for j in range(len(old_string_lines)):
                        if content_lines[i + j].rstrip() != old_string_lines[j].rstrip():
                            matched = False
                            break
                    
                    if matched:
                        actual_match = "\n".join(content_lines[i:i + len(old_string_lines)])
                        # Update old_string to use the actual text from the file
                        logger.debug(f"Found match after stripping trailing whitespace. Using actual text from file.")
                        old_string = actual_match
                        break
            else:
                return "Error: String to replace not found in file."

        # Check for uniqueness of old_string
        if old_string and content.count(old_string) > 1:
            matches = content.count(old_string)
            return f"Error: Found {matches} matches of the string to replace. For safety, this tool only supports replacing exactly one occurrence at a time. Add more lines of context to your edit and try again."

        # Apply the edit
        patch, updated_file = apply_edit(full_file_path, old_string, new_string)

        # Create directory if it doesn't exist
        directory = os.path.dirname(full_file_path)
        os.makedirs(directory, exist_ok=True)

        # Write the modified content back to the file
        write_text_content(full_file_path, updated_file, encoding, line_endings)

        # Update read timestamp
        if read_file_timestamps is not None:
            read_file_timestamps[full_file_path] = os.stat(full_file_path).st_mtime

        # Generate a snippet of the edited file to show in the response
        snippet = get_edit_snippet(content, old_string, new_string)

        # Commit the changes
        git_message = ""
        success, message = commit_changes(full_file_path, description)
        if success:
            git_message = f"\n\nChanges committed to git: {description}"
        else:
            git_message = f"\n\nFailed to commit changes to git: {message}"

        return f"Successfully edited {full_file_path}\n\nHere's a snippet of the edited file:\n{snippet}{git_message}"
    except Exception as e:
        return f"Error editing file: {str(e)}"
