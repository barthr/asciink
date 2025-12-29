import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PIL.ImageFile import ImageFile
from rich.console import Console
from rich.terminal_theme import TerminalTheme
from rich.text import Text
from _image import InkyRenderer

INKY_IMPRESSION_73_2025 = TerminalTheme(
    foreground=(0, 0, 0),
    background=(255, 255, 255),
    normal=[
        (0, 0, 0),
        (160, 32, 32),
        (96, 128, 80),
        (240, 224, 80),
        (80, 128, 184),
        (160, 32, 32),
        (80, 128, 184),
        (255, 255, 255),
    ],
    bright=[
        (0, 0, 0),
        (160, 32, 32),
        (96, 128, 80),
        (240, 224, 80),
        (80, 128, 184),
        (160, 32, 32),
        (80, 128, 184),
        (255, 255, 255),
    ],
)

INKY_IMPRESSION_73_2025_DARK = TerminalTheme(
    foreground=(255, 255, 255),
    background=(0, 0, 0),
    normal=[
        (0, 0, 0),
        (160, 32, 32),
        (96, 128, 80),
        (240, 224, 80),
        (80, 128, 184),
        (160, 32, 32),
        (80, 128, 184),
        (255, 255, 255),
    ],
    bright=[
        (0, 0, 0),
        (160, 32, 32),
        (96, 128, 80),
        (240, 224, 80),
        (80, 128, 184),
        (160, 32, 32),
        (80, 128, 184),
        (255, 255, 255),
    ],
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="asciink, display any ansi input or image on an E-Ink screen",
        usage="""
asciink has 2 modes. It can automatically detect which mode to use.

Mode 1: When receiving raw bytes it will interpret this as ansi (shell) escape characters and convert the shell escape characters to an image which can be shown

Mode 2: When receiving an image it can automatically read the header (JPEG/PNG) and show it directly
on an E-Ink screen.""",
    )
    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Debug mode. Output image to a system image viewer",
    )
    parser.add_argument(
        "--image-path",
        type=Path,
        help="Path to storage of images",
        default="/tmp",
    )
    parser.add_argument("--font-size", type=float, default=12)
    parser.add_argument(
        "--columns", type=int, help="Set the amount of columns", default=100
    )
    parser.add_argument("--rows", type=int, help="Set the amount of rows", default=20)
    parser.add_argument(
        "--chromium-headless-shell-bin",
        type=Path,
        help="Chromium binary",
        default="chromium-headless-shell",
    )
    parser.add_argument(
        "--saturation", type=float, help="Set the saturation", default=0.6
    )
    parser.add_argument("--contrast", type=float, help="Set the contrast", default=1.4)

    args = parser.parse_args()

    stdin = sys.stdin.buffer.read()
    if len(stdin) == 0 or sys.stdin.isatty():
        parser.print_help()
        return 1

    image = is_image(stdin) or from_ansi(args, stdin.decode("utf-8", errors="replace"))

    if args.debug:
        image.show(title="Debug Output")
    else:
        renderer = InkyRenderer()
        renderer.render(image, saturation=args.saturation, contrast=args.contrast)
    return 0


def from_ansi(args: Namespace, stdin: str) -> ImageFile:
    console = Console(
        width=args.columns,
        height=args.rows,
        file=io.StringIO(),
        record=True,
        legacy_windows=False,
        safe_box=False,
    )
    console.print(Text.from_ansi(stdin), end="")

    with tempfile.NamedTemporaryFile(
        dir=args.image_path, suffix=".html", delete=False
    ) as src:
        console.save_html(
            path=src.name,
            theme=INKY_IMPRESSION_73_2025_DARK,
            inline_styles=False,
            code_format=preview(args.font_size),
        )

    output_png = args.image_path / "output.png"

    if not binary_exists(args.chromium_headless_shell_bin):
        raise Exception(
            f"Expected '{args.chromium_headless_shell_bin}' to be installed"
        )

    command = [
        args.chromium_headless_shell_bin,
        f"--screenshot={str(output_png)}",
        "--window-size=800,480",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--use-gl=swiftshader",
        "--hide-scrollbars",
        "--in-process-gpu",
        "--js-flags=--jitless",
        "--disable-zero-copy",
        "--disable-gpu-memory-buffer-compositor-resources",
        "--disable-extensions",
        "--disable-plugins",
        "--mute-audio",
        "--no-sandbox",
        f"file://{src.name}",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Check if the process failed or the output file is missing
    if result.returncode != 0 or not os.path.exists(output_png):
        raise Exception("Failed capturing screenshot")

    # Load the image using PIL
    image = Image.open(output_png).copy()
    # Remove image files
    os.remove(output_png)

    return image


def is_image(data: bytes) -> ImageFile | None:
    try:
        return Image.open(io.BytesIO(data))
    except UnidentifiedImageError:
        return None


def binary_exists(name: str) -> bool:
    return shutil.which(name) is not None


def preview(font_size: float) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
    body {{{{
        margin: 0;
        padding: 0;
        width: 800px;
        height: 480px;
        overflow: hidden;
    }}}}

    pre {{{{
        {{stylesheet}}
        color: {{foreground}};
        background-color: {{background}};
        font-size: {font_size}px;
        border: 1px solid black;
        margin: 0;
        padding: 2px;
        width: 800px;
        height: 480px;
    }}}}
    </style>
    </head>
    <body>
        <pre style="font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"><code style="font-family:inherit">{{code}}</code></pre>
    </body>
    </html>
    """


if __name__ == "__main__":
    sys.exit(main())
