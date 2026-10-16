import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'packaging/windows/close_running_app.ps1'


@unittest.skipUnless(os.name == 'nt', 'Windows process ownership integration')
class InstallerProcessCleanupTests(unittest.TestCase):
    def test_only_exact_installation_processes_are_stopped(self):
        compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        self.assertTrue(compiler.is_file())
        children = []
        with tempfile.TemporaryDirectory(prefix='nanfeng-close-test-') as directory:
            base = Path(directory)
            install = base / 'app'
            sibling = base / 'app-other'
            helper_path = install / '_internal/playwright/driver/node.exe'
            helper_path.parent.mkdir(parents=True)
            sibling.mkdir()
            executable = install / '南枫下载.exe'
            source = base / 'wait.cs'
            source.write_text('public static class WaitApp { public static void Main() { System.Threading.Thread.Sleep(120000); } }', encoding='utf-8')
            subprocess.run([str(compiler), '/nologo', '/target:exe', f'/out:{executable}', str(source)], check=True, capture_output=True)
            shutil.copyfile(executable, helper_path)
            decoy = sibling / executable.name
            shutil.copyfile(executable, decoy)
            try:
                children = [subprocess.Popen([str(p)], creationflags=subprocess.CREATE_NO_WINDOW) for p in (executable, helper_path, decoy)]
                command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(HELPER), '-InstallDirectory', str(install), '-GraceSeconds', '0']
                dry = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(json.loads(dry.stdout)['CandidateCount'], 2)
                self.assertTrue(all(p.poll() is None for p in children))
                applied = subprocess.run(command + ['-Apply'], check=True, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(json.loads(applied.stdout)['RemainingCount'], 0)
                for p in children[:2]:
                    p.wait(timeout=5)
                self.assertIsNone(children[2].poll(), 'same-name sibling must remain running')
            finally:
                for p in children:
                    if p.poll() is None:
                        p.terminate()
                    p.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
