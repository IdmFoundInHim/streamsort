import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='streamsort',
    version='0.0.0',
    author='IdmFoundInHim',
    author_email='idmfoundinhim@gmail.com',
    description='Power tools for your playlists',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/IdmFoundInHim/streamsort',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 2 - Pre-Alpha',
        'Natural Language :: English',
        'Topic :: Multimedia :: Sound/Audio',
        'Typing :: Typed'
    ],
    keywords='playlists music backup shuffle',
    python_requires='>=3.9',
    install_requires=[
        'requests>=2.22.0',
        'spotipy~=2.15',
    ],
    package_data={
        'streamsort': ['README.md']
    }
)