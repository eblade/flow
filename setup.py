from setuptools import setup

name_ = 'flow'
version_ = '0.3'
packages_ = [
    'flow',
    'flow.source',
]
classifiers_ = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 2",
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX :: Linux",
] 
setup(
    name=name_,
    version=version_,
    author='Vizrt',
    author_email='jegneblad@DELETEMEvizrt.com',
    description='Daemon and tool framework for the Viz One API',
    license="Vizrt Confidential",
    url='https://github.com/eblade/flow',
    download_url='https://github.com/eblade/flow/archive/master.zip',
    packages=packages_,
    classifiers=classifiers_,
    scripts=[],
    install_requires=[]
)
