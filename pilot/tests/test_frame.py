"""Result frame decoding (T023, contracts/worker-io.md)."""
import base64
import hashlib
import io
import tarfile
import unittest

from specfoundry_pilot import frame

REPORT = b'{"version": 1}'


class TestFrame(unittest.TestCase):
    def test_roundtrip(self):
        text = "noise before\n" + frame.encode({"report.json": REPORT, "change.bundle": b"\x00bin"}) + "after\n"
        files, err = frame.decode(text)
        self.assertIsNone(err)
        self.assertEqual(files["report.json"], REPORT)
        self.assertEqual(files["change.bundle"], b"\x00bin")

    def test_missing_begin(self):
        self.assertEqual(frame.decode("just logs\n"), (None, "no_result"))
        self.assertEqual(frame.decode(""), (None, "no_result"))

    def test_two_frames(self):
        f = frame.encode({"report.json": REPORT})
        self.assertEqual(frame.decode(f + f), (None, "bad_frame"))

    def test_begin_line_must_be_exact(self):
        f = frame.encode({"report.json": REPORT}).replace(frame.BEGIN, "PILOT-RESULT-BEGIN v2")
        self.assertEqual(frame.decode(f), (None, "no_result"))

    def test_sha_mismatch(self):
        lines = frame.encode({"report.json": REPORT}).splitlines()
        lines[-1] = frame.END_PREFIX + "0" * 64
        self.assertEqual(frame.decode("\n".join(lines) + "\n"), (None, "bad_frame"))

    def test_oversize(self):
        import os
        f = frame.encode({"report.json": REPORT, "big": os.urandom(frame.MAX_BYTES + 10)})
        self.assertEqual(frame.decode(f), (None, "oversize"))

    def test_missing_report(self):
        self.assertEqual(frame.decode(frame.encode({"change.bundle": b"x"})), (None, "bad_frame"))

    def test_required_override(self):
        files, err = frame.decode(frame.encode({"grade.json": b"{}"}), required=("grade.json",))
        self.assertIsNone(err)

    def test_path_traversal_rejected(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for name in ("report.json", "../evil"):
                info = tarfile.TarInfo(name); info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
        raw = buf.getvalue()
        text = f"{frame.BEGIN}\n{base64.encodebytes(raw).decode()}{frame.END_PREFIX}{hashlib.sha256(raw).hexdigest()}\n"
        self.assertEqual(frame.decode(text), (None, "bad_frame"))

    def test_text_after_end_ignored(self):
        f = frame.encode({"report.json": REPORT}) + "PILOT-RESULT-END sha256=deadbeef\n"
        # a second END after the frame makes the frame ambiguous -> rejected
        self.assertEqual(frame.decode(f), (None, "bad_frame"))
        files, err = frame.decode(frame.encode({"report.json": REPORT}) + "trailing log line\n")
        self.assertIsNone(err)


if __name__ == "__main__":
    unittest.main()
