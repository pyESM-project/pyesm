from setuptools import setup, find_packages

setup(
    name='pyESM',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'numpy',
        'cvxpy',
        'openpyxl'
    ],
    author='Matteo V. Rocco',
    author_email='matteovincenzo.rocco@polimi.it',
    description='...',
    url='https://github.com/MIMO-modelling-suite/pyESM',
)
