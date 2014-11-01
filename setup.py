from setuptools import setup, find_packages

setup(
    name = "AppMetrics",
    version = "0.4.2",

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
    keywords = ["metrics", "folsom", "histogram", "metric", "monitor"],
    url = "https://github.com/avalente/appmetrics",
    platforms = 'Platform Independent',

    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: System :: Monitoring",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
    ]
)
