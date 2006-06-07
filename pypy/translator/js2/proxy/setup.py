from setuptools import setup, find_packages
from turbogears.finddata import find_package_data

setup(
    name="testme",
    version="1.0",
    #description="",
    #author="",
    #author_email="",
    #url="",
    install_requires = ["TurboGears >= 0.8.9"],
    scripts = ["testme-start.py"],
    zip_safe=False,
    packages=find_packages(),
    package_data = find_package_data(where='testme',
                                     package='testme'),
    )
    
