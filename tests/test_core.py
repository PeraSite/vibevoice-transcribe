import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from pi_vibevoice_transcribe import (
    choose_mix,
    convert,
    localize_events,
    render_draft,
    select_media,
    timestamp,
)


class CoreTests(unittest.TestCase):
    def test_formatting_and_mix_selection(self):
        self.assertEqual(choose_mix(-21.2, -75.7), "left")
        self.assertEqual(choose_mix(-75.7, -21.2), "right")
        self.assertEqual(choose_mix(-30, -38), "stereo")
        self.assertEqual(timestamp(3661.9), "01:01:01")
        self.assertEqual(
            localize_events("[Cough][Unintelligible Speech]"),
            "[기침][알아들을 수 없는 말]",
        )

    def test_render_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.json"
            draft = root / "draft.txt"
            raw.write_text(json.dumps({"segments": [
                {"start": 1.9, "speaker_id": 0, "text": "안녕하세요."},
                {"start": 3, "text": "[Silence]"},
            ]}))
            render_draft(raw, draft)
            self.assertEqual(
                draft.read_text(),
                "[00:00:01] [화자 1] 안녕하세요.\n[00:00:03] [비언어음] [침묵]\n",
            )

    def test_top_level_selection_and_duplicate_stems(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "C0001.MP4").touch()
            (root / "nested").mkdir()
            (root / "nested/C0002.MP4").touch()
            self.assertEqual(select_media(root, ["C0*.MP4"]), [root / "C0001.MP4"])
            (root / "C0001.mov").touch()
            with self.assertRaisesRegex(ValueError, "duplicate stems"):
                select_media(root, ["C0*.MP4", "C0*.mov"])

    def test_channel_aware_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "stereo.wav"
            target = root / "mono.flac"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=44100",
                "-filter_complex", "[0:a][1:a]join=inputs=2:channel_layout=stereo[a]",
                "-map", "[a]", "-t", "1", str(source),
            ], check=True)
            analysis = convert(source, target)
            self.assertEqual(analysis["mix"], "left")
            self.assertTrue(target.is_file() and target.stat().st_size)


if __name__ == "__main__":
    unittest.main()
