from setuptools import setup

setup(
    name='thumbs-xblock',
    version='0.1',
    description='Thumbs XBlock Sample',
    py_modules=['thumbs'],
    #package_dir={'thumbs':''},
    install_requires=['XBlock'],
    entry_points={
        'xblock.v1': [
            'thumbs = thumbs.thumbs:ThumbsBlock',
        ]
    }
)
