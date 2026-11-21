"""Read the native pet timeline from the installed Windows app, without changing it."""

import argparse
import json
import re
import struct
import subprocess
from pathlib import Path


OVERLAY_CALL = re.compile(
    rb'\.bH,\{(?=[^}]{0,350}className:"codex-avatar-root\b)(?=[^}]{0,350}\bstate:)[^}]+\}'
)


def inspect_renderer(asar):
    with asar.open("rb") as file:
        _, header_size, _, length = struct.unpack("<IIII", file.read(16))
        directory = json.loads(file.read(length))
        for part in ("webview", "assets", "async"):
            directory = directory["files"][part]
        timeline = None
        calls = []
        for name, entry in directory["files"].items():
            if not name.endswith(".js") or "offset" not in entry:
                continue
            file.seek(8 + header_size + int(entry["offset"]))
            source = file.read(entry["size"])
            begin = source.find(b"let c=l.columns,p=[")
            if begin >= 0:
                end = source.index(b"function v(", begin)
                timeline = source[begin:end].decode("utf-8")
            for match in OVERLAY_CALL.finditer(source):
                props = match.group()
                loop = re.search(rb"\bloop:([^},]+)", props)
                calls.append({"chunk": name, "loop": loop[1].decode("ascii") if loop else None})
    if timeline is None or not calls:
        raise ValueError("Installed renderer does not match the known layout. Recheck the new build before drawing conclusions.")
    return timeline, calls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asar", type=Path, help="Installed app.asar. See the handoff document for tested builds.")
    installed = parser.parse_args().asar
    timeline, calls = inspect_renderer(installed)
    checks = r"""
const assert = require('node:assert/strict');
const playing = m('running', false);
const idle = m('idle', false);
const looped = m('running', false, true);
assert.equal(looped.loopStartIndex, 0);
assert.ok(looped.frames.every(f => f.rowIndex === 7));
const runningMs = playing.frames.slice(0, playing.loopStartIndex).reduce((ms, frame) => ms + frame.frameDurationMs, 0);
function rowAt(schedule, elapsed) {
  const total = (frames) => frames.reduce((ms, frame) => ms + frame.frameDurationMs, 0);
  const elapsedBeforeLoop = total(schedule.frames.slice(0, schedule.loopStartIndex));
  if (elapsed >= elapsedBeforeLoop) {
    elapsed = elapsedBeforeLoop + (elapsed - elapsedBeforeLoop) %
      total(schedule.frames.slice(schedule.loopStartIndex));
  }
  return schedule.frames.find((frame) => (elapsed -= frame.frameDurationMs) < 0).rowIndex;
}
const samples = [0, runningMs - 1, runningMs, 60_000, 65_000, 250_000]
  .filter((ms) => ms >= 0)
  .map((ms) => ({ms, defaultRow: rowAt(playing, ms), continuousRow: rowAt(looped, ms)}));
assert.ok(samples.every((sample) => sample.continuousRow === 7));
console.log(JSON.stringify({
  nativeRunningMs: runningMs,
  remainderIsIdle: JSON.stringify(playing.frames.slice(playing.loopStartIndex)) === JSON.stringify(idle.frames),
  hostLoopFlagUsesRunningRowOnly: true,
  desktopOverlayCalls,
  samples,
}, null, 2));
"""
    prefix = "const l={columns:8}; const desktopOverlayCalls=" + json.dumps(calls) + ";"
    subprocess.run(["node", "-e", prefix + timeline + checks], check=True)


if __name__ == "__main__":
    main()
