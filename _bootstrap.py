import subprocess
import sys
import os
import tempfile

packages = ["rich"]

extra = []
nexus = os.environ.get("PIP_INDEX_URL", "")
if nexus:
    parts = nexus.split("/")
    nexus_host = parts[2] if len(parts) > 2 else nexus
    extra = ["--index-url", nexus, "--trusted-host", nexus_host]

cmd = [sys.executable, "-m", "pip", "install"] + packages + extra + [
    "--quiet", "--no-input", "--disable-pip-version-check"
]

with open(os.devnull, "w") as devnull:
    result = subprocess.run(cmd, stdout=devnull, stderr=devnull)

sys.exit(0)
