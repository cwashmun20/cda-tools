"""Setup script for cda-tools.

Packages the cda-core, flc-entry-checking, and flc-points modules.
Uses package_dir to map underscore import names to hyphenated directory paths.
"""

from setuptools import setup

setup(
    name="cda-tools",
    version="0.1.0",
    description="Fair Level Certification tools for the Collegiate Dancesport Association",
    author="Clifford Ashmun",
    author_email="cwashmun20@hmc.edu",
    python_requires=">=3.11",
    packages=[
        "cda_core",
        "cda_core.lib",
        "cda_core.lib.api",
        "cda_core.lib.models",
        "cda_core.lib.parsing",
        "cda_core.lib.rules",
        "flc_entry_checking",
        "flc_entry_checking.lib",
        "flc_points",
        "flc_points.lib",
    ],
    package_dir={
        "cda_core": "cda-core",
        "cda_core.lib": "cda-core/lib",
        "cda_core.lib.api": "cda-core/lib/api",
        "cda_core.lib.models": "cda-core/lib/models",
        "cda_core.lib.parsing": "cda-core/lib/parsing",
        "cda_core.lib.rules": "cda-core/lib/rules",
        "flc_entry_checking": "flc-entry-checking",
        "flc_entry_checking.lib": "flc-entry-checking/lib",
        "flc_points": "flc-points",
        "flc_points.lib": "flc-points/lib",
    },
    install_requires=[
        "flask>=3.1",
        "numpy>=2.2",
        "pandas>=2.2",
        "requests>=2.32",
        "pytz",
    ],
    entry_points={
        "console_scripts": [
            "entry-checker=flc_entry_checking.lib.entry_checker:main",
        ],
    },
)