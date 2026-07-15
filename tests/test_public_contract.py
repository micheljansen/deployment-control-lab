import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class PublicRepositoryContractTests(unittest.TestCase):
    def published_text(self):
        roots = [ROOT / "README.md", ROOT / ".github", ROOT / "docs", ROOT / "scripts", ROOT / "tests"]
        parts = []
        for root in roots:
            paths = [root] if root.is_file() else sorted(root.rglob("*")) if root.exists() else []
            for path in paths:
                if path.is_file() and path.suffix not in {".pyc"}:
                    parts.append(path.read_text(encoding="utf-8"))
        return "\n".join(parts).lower()

    def test_published_files_contain_no_private_identifiers(self):
        forbidden = [
            "pim" + "today",
            "fr" + "oq",
            "new" + "pim",
            "atlass" + "ian",
            "ji" + "ra",
            "git" + "lab.com",
            "amazon" + "aws.com",
            "6644" + "18982869",
        ]
        text = self.published_text()
        for value in forbidden:
            with self.subTest(identifier=value):
                self.assertNotIn(value, text)

    def test_workflows_have_no_real_deployment_capability(self):
        text = "\n".join(path.read_text(encoding="utf-8") for path in WORKFLOWS.glob("*.yml"))
        forbidden = [
            r"aws-actions/",
            r"id-token\s*:\s*write",
            r"secrets\.",
            r"\bdocker\s+(?:image\s+)?push\b",
            r"\b(?:curl|wget|ssh)\b",
            r"\.dkr\.ecr\.",
        ]
        self.assertTrue(text)
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE))

    def test_native_environment_workflow_is_explicit(self):
        promotion = (WORKFLOWS / "promote-mock-release-candidate.yml").read_text(encoding="utf-8")
        self.assertIn("environment: ${{ inputs.environment }}", promotion)
        for environment in ("test", "uat", "production"):
            self.assertRegex(promotion, rf"(?m)^\s+- {environment}$")

    def test_only_official_pinned_actions_are_used(self):
        allowed = {"actions/checkout@v4", "actions/upload-artifact@v4"}
        used = set()
        for path in WORKFLOWS.glob("*.yml"):
            used.update(re.findall(r"uses:\s*([^\s]+)", path.read_text(encoding="utf-8")))
        self.assertEqual(allowed, used)

    def test_readme_explains_public_safety_and_native_gate(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        for value in ("public", "synthetic digest", "no secrets", "required reviewer", "self-review"):
            self.assertIn(value, readme)


if __name__ == "__main__":
    unittest.main()
