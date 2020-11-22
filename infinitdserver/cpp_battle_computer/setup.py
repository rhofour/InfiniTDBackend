from setuptools import setup

from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        "battle_computer.pyx",
        compiler_directives={'language_level': 3},
    )
)
