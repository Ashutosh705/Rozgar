#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root entrypoint delegating to scripts/fetch_all.py"""
import os
import sys

scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
sys.path.insert(0, scripts_dir)

from fetch_all import main

if __name__ == "__main__":
    main()
