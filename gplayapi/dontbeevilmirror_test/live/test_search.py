from contextlib import contextmanager
import json
import os
import pathlib
import shutil
import unittest

from dontbeevilmirror.api import GooglePlay


@contextmanager
def telemetry(name):
    telemetry = []
    had_exception = False
    try:
        yield lambda key, fmt, val: telemetry.append((key, fmt, val))
    except Exception:
        had_exception = True
        raise
    finally:
        if had_exception or os.environ.get("FORCE_TELEMETRY") == "1":
            d = pathlib.Path(".test_telemetry") / name
            try:
                shutil.rmtree(d)
            except FileNotFoundError:
                pass
            d.mkdir(parents=True, exist_ok=True)
            for idx, (key, fmt, val) in enumerate(telemetry):
                if fmt == "json":
                    val = json.dumps(val, indent=2) + "\n"
                fname = d / f"{idx:03d}_{key}.{fmt}"
                with open(fname, "w") as f:
                    f.write(val)
                print(
                    f"note: telemetry data written to {fname} for debugging (due to exception: {had_exception})"
                )


class TestSearch(unittest.TestCase):
    def test_searches_do_not_crash(self):
        g = GooglePlay()
        for query in (
            "bandcamp",
            "youtube",
            "tasker",
            "clock",
            "files",
            "messaging",
        ):
            with self.subTest(query):
                with telemetry(f"search_{query}") as tel:
                    results = g.search(query, _telemetry=tel)
                    self.assertGreaterEqual(len(results), 1)
                    print(query, [result.id for result in results[:3]])


if __name__ == "__main__":
    unittest.main()
