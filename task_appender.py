#!/usr/bin/env python3
"""Compatibility wrapper for the new taskmgr package."""

from taskmgr.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
