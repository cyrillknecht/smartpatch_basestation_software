from setuptools import setup

setup(
    name='basestation_software',
    version='1.0.0',
    packages=['Basestation', 'AdditionalFunctionality'],
    url='https://github.com/cyrillknecht/smartpatch_basestation_software',
    license='MIT',
    author='cyrillknecht',
    author_email='',
    description='',
    install_requires=[
        'bleak==0.13.0',
        'art>=5.3',
        'termcolor==1.1.0',
        'tqdm==4.62.3',
        'paho-mqtt==1.6.1',
        'numpy==1.21.5',
        'tb-rest-client',
        'tb-mqtt-client',
        'heartpy~=1.2.7',
        'scipy==1.7.3',
        'matplotlib>=3.3.4',
        'pytest==7.3.1'
    ]
)
