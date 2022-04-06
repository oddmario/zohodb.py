#
# ZohoDB.py
#
# @oddmario
# Mario
# mariolatif741@yandex.com
#
# License: GNU GPLv3

import pathlib
from setuptools import setup

setup(
    name='zohodb.py',
    version='1.0.4',
    description='Use Zoho Sheets as a database server',
    license='GNU GPLv3',
    packages=['zohodb'],
    author='Mario',
    author_email='mariolatif741@yandex.com',
    keywords=['zohodb.py', 'zohodb', 'database', 'zoho', 'sheets'],
    url='https://github.com/oddmario/zohodb.py',
    install_requires=['httpx'],
    long_description=(pathlib.Path(__file__).parent / "README.md").read_text(),
    long_description_content_type="text/markdown"
)
