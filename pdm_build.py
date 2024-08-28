# Wheel Setup Script for generating metadata
#
# Copyright (C) 2023 Eric Callahan <arksine.code@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

from __future__ import annotations
import pathlib
import subprocess
import shlex
import json
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pdm.backend.hooks.base import Context

__package_name__ = "moonraker"
__dependencies__ = "scripts/system-dependencies.json"

def _run_git_command(cmd: str) -> str:
    prog = shlex.split(cmd)
    process = subprocess.Popen(
        prog, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    ret, err = process.communicate()
    retcode = process.wait()
    if retcode == 0:
        return ret.strip().decode()
    return ""

def get_commit_sha(source_path: pathlib.Path) -> str:
    cmd = f"git -C {source_path} rev-parse HEAD"
    return _run_git_command(cmd)

def retrieve_git_version(source_path: pathlib.Path) -> str:
    cmd = f"git -C {source_path} describe --always --tags --long --dirty"
    return _run_git_command(cmd)


def pdm_build_clean(context: Context) -> None:
    share_path: pathlib.Path = context.root.joinpath("share")
    if share_path.exists():
        shutil.rmtree(str(share_path))

def pdm_build_initialize(context: Context) -> None:
    context.ensure_build_dir()
    proj_name: str = context.config.metadata['name']
    build_dir = pathlib.Path(context.build_dir)
    pkg_path = build_dir.joinpath(__package_name__)
    pkg_path.mkdir(parents=True, exist_ok=True)
    rinfo_path: pathlib.Path = pkg_path.joinpath("release_info")
    rinfo_data: str = ""
    if context.root.joinpath(".git").exists():
        build_ver: str = context.config.metadata['version']
        build_time = datetime.now(timezone.utc)
        urls: Dict[str, str] = context.config.metadata['urls']
        release_info: Dict[str, Any] = {
            "project_name": proj_name,
            "package_name": __package_name__,
            "urls": {key.lower(): val for key, val in urls.items()},
            "package_version": build_ver,
            "git_version": retrieve_git_version(context.root),
            "commit_sha": get_commit_sha(context.root),
            "build_time": datetime.isoformat(build_time, timespec="seconds")
        }
        if __dependencies__:
            deps = pathlib.Path(context.root).joinpath(__dependencies__)
            if deps.is_file():
                dep_info: Dict[str, Any] = json.loads(deps.read_bytes())
                release_info["system_dependencies"] = dep_info
        # Write the release info to both the package and the data path
        rinfo_data = json.dumps(release_info, indent=4)
        rinfo_path.write_text(rinfo_data)
    else:
        rinfo_path = context.root.joinpath(f"{proj_name}/release_info")
        if rinfo_path.is_file():
            rinfo_data = rinfo_path.read_text()
        else:
            rinfo_data = ""
    git_ignore = build_dir.joinpath(".gitignore")
    if git_ignore.is_file():
        git_ignore.unlink()

def pdm_build_finalize(context: Context, artifact: pathlib.Path) -> None:
    share_path: pathlib.Path = context.root.joinpath("share")
    if share_path.exists():
        shutil.rmtree(str(share_path))
