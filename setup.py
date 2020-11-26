from setuptools import setup
from os.path import dirname, join, abspath

setup(
    name='Helios Scanner',
    version='1.1',
    packages=['helios', 'helios.ext', 'helios.ext.libcms', 'helios.ext.libcms.scanners', 'helios.ext.mefjus',
              'helios.ext.metamonster', 'helios.core', 'helios.webapp', 'helios.webapp.databases', 'helios.modules'],
    url='https://github.com/stefan2200/Helios',
    license='Apache 2.0',
    author='stefan2200',
    author_email='stefan@stefanvlems.nl',
    description='A Python based Web Application security scanner',
    long_description=open(join(abspath(dirname(__file__)), "README.rst")).read(),
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Security',
        'Topic :: Software Development :: Testing',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    entry_points={
        'console_scripts': ['helios=helios.main:main', 'helios-update-db=helios.webapp.databases.update:main'],
    },
    install_requires=[
        'pyOpenSSL>=0.14'
        'beautifulsoup4',
        'requests',
        'selenium',
        'filelock',
        'msgpack'
    ],
    extras_require={':python_version == "2.7"': ['futures']},
    include_package_data=True,
    package_data={
        '': [
            'scripts/*',
            'drivers/*',
            'wordlists/*'
        ]
    }
)
