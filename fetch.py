#!/usr/bin/env python3
"""Coleta RSS (sem IA). Uso: python fetch.py [--max N] [--dry-run] [--revisar [--remover]]"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
from core.fetch import main
if __name__ == "__main__": main()
