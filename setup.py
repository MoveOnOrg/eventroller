from setuptools import setup
import textwrap
try:
    # officially wrong, but as an internal lib, do we care?
    from pip._internal.req import parse_requirements
except ImportError:
    from pip.req import parse_requirements

install_reqs = parse_requirements('requirements.txt', session='hack')
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name='eventroller',
    version='0.1',
    author='MoveOn.org',
    packages=['event_store', 'event_exim', 'reviewer', 'event_review'],
    url='https://github.com/MoveOnOrg/eventroller',
    license='MIT',
    description="Event aggregator and manager across event CRMs/websites used in progressive politics",
    long_description=textwrap.dedent(open('README.md', 'r').read()),
    install_requires=reqs,
    keywords = "python events actionkit",
    classifiers=['Development Status :: 4 - Beta', 'Environment :: Console', 'Intended Audience :: Developers', 'Natural Language :: English', 'Operating System :: OS Independent', 'Topic :: Internet :: WWW/HTTP'],
)
