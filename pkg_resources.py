"""
Compatibility shim for environments where `setuptools` is unavailable.

drf-yasg depends on `pkg_resources`; we re-export the bundled copy that ships
with pip so imports continue to work without installing setuptools from PyPI.
"""

from pip._vendor.pkg_resources import *  # noqa:F401,F403
