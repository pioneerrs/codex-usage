import json
import tempfile
import unittest
from pathlib import Path

from codex_usage.errors import UsageError
from codex_usage.storage import (
    append_group,
    find_group,
    init_storage,
    load_config,
    load_groups,
    read_jsonl,
)


class StorageTests(unittest.TestCase):
    def test_init_storage_preserves_existing_config_and_appends_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            init_storage(data_dir)
            config_path = data_dir / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["defaultLanguage"] = "zh"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            init_storage(data_dir)
            append_group(data_dir, {"id": "tg_1", "name": "alpha"})

            self.assertEqual(load_config(data_dir)["defaultLanguage"], "zh")
            self.assertEqual(load_groups(data_dir), [{"id": "tg_1", "name": "alpha"}])

    def test_read_jsonl_reports_damaged_lines_with_file_and_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.jsonl"
            path.write_text('{"ok": true}\nnot-json\n', encoding="utf-8")

            with self.assertRaisesRegex(UsageError, r"broken\.jsonl.*line at 2"):
                read_jsonl(path)

    def test_find_group_requires_id_when_name_is_ambiguous(self):
        groups = [
            {"id": "tg_1", "name": "alpha"},
            {"id": "tg_2", "name": "alpha"},
        ]

        self.assertEqual(find_group(groups, "tg_2")["id"], "tg_2")
        with self.assertRaisesRegex(UsageError, "ambiguous"):
            find_group(groups, "alpha")
        with self.assertRaisesRegex(UsageError, "was not found"):
            find_group(groups, "missing")


if __name__ == "__main__":
    unittest.main()
