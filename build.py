#!/usr/bin/env python3
"""Gera public/. Uso: python build.py  (env: PORTAL_BASE_URL para prévia, PORTAL_NOINDEX=1 para noindex global)"""
from pathlib import Path
from core.build import main
if __name__ == "__main__": main(Path(__file__).resolve().parent)
