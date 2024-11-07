import os
import re
import shutil
import subprocess
from typing import List, Optional

from pydantic import BaseModel, Field
from supersullytools.llm.agent import AgentTool


# 1. Replace Text in Files
class ReplaceTextInput(BaseModel):
    file_paths: list[str] = Field(
        description="list of file paths within the repository where text replacement should occur."
    )
    search_text: str = Field(description="The text or regex pattern to search for.")
    replacement_text: str = Field(description="The text to replace with.")
    use_regex: bool = Field(
        default=False, description="Set to True to interpret 'search_text' as a regular expression."
    )
    case_sensitive: bool = Field(default=True, description="Set to False for case-insensitive search.")


def replace_text_in_files(input: ReplaceTextInput) -> str:
    """
    Replaces occurrences of 'search_text' with 'replacement_text' in the specified files.
    """
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()

    total_replacements = 0
    for relative_path in input.file_paths:
        target_file = os.path.join(repo_root, relative_path)

        if not os.path.isfile(target_file):
            raise FileNotFoundError(f"The file '{relative_path}' does not exist.")

        if not os.path.commonpath([repo_root, os.path.abspath(target_file)]) == repo_root:
            raise ValueError(f"File '{relative_path}' is outside the repository.")

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
class CheckFileExistenceInput(BaseModel):
    file_path: str = Field(description="Path to the file to check within the repository.")


def check_file_existence(input: CheckFileExistenceInput) -> str:
    """
    Checks whether the specified file exists in the repository.
    """
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()

    target_file = os.path.join(repo_root, input.file_path)

    if not os.path.commonpath([repo_root, os.path.abspath(target_file)]) == repo_root:
        raise ValueError("File path is outside the repository.")

    if os.path.isfile(target_file):
        return f"File '{input.file_path}' exists."
    else:
        return f"File '{input.file_path}' does not exist."


# 3. Create Directory
class CreateDirectoryInput(BaseModel):
    directory_path: str = Field(description="Path to the new directory within the repository.")


def create_directory(input: CreateDirectoryInput) -> str:
    """
    Creates a new directory at the specified path within the repository.
    """
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()

    target_directory = os.path.join(repo_root, input.directory_path)

    if not os.path.commonpath([repo_root, os.path.abspath(target_directory)]) == repo_root:
        raise ValueError("Directory path is outside the repository.")

    if os.path.exists(target_directory):
        raise FileExistsError(f"Directory '{input.directory_path}' already exists.")

    os.makedirs(target_directory, exist_ok=True)

    return f"Directory '{input.directory_path}' created successfully."


# 4. Search in Files
class SearchInFilesInput(BaseModel):
    search_text: str = Field(description="The text or regex pattern to search for.")
    file_paths: Optional[list[str]] = Field(
        default=None,
        description="list of file paths to search in. If not provided, searches all files in the repository.",
    )
    use_regex: bool = Field(
        default=False, description="Set to True to interpret 'search_text' as a regular expression."
    )
    case_sensitive: bool = Field(default=True, description="Set to False for case-insensitive search.")


def search_in_files(input: SearchInFilesInput) -> dict[str, list[int]]:
    """
    Searches for 'search_text' in specified files and returns a dictionary with file paths and line numbers of matches.
    """
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()

    matched_files = {}
    if input.file_paths:
        files_to_search = [os.path.join(repo_root, path) for path in input.file_paths]
    else:
        # Get all files in the repo
        files_to_search = []
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]
            for file in files:
                files_to_search.append(os.path.join(root, file))

    for file_path in files_to_search:
        if not os.path.commonpath([repo_root, os.path.abspath(file_path)]) == repo_root:
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
                relative_path = os.path.relpath(file_path, repo_root)
                matched_files[relative_path] = matched_lines

    return matched_files  # Returns a dict with file paths and lists of matching line numbers


class ListFilesInput(BaseModel):
    recursive: bool = Field(default=False, description="Set to True to list files recursively.")
    path: Optional[str] = Field(default=None, description="Sub-path within the repository to list files from.")


def list_files(input: ListFilesInput) -> List[str]:
    # Get the root of the git repository
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
    target_path = os.path.join(repo_root, input.path) if input.path else repo_root

    # Verify the target path is within the repo to avoid unintended access
    if not os.path.commonpath([repo_root, os.path.abspath(target_path)]) == repo_root:
        raise ValueError("Path is outside the repository.")

    # Build the git command
    git_command = ["git", "ls-files"]
    if not input.recursive:
        # Non-recursive; restrict to the specified directory only
        git_command.extend(["--directory", target_path])
    else:
        # Recursive; start from target path (Git is recursive by default here)
        git_command.append(target_path)

    # Run the git command to get only tracked files and directories
    try:
        tracked_files = subprocess.check_output(git_command, cwd=repo_root).decode().splitlines()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error executing git command: {e}")

    # Filter output based on recursive mode
    if input.recursive:
        # Recursive: only list files
        tracked_files = [f for f in tracked_files if not f.endswith("/")]
    else:
        # Non-recursive: include both files and directories at the specified level
        tracked_files = [f + "/" if os.path.isdir(os.path.join(repo_root, f)) else f for f in tracked_files]

    return tracked_files


# 5. Read File with Line Numbers
class ReadFileInput(BaseModel):
    file_path: str = Field(description="Path to the file within the repository.")


def read_file(input: ReadFileInput) -> list[str]:
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
    target_file = os.path.join(repo_root, input.file_path)

    if not os.path.isfile(target_file):
        raise FileNotFoundError("The specified file does not exist.")

    if not os.path.commonpath([repo_root, os.path.abspath(target_file)]) == repo_root:
        raise ValueError("File is outside the repository.")

    with open(target_file, "r") as f:
        lines = f.readlines()

    # Return lines with line numbers
    return [f"{idx + 1}: {line.rstrip()}" for idx, line in enumerate(lines)]


# 6. Write New File
class WriteFileInput(BaseModel):
    file_path: str = Field(description="Path where the new file will be created.")
    content: str = Field(description="Content to write into the new file.")


def write_file(input: WriteFileInput) -> str:
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
    target_file = os.path.join(repo_root, input.file_path)

    if os.path.exists(target_file):
        raise FileExistsError("File already exists.")

    if not os.path.commonpath([repo_root, os.path.abspath(target_file)]) == repo_root:
        raise ValueError("File path is outside the repository.")

    # Ensure the directory exists
    os.makedirs(os.path.dirname(target_file), exist_ok=True)

    with open(target_file, "w") as f:
        f.write(input.content)

    return f"File {input.file_path} created successfully."


# 7. Edit Existing File
class EditFileInput(BaseModel):
    file_path: str = Field(description="Path to the file to edit.")
    start_line: int = Field(description="Starting line number for the edit.")
    end_line: int = Field(description="Ending line number for the edit.")
    replacement_text: str = Field(description="Text to replace between the specified lines.")


def edit_file(input: EditFileInput) -> str:
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
    target_file = os.path.join(repo_root, input.file_path)

    if not os.path.isfile(target_file):
        raise FileNotFoundError("The specified file does not exist.")

    if not os.path.commonpath([repo_root, os.path.abspath(target_file)]) == repo_root:
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
class AddToFileInput(BaseModel):
    file_path: str = Field(description="Path to the file to add content to.")
    content: str = Field(description="Content to add to the file.")
    insert_at_line: Optional[int] = Field(
        default=None, description="Line number to insert the content at. If not provided, appends to the end."
    )


def add_to_file(input: AddToFileInput) -> str:
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
    target_file = os.path.join(repo_root, input.file_path)

    if not os.path.isfile(target_file):
        raise FileNotFoundError("The specified file does not exist.")

    if not os.path.commonpath([repo_root, os.path.abspath(target_file)]) == repo_root:
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

    return f"Content added to {input.file_path} successfully."


# 9. Delete File
class DeleteFileInput(BaseModel):
    file_path: str = Field(description="Path to the file to delete.")


def delete_file(input: DeleteFileInput) -> str:
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
    target_file = os.path.join(repo_root, input.file_path)

    if not os.path.isfile(target_file):
        raise FileNotFoundError("The specified file does not exist.")

    if not os.path.commonpath([repo_root, os.path.abspath(target_file)]) == repo_root:
        raise ValueError("File is outside the repository.")

    os.remove(target_file)

    return f"File {input.file_path} deleted successfully."


# 10. Move or Copy File
class MoveFileInput(BaseModel):
    source_path: str = Field(description="Current path of the file.")
    destination_path: str = Field(description="New path for the file.")
    copy_file: bool = Field(default=False, description="Set to True to copy the file instead of moving it.")


def move_file(input: MoveFileInput) -> str:
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
    source_file = os.path.join(repo_root, input.source_path)
    dest_file = os.path.join(repo_root, input.destination_path)

    if not os.path.isfile(source_file):
        raise FileNotFoundError("The source file does not exist.")

    if not os.path.commonpath([repo_root, os.path.abspath(dest_file)]) == repo_root:
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


# get_ai_tools function
def get_ai_tools() -> list[AgentTool]:
    return [
        AgentTool(
            name=ListFilesInput.__name__,
            params_model=ListFilesInput,
            mechanism=list_files,
            safe_tool=True,
        ),
        AgentTool(
            name=ReadFileInput.__name__,
            params_model=ReadFileInput,
            mechanism=read_file,
            safe_tool=True,
        ),
        AgentTool(
            name=ReplaceTextInput.__name__,
            params_model=ReplaceTextInput,
            mechanism=replace_text_in_files,
            safe_tool=False,
        ),
        AgentTool(
            name=CheckFileExistenceInput.__name__,
            params_model=CheckFileExistenceInput,
            mechanism=check_file_existence,
            safe_tool=True,
        ),
        AgentTool(
            name=CreateDirectoryInput.__name__,
            params_model=CreateDirectoryInput,
            mechanism=create_directory,
            safe_tool=True,
        ),
        # AgentTool(
        #     name=SearchInFilesInput.__name__,
        #     params_model=SearchInFilesInput,
        #     mechanism=search_in_files,
        #     safe_tool=True,
        # ),
        AgentTool(
            name=WriteFileInput.__name__,
            params_model=WriteFileInput,
            mechanism=write_file,
            safe_tool=False,
        ),
        AgentTool(
            name=EditFileInput.__name__,
            params_model=EditFileInput,
            mechanism=edit_file,
            safe_tool=False,
        ),
        AgentTool(
            name=AddToFileInput.__name__,
            params_model=AddToFileInput,
            mechanism=add_to_file,
            safe_tool=False,
        ),
        AgentTool(
            name=DeleteFileInput.__name__,
            params_model=DeleteFileInput,
            mechanism=delete_file,
            safe_tool=False,
        ),
        AgentTool(
            name=MoveFileInput.__name__,
            params_model=MoveFileInput,
            mechanism=move_file,
            safe_tool=False,
        ),
    ]
