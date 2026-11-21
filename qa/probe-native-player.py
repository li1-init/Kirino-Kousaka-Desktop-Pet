"""Read the native pet timeline from the installed Windows app, without changing it."""

import argparse
import json
import struct
import subprocess
from pathlib import Path


def read_renderer(asar):
    with asar.open("rb") as file:
        _, header_size, _, length = struct.unpack("<IIII", file.read(16))
        entry = json.loads(file.read(length))
        for part in "webview/assets/async/911644.2b086ab057.js".split("/"):
            entry = entry["files"][part]
        file.seek(8 + header_size + int(entry["offset"]))
        source = file.read(entry["size"]).decode("utf-8")
    start = source.index("let c=l.columns,p=[")
    end = source.index("function v(", start)
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asar", type=Path, help="Installed app.asar for Windows build 26.1117.3838.0")
    installed = parser.parse_args().asar
    checks = r"""
const assert = require('node:assert/strict');
const playing = m('running', false);
const idle = m('idle', false);
const looped = m('running', false, true);
assert.deepEqual(playing.frames.slice(playing.loopStartIndex), idle.frames);
assert.equal(looped.loopStartIndex, 0);
assert.ok(looped.frames.every(f => f.rowIndex === 7));
const runningMs = playing.frames.slice(0, playing.loopStartIndex).reduce((ms, frame) => ms + frame.frameDurationMs, 0);
console.log(JSON.stringify({
  nativeRunningMs: runningMs,
  remainderIsIdle: true,
  hostLoopFlagUsesRunningRowOnly: true,
}, null, 2));
"""
    subprocess.run(["node", "-e", "const l={columns:8};" + read_renderer(installed) + checks], check=True)


if __name__ == "__main__":
    main()
