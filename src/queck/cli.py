import os
import subprocess
import fire
import yaml
import asyncio
from typing import Literal
from watchfiles import awatch

from .quiz_models import Quiz
from .renderers import render_quiz
from .live_server import start_http_server, websocket_server, send_reload_signal


# Function to load and validate the quiz YAML file using Pydantic
def load_quiz(yaml_file):
    """
    Loads and validates the quiz YAML file.

    Args:
        yaml_file (str): Path to the YAML file.

    Returns:
        Quiz: Validated Quiz object if successful.

    Raises:
        ValidationError: if validation is not successfull
    """
    with open(yaml_file, "r") as f:
        return Quiz.model_validate(yaml.safe_load(f))


# Function to export the quiz into the required format (HTML or Markdown)
def export_file(
    yaml_file,
    output_file=None,
    format: Literal["html", "md"] = "html",
    render_mode: Literal["fast", "compat"] = "fast",
):
    """
    Exports the quiz file to the required format.

    Args:
        yaml_file (str): Path to the quiz YAML file.
        format (str): Output format (html or md). Defaults to 'html'.
        render_mode (str): Rendering mode - 'fast' for KaTeX and HLJS, 'compat' for MathJax and Pygments.
        output_file (str): Output file path. Defaults to None.

    Returns:
        None
    """
    try:
        quiz = load_quiz(yaml_file)
    except:
        raise f"{yaml_file} is not valid Quiz YAML. Please fix the errors."

    # Write the rendered output to a file
    with open(output_file, "w") as f:
        f.write(render_quiz(quiz, format, render_mode))

    print(f"Quiz successfully exported to {output_file}")


class Queck:
    """
    A CLI tool for Quiz Validation and Exporting.

    Provides options to validate and export quizzes defined in YAML format.
    """

    def __init__(self):
        # Function to convert quiz to JSON format
        self.tojson = lambda quiz: load_quiz(quiz).model_dump_json(indent=2)

    def export(
        self,
        *yaml_files,
        format: Literal["html", "md"] = "html",
        output_folder="export",
        render_mode: Literal["fast", "compat"] = "fast",
        watch=False,
    ):
        """
        Export YAML files into the specified format with optional live watching.

        Args:
            yaml_files (list): List of YAML files to be exported.
            format (str): Output format (html or md). Defaults to 'html'.
            output_folder (str): Output folder path. Defaults to 'exports'.
            render_mode (str): Rendering mode - 'fast' or 'compat'.
            watch (bool): Enable watch mode to monitor changes in files. Defaults to False.

        Returns:
            None
        """

        if watch:
            # Run the file watcher asynchronously to monitor file changes
            self.export(
                *yaml_files,
                output_folder=output_folder,
                format=format,
                render_mode=render_mode,
            )
            start_http_server(output_folder)
            asyncio.run(
                self._watch_and_export(yaml_files, output_folder, format, render_mode)
            )
        else:
            # Export files without watching for changes
            for yaml_file in yaml_files:
                try:
                    print(f"Rendering {yaml_file}...")
                    current_dir = os.path.abspath(os.curdir)
                    yaml_file = os.path.abspath(yaml_file)
                    output_file = os.path.join(
                        output_folder, os.path.relpath(yaml_file, current_dir)
                    )
                    output_file = os.path.splitext(output_file)[0] + f".{format}"
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)

                    export_file(
                        yaml_file,
                        format=format,
                        output_file=output_file,
                        render_mode=render_mode,
                    )
                except Exception as e:
                    print(e)

    async def _watch_and_export(self, yaml_files, output_folder, format, render_mode):
        """
        Watches for changes in the specified files and re-exports them upon changes.

        Args:
            yaml_files (list): List of YAML files to be monitored and exported.
            format (str): Output format (html or md).
            output_file (str): Output file path.
            render_mode (str): Rendering mode - 'fast' or 'compat'.

        Returns:
            None
        """
        print("Watching for changes...")
        print(yaml_files)
        ws_server_task = asyncio.create_task(websocket_server())

        async for changes in awatch(*yaml_files):
            # On detecting a file change, re-export the YAML files
            files_changed = [yaml_file for change, yaml_file in changes]
            print(
                "Dected changes:",
                *(f"  - {file_name}" for file_name in files_changed),
                sep="\n",
            )
            self.export(
                *files_changed,
                output_folder=output_folder,
                format=format,
                render_mode=render_mode,
            )
            await send_reload_signal()
        await ws_server_task

def main():
    # Fire the CLI with the Queck class
    fire.Fire(Queck)


if __name__ == "__main__":
    main()
