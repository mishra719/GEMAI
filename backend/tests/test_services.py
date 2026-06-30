import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.services import gemini
from app.services.zip import create_project_zip, normalize_project_data


class FakeImageResponse:
    def __init__(self, image_bytes: bytes, content_type: str = "image/png"):
        self._image_bytes = image_bytes
        self.headers = {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._image_bytes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ZipServiceTests(unittest.TestCase):
    def test_normalize_project_data_accepts_array_files(self):
        project_data = {
            "project_name": "demo",
            "files": [
                {"path": "src/main.py", "content": "print('hi')"},
                {"name": "README.md", "content": "# Demo"},
            ],
        }

        normalized = normalize_project_data(project_data)

        self.assertEqual(normalized["project_name"], "demo")
        self.assertEqual(
            normalized["files"],
            {
                "src/main.py": "print('hi')",
                "README.md": "# Demo",
            },
        )

    def test_create_project_zip_writes_all_normalized_files(self):
        project_data = {
            "project_name": "demo",
            "files": [
                {"path": "src/main.py", "content": "print('hi')"},
                {"name": "README.md", "content": "# Demo"},
            ],
        }

        zip_buffer = create_project_zip(project_data)

        self.assertIsNotNone(zip_buffer)
        with zipfile.ZipFile(zip_buffer) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                ["demo/README.md", "demo/src/main.py"],
            )
            self.assertEqual(
                archive.read("demo/src/main.py").decode("utf-8"),
                "print('hi')",
            )

    def test_create_project_zip_skips_traversal_and_drive_paths(self):
        project_data = {
            "project_name": "demo",
            "files": {
                "../secret.txt": "nope",
                "src/../escape.py": "nope",
                "C:/windows/system32.txt": "nope",
                "src/app.py": "print('safe')",
            },
        }

        zip_buffer = create_project_zip(project_data)

        self.assertIsNotNone(zip_buffer)
        with zipfile.ZipFile(zip_buffer) as archive:
            self.assertEqual(archive.namelist(), ["demo/src/app.py"])

    def test_create_project_zip_decodes_common_escaped_source_text(self):
        project_data = {
            "project_name": "demo",
            "files": {
                "package.json": '{\\n  "name": "demo"\\n}',
                "src/app.js": 'console.log(\\"hello\\");\\nconsole.log(\\"world\\");',
            },
        }

        zip_buffer = create_project_zip(project_data)

        self.assertIsNotNone(zip_buffer)
        with zipfile.ZipFile(zip_buffer) as archive:
            self.assertEqual(
                archive.read("demo/package.json").decode("utf-8"),
                '{\n  "name": "demo"\n}',
            )
            self.assertEqual(
                archive.read("demo/src/app.js").decode("utf-8"),
                'console.log("hello");\nconsole.log("world");',
            )


class GeminiImageFallbackTests(unittest.TestCase):
    def test_pollinations_fallback_saves_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            fake_response = FakeImageResponse(b"fake-image-bytes", "image/png")

            with (
                patch("app.services.gemini.IMAGES_DIR", temp_path),
                patch("urllib.request.urlopen", return_value=fake_response),
            ):
                result = gemini._generate_image_with_pollinations("red robot")

            self.assertIsNotNone(result)
            self.assertEqual(result["type"], "image")
            self.assertTrue(result["image_url"].startswith("/static/images/"))
            self.assertEqual(len(list(temp_path.iterdir())), 1)


class GeminiCodingParsingTests(unittest.TestCase):
    def test_parse_code_response_repairs_unescaped_docstrings(self):
        broken_response = """```json
{
  "project_name": "python-notepad",
  "files": {
    "main.py": "class Notepad:\\n    def help(self):\\n        \"\"\"Show help\"\"\"\\n        print(\\"hello\\")",
    "README.md": "# Python Notepad\\n\\nSimple app"
  }
}
```"""

        parsed = gemini.parse_code_response(broken_response)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["project_name"], "python-notepad")
        self.assertIn('"""Show help"""', parsed["files"]["main.py"])
        self.assertEqual(parsed["files"]["README.md"], "# Python Notepad\n\nSimple app")


class UserSchemaTests(unittest.TestCase):
    def test_email_is_normalized_for_auth_payloads(self):
        from app.schemas.user import UserLogin, UserRegister

        register_payload = UserRegister(
            email="  STUDENT@Example.COM  ",
            password="Password1",
        )
        login_payload = UserLogin(
            email="  STUDENT@Example.COM  ",
            password="Password1",
        )

        self.assertEqual(register_payload.email, "student@example.com")
        self.assertEqual(login_payload.email, "student@example.com")


if __name__ == "__main__":
    unittest.main()
