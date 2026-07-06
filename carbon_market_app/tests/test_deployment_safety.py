from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DeploymentSafetyTests(unittest.TestCase):
    def test_streamlit_app_and_docs_do_not_contain_windows_absolute_paths(self):
        checked_files = ["app.py", "data_loader.py", "exporter.py", "README.md"]
        pattern = re.compile(r"[A-Za-z]:\\")

        offenders = []
        for filename in checked_files:
            text = (PROJECT_ROOT / filename).read_text(encoding="utf-8")
            if pattern.search(text):
                offenders.append(filename)

        self.assertEqual(offenders, [])

    def test_app_uses_file_uploader_and_session_state_for_user_results(self):
        app_source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn("st.file_uploader", app_source)
        self.assertIn("st.session_state", app_source)
        self.assertNotIn("st.cache_data", app_source)

    def test_exporter_uses_in_memory_excel_buffer(self):
        exporter_source = (PROJECT_ROOT / "exporter.py").read_text(encoding="utf-8")

        self.assertIn("BytesIO", exporter_source)
        self.assertIn("pd.ExcelWriter(buffer", exporter_source)
        self.assertNotIn(".to_excel(", exporter_source.replace(".to_excel(writer", ""))


if __name__ == "__main__":
    unittest.main()
