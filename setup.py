from setuptools import setup, find_packages

setup(
    name = "AppMetrics",
    version = "0.1",

    packages = find_packages(),

    scripts = [],

    install_requires = [],

    package_data = {
    },

    # metadata for upload to PyPI
    author = "Antonio Valente",
    author_email = "y3sman@gmail.com",
    description = "Application metrics collector",
    license = "Apache 2.0",
    keywords = "metrics",
    url = "https://github.com/avalente/appmetrics",
)
