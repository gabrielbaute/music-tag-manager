from rich.console import Console

from mtm.cli.cli_parser import create_parser
from mtm.cli.commands import (
    show_version,
    analyze_command,
    set_genres_to_album_command,
    swap_artists_command,
    force_album_artist_command,
    sanitize_command,
    fix_field_command,
)

def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    console = Console()

    if args.command == "version":
        show_version(console)

    elif args.command == "analyze":
        analyze_command(console, args)

    elif args.command == "genres":
        set_genres_to_album_command(console, args)

    elif args.command == "swap-artists":
        swap_artists_command(console, args)

    elif args.command == "force-album-artist":
        force_album_artist_command(console, args)

    elif args.command == "sanitize":
        sanitize_command(console, args)

    elif args.command == "fix-field":
        fix_field_command(console, args)

    else:
        parser.print_help()