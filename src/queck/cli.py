import asyncio
import os
from io import StringIO
from typing import Literal

import fire
from watchfiles import awatch

from .live_server import LiveServer
from .queck_models import Queck, yaml
from .utils import write_file

GENAI_ENABLED = True
try:
    from .extract import extract_queck
except ImportError:
    GENAI_ENABLED = False


class QueckCli:
    """A CLI tool for Quiz Validation and Exporting.

    Provides options to validate and export quizzes defined in YAML format.
    """

    def format(self, *queck_files):
        """Formats the queck file."""
        for queck_file in queck_files:
            Queck.read_queck(queck_file).to_queck(queck_file)

    def extract(self, file_name, model=None):
        """Extracts the questions as queck from the given file."""
        if GENAI_ENABLED:
            try:
                extract_queck(file_name, model).to_queck(file_name)
            except Exception as e:
                if hasattr(e, "quiz_dump"):
                    stream = StringIO()
                    yaml.dump(e.quiz_dump, stream=stream)
                    write_file(file_name, stream.getvalue(), format="queck")
                    print(stream.getvalue())
                raise e

        else:
            print(
                "optional genai features not enabled, "
                "install the package queck[genai] to avail this feature."
            )

    def export(
        self,
        *queck_files,
        format: Literal["html", "md", "json"] = "html",
        output_folder="export",
        render_mode: Literal["fast", "latex", "compat"] = "fast",
        watch=False,
    ):
        """Export queck (YAML) files into the specified .

        Args:
            queck_files : List of queck (YAML) files to be exported.
            format : Output format
            output_folder : Output folder path
            render_mode : Rendering mode
            watch : Enable watch mode to monitor changes in files

        Returns:
            None
        """
        if watch:
            # Run the file watcher asynchronously to monitor file changes
            self.export(
                *queck_files,
                output_folder=output_folder,
                format=format,
                render_mode=render_mode,
            )
            asyncio.run(
                self._watch_and_export(queck_files, output_folder, format, render_mode)
            )
        else:
            # Export files without watching for changes
            for yaml_file in queck_files:
                try:
                    print(f"Rendering {yaml_file}...")
                    current_dir = os.path.abspath(os.curdir)
                    yaml_file = os.path.abspath(yaml_file)
                    output_file = os.path.join(
                        output_folder, os.path.relpath(yaml_file, current_dir)
                    )
                    output_file = os.path.splitext(output_file)[0] + f".{format}"
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)

                    try:
                        Queck.read_queck(yaml_file).export(
                            output_file=output_file,
                            format=format,
                            render_mode=render_mode,
                        )
                    except ValueError:
                        raise ValueError(
                            f"{yaml_file} is not valid "
                            "queck file. Please fix the errors."
                        )
                except Exception as e:
                    print(e)

    async def _watch_and_export(self, queck_files, output_folder, format, render_mode):
        """Watches for changes in the specified files and re-exports them upon changes.

        Args:
            queck_files: List of YAML files to be monitored and exported.
            format: Output format (html or md).
            output_folder: Output folder path
            render_mode: Rendering mode - 'fast' or 'compat'.

        Returns:
            None
        """
        print("Watching for changes...")
        print(queck_files)
        if format == "html":
            self.live_server = LiveServer(output_folder)
            self.live_server.start()

        async for changes in awatch(*queck_files):
            # On detecting a file change, re-export the YAML files
            files_changed = [yaml_file for _, yaml_file in changes]
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
            if format == "html":
                await self.live_server.send_reload_signal()


def main():
    # Fire the CLI with the Queck class
    fire.Fire(QueckCli())


if __name__ == "__main__":
    main()
