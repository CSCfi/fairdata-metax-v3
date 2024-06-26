# -*- coding: utf-8 -*-
"""
    Setup file for metax_service.
    Use setup.cfg to configure your project.

    This file was generated with PyScaffold 3.3.1.
    PyScaffold helps you to put up the scaffold of your new Python project.
    Learn more under: https://pyscaffold.org/
"""
from setuptools import setup

if __name__ == "__main__":
    try:
        setup(use_scm_version={"version_scheme": "post-release"})
    except:  # noqa
        print(
            "\n\nAn error occurred while building the project, "
            "please ensure you have the most updated version of setuptools with: "
            "`pip install -U setuptools`\n\n"
        )
        raise
