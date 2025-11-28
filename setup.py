"""
Prometheus v0 PoC - Setup Configuration

Installation:
    pip install -e .                    # Development mode (local)
    pip install git+https://github.com/pmcray/Prometheus_v0_PoC.git  # From GitHub
"""

from setuptools import setup, find_packages

# Read requirements
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read README for long description
with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='prometheus-ai',
    version='0.69.0',
    description='Empirical Validation of Recursive Self-Improvement',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Prometheus AI Team',
    author_email='contact@prometheus-ai.org',
    url='https://github.com/pmcray/Prometheus_v0_PoC',
    packages=find_packages(exclude=['tests', 'notebooks', 'docs']),
    install_requires=requirements,
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    keywords='ai machine-learning deep-learning reinforcement-learning self-improvement chess go',
    project_urls={
        'Bug Reports': 'https://github.com/pmcray/Prometheus_v0_PoC/issues',
        'Source': 'https://github.com/pmcray/Prometheus_v0_PoC',
        'Documentation': 'https://github.com/pmcray/Prometheus_v0_PoC/blob/main/README.md',
    },
    entry_points={
        'console_scripts': [
            'prometheus=prometheus_cli:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
