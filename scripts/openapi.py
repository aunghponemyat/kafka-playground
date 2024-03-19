import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from lts.main_routes import app


def main(dist_dir: str, file_name: str, file_formats: List[str]) -> None:
    #app: FastAPI = create_app()
    schema: Dict[str, Any] = app.openapi()

    for _format in file_formats:
        schema_file = Path(dist_dir) / f"{file_name}.{_format}"

        if _format == "yaml":
            yaml.dump(schema, open(schema_file, "w"), allow_unicode=True)
        elif _format == "json":
            json.dump(schema, open(schema_file, "w"), ensure_ascii=False, indent=4)


if __name__ == "__main__":
    args_parser = argparse.ArgumentParser(description="Generate OpenAPI Schema")
    args_parser.add_argument(
        "--dir", type=str, action="store", default=".", help="Output directory"
    )
    args_parser.add_argument(
        "--name", type=str, action="store", default="openapi", help="Schema file name"
    )
    args_parser.add_argument(
        "--yaml",
        dest="formats",
        action="append_const",
        const="yaml",
        help="Generate YAML format schema",
    )
    args_parser.add_argument(
        "--json",
        dest="formats",
        action="append_const",
        const="json",
        help="Generate JSON format schema",
    )
    args = args_parser.parse_args()

    if args.formats is None:
        args.formats = ["yaml"]

    main(args.dir, args.name, args.formats)
