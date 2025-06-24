import asyncio
import os
from functools import wraps
from typing import Literal

import fire
from watchfiles import awatch

from .genai_utils import extract_queck
from .live_server import LiveServer
from .queck_models import Queck


class QueckCli:
    """A CLI tool for Quiz Validation and Exporting.

    Provides options to validate and export quizzes defined in YAML format.
    """

    def format(self, *queck_files):
        """Formats the queck file."""
        for queck_file in queck_files:
            Queck.read_queck(queck_file, format_md=True, round_trip=True).to_queck(
                queck_file
            )

    @staticmethod
    @wraps(extract_queck)
    def extract(file_name, model, prompt_extra, force_single_select, output_file):
        extract_queck(
            file_name=file_name,
            model=model,
            prompt_extra=prompt_extra,
            force_single_select=force_single_select,
            output_file=output_file or file_name,
        )

    def export(
        self,
        *queck_files,
        format: Literal["html", "md", "json"] = "html",
        output_dir="export",
        render_mode: Literal["fast", "latex", "inline"] = "fast",
        overview=False,
        render_json=False,
        parsed=False,
        watch=False,
        kwargs: dict | None = {},
    ):
        """Export queck (YAML) files into the specified .

        Args:
            queck_files (list[str]): List of queck (YAML) files to be exported.
            format (Literal['html','md','json']): Output format
            output_dir (str) : Output dir path
            render_mode (Literal['fast','latex','inline']) : Rendering mode
            overview (bool): Whether to add overview section
            render_json (bool): Whether to render markdown to html in json
            parsed (bool): Whether to add parsed choices
            watch (bool): Enable watch mode to monitor changes in files
            kwargs (dict|None) : Other configs passed to Queck export
        Returns:
            None
        """
        kwargs = kwargs or {}
        if watch:
            # Run the file watcher asynchronously to monitor file changes
            self.export(
                *queck_files,
                output_dir=output_dir,
                format=format,
                overview=overview,
                render_mode=render_mode,
                render_json=render_json,
                parsed=parsed,
                **kwargs,
            )
            asyncio.run(
                self._watch_and_export(
                    *queck_files,
                    output_dir=output_dir,
                    format=format,
                    overview=overview,
                    render_mode=render_mode,
                    render_json=render_json,
                    parsed=parsed,
                    **kwargs,
                )
            )
        else:
            # Export files without watching for changes
            for yaml_file in queck_files:
                try:
                    print(f"Rendering {yaml_file}...")
                    current_dir = os.path.abspath(os.curdir)
                    yaml_file = os.path.abspath(yaml_file)
                    output_file = os.path.join(
                        output_dir, os.path.relpath(yaml_file, current_dir)
                    )
                    output_file = os.path.splitext(output_file)[0] + f".{format}"
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)

                    try:
                        Queck.read_queck(yaml_file).export(
                            output_file=output_file,
                            format=format,
                            render_mode=render_mode,
                            overview=overview,
                            render_json=render_json,
                            parsed=parsed,
                            **kwargs,
                        )
                    except ValueError:
                        raise ValueError(
                            f"{yaml_file} is not valid "
                            "queck file. Please fix the errors."
                        )
                except Exception as e:
                    print(e)

    async def _watch_and_export(
        self, *queck_files, output_dir, format, render_mode, **kwargs
    ):
        print("Watching for changes...")
        print(queck_files)
        if format == "html":
            self.live_server = LiveServer(output_dir)
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
                output_dir=output_dir,
                format=format,
                render_mode=render_mode,
                **kwargs,
            )
            if format == "html":
                await self.live_server.send_reload_signal()


def main():
    # Fire the CLI with the Queck class
    fire.Fire(QueckCli())


if __name__ == "__main__":
    main()
