"""Configuração comum de testes.

Garante que o diretório raiz do repositório entre no sys.path para permitir imports de `infra.*`.
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
