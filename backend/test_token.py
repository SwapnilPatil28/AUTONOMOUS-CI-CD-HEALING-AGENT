import os
from pathlib import Path
from dotenv import load_dotenv

# Load from .env
env_path = Path('.').absolute() / '.env'
print(f"Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path)

token = os.getenv('GITHUB_TOKEN')
if token:
    print(f"✓ Token loaded: {token[:20]}...{token[-10:]}")
    print(f"  Full length: {len(token)} chars")
else:
    print("✗ No GITHUB_TOKEN found in environment")
