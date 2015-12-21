
import os
import warnings
import subprocess

from charmhelpers.fetch import (
    apt_install,
    apt_purge,
    apt_update,
    _run_apt_command,
)

from charmhelpers.core.host import (
    lsb_release,
)


def apt_key(key_id):
    subprocess.check_call(['apt-key', 'adv', '--keyserver',
                           'hkp://keyserver.ubuntu.com:80', '--recv', key_id])

class MongoDB(object):
    upstream_list = '/etc/apt/sources.list.d/mongodb.list'

    def __init__(self, source, version=None):
        if source not in self.package_map.keys():
            raise Exception('{0} is not a valid source'.format(source))
        self.source = source
        self.version = version

    def install(self):
        apt_install(self.packages())

    def uninstall(self):
        apt_purge(self.packages())
        _run_apt_command(['apt-get', 'autoremove', '--purge', '--assume-yes'])

    def packages(self):
        return [p.format(self.version) for p in self.package_map[self.source]]

    def add_upstream(self):
        with open(self.upstream_list, 'w') as f:
            f.write(self.upstream_repo.format(lsb_release()['DISTRIB_CODENAME']))
        apt_key('7F0CEB10')
        apt_key('EA312927')


class MongoDB20(MongoDB):
    package_map = {
        'upstream': [
            'mongodb-10gen={}',
        ],
        'archive': [
            'mongodb-server',
        ],
    }

    upstream_repo = 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen'

    def install(self):
        if self.source == 'upstream':
            self.add_upstream()
            apt_update()

        super(MongoDB20, self).install()

    def uninstall(self):
        super(MongoDB20, self).uninstall()
        if os.path.exists(self.upstream_list):
            os.unlink(self.upstream_list)


class MongoDB22(MongoDB20):
    pass


class MongoDB24(MongoDB20):
    pass


class MongoDB26(MongoDB20):
    package_map = {
        'upstream': [
            'mongodb-org-server={}',
            'mongodb-org-shell={}',
            'mongodb-org-tools={}',
        ],
        'archive': [
            'mongodb-server',
        ],
    }


class MongoDB30(MongoDB):
    package_map = {
        'upstream': [
            'mongodb-org-server={}',
            'mongodb-org-shell={}',
            'mongodb-org-tools={}',
        ],
    }

    upstream_repo = 'deb http://repo.mongodb.org/apt/ubuntu {0}/mongodb-org/3.0 multiverse'

    def install(self):
        self.add_upstream()
        apt_update()
        super(MongoDB30, self).install()

    def uninstall(self):
        super(MongoDB30, self).uninstall()
        if os.path.exists(self.upstream_list):
            os.unlink(self.upstream_list)


class MongoDB31(MongoDB30):
    package_map = {
        'upstream': [
            'mongodb-org-unstable-server={}',
            'mongodb-org-unstable-shell={}',
            'mongodb-org-unstable-tools={}',
        ],
    }

    upstream_repo = 'deb http://repo.mongodb.org/apt/ubuntu {0}/mongodb-org/3.1 multiverse'


class MongoDB32(MongoDB30):
    upstream_repo = 'deb http://repo.mongodb.org/apt/ubuntu {0}/mongodb-org/3.2 multiverse'


def installed():
    return os.path.isfile('/usr/bin/mongo')


def version():
    if not installed():
        return None
    return subprocess.check_output(['/usr/bin/mongo', '--version'],
                                   stderr=subprocess.STDOUT).decode('UTF-8').split(': ')[1]

_distro_map = {
    'precise': MongoDB20,
    'trusty': MongoDB24,
    'xenial': MongoDB26,
}

def mongodb(ver=None):
    if not ver and installed():
        ver = version()
    if not ver or ver == 'archive':
        distro = lsb_release()['DISTRIB_CODENAME']
        if distro not in _distro_map.keys():
            _msg = 'Unknown distribution: {0}. Please deploy only on: {1}'
            raise Exception(_msg.format(distro, _distro_map.keys()))

        return _distro_map[distro]('archive')

    def subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in subclasses(s)]

    def search(version):
        # Does a count down search of version until next lowest match. So
        # long as it doesn't drop below a major version things should be good.
        major, minor = [c for c in version.replace('.', '')[:2]]
        minor_range = reversed(range(0, int(minor) + 1))
        needles = ['MongoDB{0}{1}'.format(major, v) for v in minor_range]
        versions = subclasses(MongoDB)

        for needle in needles:
            for m in subclasses(MongoDB):
                if m.__name__ == needle:
                    return m('upstream', version)

        warnings.warn('No viable major version found, fallback to default')
        return MongoDB()

    return search(ver)

