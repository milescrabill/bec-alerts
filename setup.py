from setuptools import setup

setup(
    name='bec-alerts',
    version='0.1.0',
    py_modules=['bec_alerts'],
    install_requires=[
        'Click',
        'boto3',
        'Django',
        'python-dotenv',
    ],
    entry_points='''
        [console_scripts]
        bec-alerts=bec_alerts.cli:cli
    ''',
)
