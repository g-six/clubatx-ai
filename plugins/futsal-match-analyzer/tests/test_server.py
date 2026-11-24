import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SERVER = Path(__file__).resolve().parents[1] / "server/server.py"
spec = importlib.util.spec_from_file_location("futsal_server", SERVER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def data(result):
    return json.loads(result["content"][0]["text"])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="futsal-test-")
        cls.video = Path(cls.temp.name) / "match ü with spaces.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                        "testsrc2=size=640x360:rate=20:duration=4", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", str(cls.video)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.analyzer = module.Analyzer()
        self.metadata = data(self.analyzer.inspect_recording(str(self.video)))
        self.rid = self.metadata["recording_id"]

    def tearDown(self):
        for recording in self.analyzer.recordings.values():
            shutil.rmtree(recording["root"])

    def window(self, start=0, interval=0.25, count=8):
        return self.analyzer.review_window(self.rid, start, interval, count, 320)

    def event(self, wid, status="confirmed", timestamp=1):
        return {"timestamp_seconds": timestamp, "type": "shot", "status": status,
                "description": "Synthetic test observation; not a real sports event.",
                "team": "=not_a_formula", "evidence_window_ids": [wid]}

    def test_media_evidence_and_export(self):
        self.assertAlmostEqual(self.metadata["duration_seconds"], 4, places=1)
        result = self.window()
        window = data(result)
        wid = window["window_id"]
        self.assertEqual(result["content"][1]["mimeType"], "image/png")
        self.assertEqual(len(window["frames"]), 8)
        self.assertEqual(window["frames"][4]["seconds"], 1)
        self.assertTrue(Path(window["sheet_path"]).is_file())
        with self.assertRaisesRegex(ValueError, "reviewed windows"):
            self.analyzer.export_report(self.rid, [self.event(wid)], "Test")
        self.analyzer.mark_reviewed(wid, "Synthetic pattern inspected by test; no real match.")
        report = data(self.analyzer.export_report(self.rid, [self.event(wid)], "Synthetic pipeline test"))
        saved = json.loads(Path(report["paths"]["events.json"]).read_text())
        self.assertEqual(saved["coverage"]["sampled_span_percent"], 50)
        self.assertEqual(saved["coverage"]["unreviewed_spans"], [[2, 4]])
        self.assertIn("'=not_a_formula", Path(report["paths"]["events.csv"]).read_text())
        clip = data(self.analyzer.export_clip(self.rid, 0.5, 2.5))
        probe = json.loads(module.run(["ffprobe", "-v", "error", "-show_format", "-of", "json", clip["path"]]))
        self.assertAlmostEqual(float(probe["format"]["duration"]), 2, delta=0.15)

    def test_sparse_review_cannot_confirm_and_unseen_time_rejected(self):
        wid = data(self.window(interval=1, count=4))["window_id"]
        self.analyzer.mark_reviewed(wid, "Sparse screening")
        with self.assertRaisesRegex(ValueError, "4fps"):
            self.analyzer.export_report(self.rid, [self.event(wid)], "Test")
        with self.assertRaisesRegex(ValueError, "between actual evidence"):
            self.analyzer.export_report(self.rid, [self.event(wid, "candidate", 3.5)], "Test")
        self.analyzer.export_report(self.rid, [self.event(wid, "candidate")], "Test")

    def test_bounds_invalid_files_and_changed_recording(self):
        for kwargs in [{"start_seconds": -1}, {"start_seconds": 4},
                       {"start_seconds": 0, "count": 100},
                       {"start_seconds": 0, "interval_seconds": float("nan")},
                       {"start_seconds": 0, "width": 321}]:
            with self.assertRaises(ValueError):
                self.analyzer.review_window(self.rid, **kwargs)
        with self.assertRaises(ValueError):
            self.analyzer.inspect_recording("relative.mp4")
        # A read of the last decodable frame is clamped to the recording duration.
        tail = data(self.window(start=3.5, interval=0.25, count=24))
        self.assertEqual(len(tail["frames"]), 2)
        self.analyzer.mark_reviewed(tail["window_id"], "Tail")
        other = data(self.analyzer.inspect_recording(str(self.video)))["recording_id"]
        with self.assertRaisesRegex(ValueError, "reviewed windows"):
            self.analyzer.export_report(other, [self.event(tail["window_id"], "candidate", 3.5)], "Test")
        self.analyzer.recordings[self.rid]["fingerprint"] = (0, 0)
        with self.assertRaisesRegex(ValueError, "changed"):
            self.analyzer.recording(self.rid)

    def test_stdio_handshake_discovery_errors_and_media(self):
        proc = subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def send(message):
            proc.stdin.write(json.dumps(message) + "\n")
            proc.stdin.flush()
            return json.loads(proc.stdout.readline())
        def request(i, method, params=None):
            return send({"jsonrpc": "2.0", "id": i, "method": method, "params": params or {}})
        try:
            init = request(1, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})
            self.assertEqual(init["result"]["protocolVersion"], "2025-11-25")
            proc.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            proc.stdin.flush()
            listing = request(2, "tools/list")
            self.assertEqual(len(listing["result"]["tools"]), 5)
            self.assertIn("error", request(3, "not_a_method"))
            bad = request(4, "tools/call", {"name": "inspect_recording", "arguments": {"path": "missing.mp4"}})
            self.assertTrue(bad["result"]["isError"])
            inspected = request(5, "tools/call", {"name": "inspect_recording", "arguments": {"path": str(self.video)}})
            metadata = data(inspected["result"])
            reviewed = request(6, "tools/call", {"name": "review_window", "arguments": {"recording_id": metadata["recording_id"], "start_seconds": 0, "count": 2, "width": 320}})
            self.assertEqual(reviewed["result"]["content"][1]["type"], "image")
            shutil.rmtree(metadata["output_directory"])
            proc.stdin.close()
            proc.wait(timeout=10)
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stderr.read(), "")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            proc.stdout.close()
            proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
