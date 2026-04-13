"""
Build script for Vault Analytics executable
"""
import PyInstaller.__main__
import os
import sys

# Change to vault_analytics directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PyInstaller.__main__.run([
    'main.py',
    '--name=VaultAnalytics',
    '--onefile',
    '--windowed',
    '--add-data=index.html;.',
    '--add-data=vault;vault',
    '--hidden-import=requests',
    '--hidden-import=urllib3',
    '--hidden-import=charset_normalizer',
    '--hidden-import=idna',
    '--hidden-import=certifi',
    '--hidden-import=packaging',
    '--hidden-import=packaging.version',
    '--hidden-import=packaging.specifiers',
    '--hidden-import=packaging.requirements',
    '--icon=NONE',
    '--clean',
    '--noconfirm',
])
