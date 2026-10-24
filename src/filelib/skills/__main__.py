"""Print the installed skills directory and the deployment-guide pointer.

Usage: ``python -m filelib.skills``
"""

from pathlib import Path

root = Path(__file__).parent.resolve()
print(root)
print(f"Deployment guide: {root / 'SKILL-DEPLOY.md'}")
