#!/usr/bin/env python3
"""
KeyPick Quick Setup Script

This script helps with initial project setup using uv package manager.
Run: python setup.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, str(e)


def check_python_version():
    """Check if Python version is 3.12 or higher."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 12):
        print(f"❌ Python 3.12+ required, but found {version.major}.{version.minor}")
        print("   Please install Python 3.12 or higher")
        return False
    print(f"✅ Python {version.major}.{version.minor} detected")
    return True


def install_uv():
    """Install uv if not already installed."""
    if shutil.which("uv"):
        success, output = run_command("uv --version")
        print(f"✅ uv already installed: {output}")
        return True

    print("📦 Installing uv...")
    if sys.platform == "win32":
        cmd = 'powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
    else:
        cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"

    success, _ = run_command(cmd)
    if success:
        # Add to PATH for current session
        home = Path.home()
        uv_path = home / ".local" / "bin"
        if str(uv_path) not in os.environ["PATH"]:
            os.environ["PATH"] = f"{uv_path}:{os.environ['PATH']}"
        print("✅ uv installed successfully")
        return True
    else:
        print("❌ Failed to install uv")
        print("   Please install manually: https://github.com/astral-sh/uv")
        return False


def setup_environment():
    """Set up Python virtual environment and install dependencies."""
    print("\n🔧 Setting up Python environment...")

    # Create virtual environment
    if not Path(".venv").exists():
        print("   Creating virtual environment...")
        success, _ = run_command("uv venv --python 3.12")
        if not success:
            print("❌ Failed to create virtual environment")
            return False

    # Determine pip command based on OS
    if sys.platform == "win32":
        pip_cmd = ".venv\\Scripts\\python -m pip"
    else:
        pip_cmd = ".venv/bin/python -m pip"

    # Install dependencies
    print("   Installing dependencies...")
    success, _ = run_command(f"uv pip install -e '.[dev]'")
    if not success:
        print("❌ Failed to install dependencies")
        return False

    print("✅ Environment setup complete")
    return True


def setup_config():
    """Set up configuration files."""
    print("\n⚙️ Setting up configuration...")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("   ⚠️  Please edit .env file with your configuration:")
        print("      - Set KEYPICK_API_KEYS for API authentication")
        print("      - Configure Supabase credentials (optional)")
        print("      - Set Redis URL (optional)")
    elif env_file.exists():
        print("✅ .env file already exists")

    # Create logs directory
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir()
        print("✅ Created logs directory")

    return True


def check_redis():
    """Check if Redis is available."""
    print("\n🔍 Checking Redis...")

    if shutil.which("redis-cli"):
        success, _ = run_command("redis-cli ping", check=False)
        if success:
            print("✅ Redis is running")
        else:
            print("⚠️  Redis is installed but not running")
            print("   Start Redis for caching functionality")
    else:
        print("ℹ️  Redis not installed (optional)")
        print("   Install for better performance: brew install redis (macOS)")


def main():
    """Main setup function."""
    print("🚀 KeyPick Setup Script\n")

    # Check Python version
    if not check_python_version():
        return 1

    # Install uv
    if not install_uv():
        return 1

    # Setup environment
    if not setup_environment():
        return 1

    # Setup configuration
    if not setup_config():
        return 1

    # Check Redis
    check_redis()

    print("\n" + "="*50)
    print("✅ Setup complete!")
    print("="*50)
    print("\nTo start the API server:")
    print("  1. Activate environment: source .venv/bin/activate")
    print("  2. Run server: uvicorn api.main:app --reload")
    print("\nAPI documentation will be available at:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print("\nFor testing:")
    print("  - Run tests: pytest tests/")
    print("  - See test guide: tests/TEST_GUIDE.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())