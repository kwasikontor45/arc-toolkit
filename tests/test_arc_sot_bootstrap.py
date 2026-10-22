import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "bin" / "arc-sot"


class OfflineBootstrapTests(unittest.TestCase):
    def test_local_source_bootstraps_without_git_pull(self):
        with tempfile.TemporaryDirectory(prefix="arc-sot-bootstrap-") as temp:
            root = Path(temp)
            source = root / "source"
            (source / "bin").mkdir(parents=True)
            (source / "bin" / "perms.txt").write_text("755 sample-tool\n")
            tool = source / "bin" / "sample-tool"
            tool.write_text("#!/bin/sh\necho ready\n")
            tool.chmod(0o755)

            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(source), "-c", "user.name=Test", "-c",
                 "user.email=test@example.invalid", "commit", "-qm", "fixture"],
                check=True,
            )

            shim_dir = root / "shim"
            shim_dir.mkdir()
            pull_log = root / "pull-attempted"
            git_shim = shim_dir / "git"
            git_shim.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = pull ]; then\n"
                "  : > \"$ARC_SOT_PULL_MARKER\"\n"
                "  exit 97\n"
                "fi\n"
                "exec /usr/bin/git \"$@\"\n"
            )
            git_shim.chmod(0o755)

            home = root / "home"
            env = os.environ.copy()
            env.update({"HOME": str(home), "PATH": f"{shim_dir}:/usr/bin:/bin",
                        "ARC_SOT_PULL_MARKER": str(pull_log)})
            result = subprocess.run(
                ["bash", str(SCRIPT), "bootstrap", str(source)],
                env=env, text=True, capture_output=True, check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("local source selected; skipping network update", result.stdout)
            self.assertFalse(pull_log.exists(), "offline bootstrap attempted git pull")
            installed = home / ".local" / "bin" / "sample-tool"
            self.assertTrue(installed.is_symlink())
            self.assertEqual(installed.resolve(), home / "khaos-lab" / "local-cloud-hub" /
                             "apps" / "arc-toolkit" / "bin" / "sample-tool")
            self.assertEqual(subprocess.check_output([str(installed)], text=True).strip(), "ready")


if __name__ == "__main__":
    unittest.main()
