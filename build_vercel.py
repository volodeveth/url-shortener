#!/usr/bin/env python
"""Build script for Vercel deployment"""
import os
import subprocess
import sys

def run_command(command):
    """Run a command and print output"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode

def main():
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

    # Collect static files
    print("=" * 50)
    print("Collecting static files...")
    print("=" * 50)
    run_command(f"{sys.executable} manage.py collectstatic --noinput")

    # Run migrations
    print("=" * 50)
    print("Running migrations...")
    print("=" * 50)
    exit_code = run_command(f"{sys.executable} manage.py migrate --noinput")

    if exit_code != 0:
        print("Warning: Migrations may have failed, but continuing...")

    print("=" * 50)
    print("Build complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()
