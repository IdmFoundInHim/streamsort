import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="streamsort",
    version="0.0.2",
    author="IdmFoundInHim",
    author_email="idmfoundinhim@gmail.com",
    description="Power tools for your playlists",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/IdmFoundInHim/streamsort",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Natural Language :: English",
        "Topic :: Multimedia :: Sound/Audio",
        "Typing :: Typed",
    ],
    keywords="playlists music backup shuffle",
    python_requires=">=3.10",
    install_requires=[  # Licenses
        "requests>=2.22.0",  # Apache
        "spotipy~=2.15",  # MIT
        "more-itertools>=8.0.0",  # MIT
        "frozendict>=2.0.0",  # LGPL
    ],
    package_data={"streamsort": ["README.md"]},
)
