from __future__ import unicode_literals

import os
import re
import setuptools


version = (
    re
        .compile(r".*__version__ = '(.*?)'", re.S)
        .match(open('chronicle/__init__.py').read())
        .group(1)
)

packages = [
    str(s) for s in
    setuptools.find_packages('.', exclude=('tests', 'tests.*'))
]

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = []

extras_require = {
    'tests': [
        'blumpkin>=0.4.0,<0.5.0',
        'ipdb',
        'webtest',
    ],
    'sentry': [
        'raven >=3.5,<3.6',
    ],
    'flask': [
        'flask',
    ],
    'pyramid': [
        'pyramid',
    ],
    'gunicorn': [
        'gunicorn',
    ]
}

scripts = []


setuptools.setup(
    name='chronicle',
    version=version,
    description='logging utils',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Programming Language :: Python",
    ],
    author='Balanced',
    author_email='dev+bob@balancedpayments.com',
    packages=packages,
    include_package_data=True,
    zip_safe=False,
    scripts=scripts,
    install_requires=requires,
    extras_require=extras_require,
    tests_require=extras_require['tests'],
    test_suite='nose.collector',
)
