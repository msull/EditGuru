import os
import re
import shutil
import subprocess
from typing import List, Optional

from pydantic import BaseModel, Field
from supersullytools.llm.agent import AgentTool
from supersullytools.llm.completions import CompletionHandler

from .config import ConfigManager


# get_ai_tools function
def get_ai_tools(completion_handler: "CompletionHandler") -> list[AgentTool]:
    _ = completion_handler  # feed the linter for now
    tools = [
        (ListFiles, list_files, False),
        (ReadFile, read_file, True),
        (WriteFile, write_file, True),
        (CreateDirectory, create_directory, True),
        (AddToFile, add_to_file, True),
        (DeleteFile, delete_file, False),
        (MoveFile, move_file, True),
        (CheckFileExistence, CheckFileExistence, True),
    ]
    all_tools = [AgentTool(name=x[0].__name__, params_model=x[0], mechanism=x[1], safe_tool=x[2]) for x in tools]
    return all_tools


# 1. Replace Text in Files
class ReplaceText(BaseModel):
    file_paths: list[str] = Field(
        description="list of file paths within the repository where text replacement should occur."
    )
    search_text: str = Field(description="The text or regex pattern to search for.")
    replacement_text: str = Field(description="The text to replace with.")
    use_regex: bool = Field(
        default=False, description="Set to True to interpret 'search_text' as a regular expression."
    )
    case_sensitive: bool = Field(default=True, description="Set to False for case-insensitive search.")


def replace_text_in_files(input: ReplaceText) -> str:
    """
    Replaces occurrences of 'search_text' with 'replacement_text' in the specified files.
    """
    config = ConfigManager.get_instance()
    total_replacements = 0
    for relative_path in input.file_paths:
        target_file = os.path.join(config.base_path, relative_path)

        if not os.path.isfile(target_file):
            raise FileNotFoundError(f"The file '{relative_path}' does not exist.")

        if not os.path.commonpath([config.base_path, relative_path]) == config.base_path:
            raise ValueError("Path is outside allowed directory")

        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()

        if input.use_regex:
            flags = 0
            if not input.case_sensitive:
                flags |= re.IGNORECASE
            pattern = re.compile(input.search_text, flags)
            new_content, num_replacements = pattern.subn(input.replacement_text, content)
        else:
            if input.case_sensitive:
                new_content = content.replace(input.search_text, input.replacement_text)
                num_replacements = content.count(input.search_text)
            else:
                # Case-insensitive simple string replacement
                pattern = re.compile(re.escape(input.search_text), re.IGNORECASE)
                new_content, num_replacements = pattern.subn(input.replacement_text, content)

        if num_replacements > 0:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            total_replacements += num_replacements

    return f"Text replacement completed. Total replacements made: {total_replacements}."


# 2. Check File Existence
class CheckFileExistence(BaseModel):
    file_path: str = Field(description="Path to the file to check within the repository.")


def check_file_existence(input: CheckFileExistence) -> str:
    """
    Checks whether the specified file exists in the repository.
    """
    config = ConfigManager.get_instance()

    target_file = os.path.join(config.base_path, input.file_path)

    if not os.path.commonpath([config.base_path, os.path.abspath(target_file)]) == config.base_path:
        raise ValueError("File path is outside the repository.")

    if os.path.isfile(target_file):
        return f"File '{input.file_path}' exists."
    else:
        return f"File '{input.file_path}' does not exist."


# 3. Create Directory
class CreateDirectory(BaseModel):
    directory_path: str = Field(description="Path to the new directory within the repository.")


def create_directory(input: CreateDirectory) -> str:
    """
    Creates a new directory at the specified path within the repository.
    """
    config = ConfigManager.get_instance()

    target_directory = os.path.join(config.base_path, input.directory_path)

    if not os.path.commonpath([config.base_path, os.path.abspath(target_directory)]) == config.base_path:
        raise ValueError("Directory path is outside the repository.")

    if os.path.exists(target_directory):
        raise FileExistsError(f"Directory '{input.directory_path}' already exists.")

    os.makedirs(target_directory, exist_ok=True)

    return f"Directory '{input.directory_path}' created successfully."


# 4. Search in Files
class SearchInFiles(BaseModel):
    search_text: str = Field(description="The text or regex pattern to search for.")
    file_paths: Optional[list[str]] = Field(
        default=None,
        description="list of file paths to search in. If not provided, searches all files in the repository.",
    )
    use_regex: bool = Field(
        default=False, description="Set to True to interpret 'search_text' as a regular expression."
    )
    case_sensitive: bool = Field(default=True, description="Set to False for case-insensitive search.")


def search_in_files(input: SearchInFiles) -> dict[str, list[int]]:
    """
    Searches for 'search_text' in specified files and returns a dictionary with file paths and line numbers of matches.
    """
    config = ConfigManager.get_instance()

    matched_files = {}
    if input.file_paths:
        files_to_search = [os.path.join(config.base_path, path) for path in input.file_paths]
    else:
        # Get all files in the repo
        files_to_search = []
        for root, dirs, files in os.walk(config.base_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]
            for file in files:
                files_to_search.append(os.path.join(root, file))

    for file_path in files_to_search:
        if not os.path.commonpath([config.base_path, os.path.abspath(file_path)]) == config.base_path:
            continue  # Skip files outside the repo

        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except (UnicodeDecodeError, PermissionError):
                continue  # Skip files that cannot be read

            matched_lines = []
            for idx, line in enumerate(lines):
                if input.use_regex:
                    flags = 0
                    if not input.case_sensitive:
                        flags |= re.IGNORECASE
                    if re.search(input.search_text, line, flags):
                        matched_lines.append(idx + 1)
                else:
                    if input.case_sensitive:
                        if input.search_text in line:
                            matched_lines.append(idx + 1)
                    else:
                        if input.search_text.lower() in line.lower():
                            matched_lines.append(idx + 1)

            if matched_lines:
                relative_path = os.path.relpath(file_path, config.base_path)
                matched_files[relative_path] = matched_lines

    return matched_files  # Returns a dict with file paths and lists of matching line numbers


class ListFiles(BaseModel):
    recursive: bool = Field(
        default=False,
        description=(
            "Set to True to list files recursively; "
            "be careful with this option if there may be lots of files, "
            "as it can overwhelm your system"
        ),
    )
    path: Optional[str] = Field(default=None, description="Sub-path within the repository to list files from.")


def list_files(input: ListFiles) -> List[str]:
    # Get the root of the git repository or cwd
    config = ConfigManager.get_instance()
    target_path = os.path.join(config.base_path, input.path) if input.path else config.base_path

    # Verify the target path is within the repo to avoid unintended access
    if not os.path.commonpath([config.base_path, target_path]) == config.base_path:
        raise ValueError("Path is outside allowed directory")

    # If use_cwd is True, list files directly from the filesystem
    if config.use_cwd:
        if input.recursive:
            # Recursive file listing using os.walk
            return [os.path.join(dp, f) for dp, dn, filenames in os.walk(target_path) for f in filenames]
        else:
            # Non-recursive listing of files and directories at the specified level
            return [f + "/" if os.path.isdir(os.path.join(target_path, f)) else f for f in os.listdir(target_path)]
    else:
        # Proceed with Git-based file listing
        git_command = ["git", "ls-files"]
        if not input.recursive:
            # Non-recursive; restrict to the specified directory only
            git_command.extend(["--directory", target_path])
        else:
            # Recursive; start from target path (Git is recursive by default here)
            git_command.append(target_path)

        # Run the git command to get only tracked files and directories
        try:
            tracked_files = subprocess.check_output(git_command, cwd=config.base_path).decode().splitlines()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error executing git command: {e}")

        # Filter output based on recursive mode
        if input.recursive:
            # Recursive: only list files
            tracked_files = [f for f in tracked_files if not f.endswith("/")]
        else:
            # Non-recursive: include both files and directories at the specified level
            tracked_files = [f + "/" if os.path.isdir(os.path.join(config.base_path, f)) else f for f in tracked_files]

        return tracked_files


# 5. Read File with Line Numbers
class ReadFile(BaseModel):
    file_path: str = Field(description="Path to the file within the repository.")


def read_file(input: ReadFile) -> list[str]:
    config = ConfigManager.get_instance()
    target_file = os.path.join(config.base_path, input.file_path)

    if not os.path.isfile(target_file):
        raise FileNotFoundError("The specified file does not exist.")

    if not os.path.commonpath([config.base_path, os.path.abspath(target_file)]) == config.base_path:
        raise ValueError("File is outside the repository.")

    with open(target_file, "r") as f:
        lines = f.readlines()

    # Return lines with line numbers
    return [f"{idx + 1}: {line.rstrip()}" for idx, line in enumerate(lines)]


# 6. Write New File
class WriteFile(BaseModel):
    """Write a new file that either doesn't exist or overwrites an existing file."""

    file_path: str = Field(description="Path where the new file will be created.")
    content: str = Field(description="Content to write into the new file.")
    overwrite: bool = Field(False, description="Completely replace any existing content at the path")


def write_file(input: WriteFile) -> str:
    config = ConfigManager.get_instance()
    target_file = os.path.join(config.base_path, input.file_path)

    if os.path.exists(target_file):
        if not input.overwrite:
            raise FileExistsError("File already exists.")

    if not os.path.commonpath([config.base_path, os.path.abspath(target_file)]) == config.base_path:
        raise ValueError("File path is outside the repository.")

    # Ensure the directory exists
    os.makedirs(os.path.dirname(target_file), exist_ok=True)

    with open(target_file, "w") as f:
        f.write(input.content)

    return f"File {input.file_path} created successfully."


# 7. Edit Existing File
class EditFile(BaseModel):
    """Edit an existing file; always re-read the file if you want to make further edits after using this."""

    file_path: str = Field(description="Path to the file to edit.")
    start_line: int = Field(description="Starting line number for the edit.")
    end_line: int = Field(description="Ending line number for the edit.")
    replacement_text: str = Field(description="Text to replace between the specified lines.")


def edit_file(input: EditFile) -> str:
    config = ConfigManager.get_instance()
    target_file = os.path.join(config.base_path, input.file_path)

    if not os.path.isfile(target_file):
        raise FileNotFoundError("The specified file does not exist.")

    if not os.path.commonpath([config.base_path, os.path.abspath(target_file)]) == config.base_path:
        raise ValueError("File is outside the repository.")

    with open(target_file, "r") as f:
        lines = f.readlines()

    if input.start_line < 1 or input.end_line > len(lines):
        raise ValueError("Line numbers are out of range.")

    # Adjust indices for 0-based indexing
    start_idx = input.start_line - 1
    end_idx = input.end_line

    # Replace the specified lines
    lines[start_idx:end_idx] = [input.replacement_text + "\n"]

    with open(target_file, "w") as f:
        f.writelines(lines)

    return f"File {input.file_path} edited successfully."


# 8. Add to File
class AddToFile(BaseModel):
    file_path: str = Field(description="Path to the file to add content to.")
    content: str = Field(description="Content to add to the file.")
    insert_at_line: Optional[int] = Field(
        default=None, description="Line number to insert the content at. If not provided, appends to the end."
    )


def add_to_file(input: AddToFile):
    config = ConfigManager.get_instance()
    target_file = os.path.join(config.base_path, input.file_path)

    if not os.path.isfile(target_file):
        raise FileNotFoundError("The specified file does not exist.")

    if not os.path.commonpath([config.base_path, os.path.abspath(target_file)]) == config.base_path:
        raise ValueError("File is outside the repository.")

    with open(target_file, "r") as f:
        lines = f.readlines()

    if input.insert_at_line:
        if input.insert_at_line < 1 or input.insert_at_line > len(lines) + 1:
            raise ValueError("Insert line number is out of range.")

        # Adjust index for 0-based indexing
        idx = input.insert_at_line - 1
        lines.insert(idx, input.content + "\n")
    else:
        lines.append(input.content + "\n")

    with open(target_file, "w") as f:
        f.writelines(lines)

    return read_file(ReadFile(file_path=input.file_path))


# 9. Delete File
class DeleteFile(BaseModel):
    file_path: str = Field(description="Path to the file to delete.")


def delete_file(input: DeleteFile) -> str:
    config = ConfigManager.get_instance()
    target_file = os.path.join(config.base_path, input.file_path)

    if not os.path.isfile(target_file):
        raise FileNotFoundError("The specified file does not exist.")

    if not os.path.commonpath([config.base_path, os.path.abspath(target_file)]) == config.base_path:
        raise ValueError("File is outside the repository.")

    os.remove(target_file)

    return f"File {input.file_path} deleted successfully."


# 10. Move or Copy File
class MoveFile(BaseModel):
    source_path: str = Field(description="Current path of the file.")
    destination_path: str = Field(description="New path for the file.")
    copy_file: bool = Field(default=False, description="Set to True to copy the file instead of moving it.")


def move_file(input: MoveFile) -> str:
    config = ConfigManager.get_instance()
    source_file = os.path.join(config.base_path, input.source_path)
    dest_file = os.path.join(config.base_path, input.destination_path)

    if not os.path.isfile(source_file):
        raise FileNotFoundError("The source file does not exist.")

    if not os.path.commonpath([config.base_path, os.path.abspath(dest_file)]) == config.base_path:
        raise ValueError("Destination is outside the repository.")

    # Ensure the destination directory exists
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)

    if input.copy_file:
        shutil.copy2(source_file, dest_file)
        action = "copied"
    else:
        shutil.move(source_file, dest_file)
        action = "moved"

    return f"File {input.source_path} {action} to {input.destination_path} successfully."
