"""
PlatformIO build script to inject version info.
"""

import subprocess
import os

Import("env")

def get_git_version():
    """Get version from git tags/commits"""
    try:
        # Try to get tag
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--always"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return tag
    except:
        return "0.1.0-dev"

def get_build_time():
    """Get current build timestamp"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# Add version defines to build
version = get_git_version()
build_time = get_build_time()

env.Append(CPPDEFINES=[
    ("FIRMWARE_VERSION", f'\\"{version}\\"'),
    ("BUILD_TIME", f'\\"{build_time}\\"'),
])

print(f"Building firmware version: {version}")
