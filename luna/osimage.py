'''
Written by Dmitry Chirikov <dmitry@chirikov.ru>
This file is part of Luna, cluster provisioning tool
https://github.com/dchirikov/luna

This file is part of Luna.

Luna is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Luna is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Luna.  If not, see <http://www.gnu.org/licenses/>.

'''

from config import *
import logging
import sys
import os
import pwd
import grp
import subprocess
import ctypes
import rpm
from bson.dbref import DBRef
from luna.base import Base
from luna.cluster import Cluster
import libtorrent
import uuid
#import tarfile
import shutil
import tempfile

class OsImage(Base):
    """
    Class for operating with osimages records
    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, mongo_db = None, create = False, id = None, path = '', kernver = '', kernopts = '', grab_list = 'grab_default_centos.lst'):
        """
        create    - shoulld be True if we need create osimage
        path      - path to / of the image/ can be ralative, if needed (will be converted to absolute)
        kernver   - kernel version (will be checked on creation)
        kernopt   - kernel options
        grab_list - rsync exclude list for grabbing live node to image
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'osimage'
        mongo_doc = self._check_name(name, mongo_db, create, id)
        if bool(kernopts) and type(kernopts) is not str:
            self._logger.error("Kernel options should be 'str' type")
            raise RuntimeError
        self._keylist = {'path': type(''), 'kernver': type(''), 'kernopts': type(''),
                        'kernmodules': type(''), 'dracutmodules': type(''), 'tarball': type(''),
                        'torrent': type(''), 'kernfile': type(''), 'initrdfile': type(''),
                        'grab_exclude_list': type(''), 'grab_filesystems': type('')}
        if create:
            cluster = Cluster(mongo_db = self._mongo_db)
            path = os.path.abspath(path)
            path_suspected_doc = self._mongo_collection.find_one({'path': path})
            if path_suspected_doc and path_suspected_doc['path'] == path:
                self._logger.error("Cannot create 'osimage' with the same 'path' as name='{}' has".format(path_suspected_doc['name']))
                raise RuntimeError
            if kernver == 'ANY':
                try:
                    kernver = self.get_package_ver(path, 'kernel')[0]
                except:
                    pass
            if not self._check_kernel(path, kernver):
                raise RuntimeError
            grab_list_path = cluster.get('path') + '/templates/' + grab_list
            if not os.path.isfile(grab_list_path):
                self._logger.error("'{}' is not a file.".format(grab_list_path))
                raise RuntimeError
            with open(grab_list_path) as lst:
                grab_list_content = lst.read()
            mongo_doc = {'name': name, 'path': path,
                        'kernver': kernver, 'kernopts': kernopts,
                        'dracutmodules': 'luna,-i18n,-plymouth',
                        'kernmodules': 'ipmi_devintf,ipmi_si,ipmi_msghandler',
                        'grab_exclude_list': grab_list_content,
                        'grab_filesystems': '/,/boot'}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(cluster)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger(__name__ + '.' + self._name)

    def list_kernels(self):
        return self.get_package_ver(self.get('path'), 'kernel')

    def get_package_ver(self, path, package):
        rpm.addMacro("_dbpath", path + '/var/lib/rpm')
        ts = rpm.TransactionSet()
        package_vers = list()
        mi = ts.dbMatch( 'name', package )
        for h in mi:
            ver = "%s-%s.%s" % (h['VERSION'], h['RELEASE'], h['ARCH'])
            package_vers.extend([ver])
        return package_vers

    def _check_kernel(self, path, kernver):
        os_image_kernvers = None
        if not os.path.isdir(path):
            self._logger.error("{} is not valid dir".format(path))
            return None
        try:
            os_image_kernvers = self.get_package_ver(path,'kernel')
            #req_kernver = os_image_kernvers.index(kernver)
        except:
            #req_kernver = None
            if os_image_kernvers == []:
                self._logger.error("No kernel package installed in {}".format(path))
                return None
            self._logger.error("Kernel version '{}' not in list {} from {}. Kernel Version or osimage path are incorrect?".format(kernver, os_image_kernvers, path))
            return None
        return True

    def create_tarball(self):
        # TODO check if root
        cluster = Cluster(mongo_db = self._mongo_db)

        path = cluster.get('path')
        if not path:
            self._logger.error("Path needs to be configured.")
            return None
        tracker_address = cluster.get('fronend_address')
        if tracker_address == '':
            self._logger.error("Tracker address needs to be configured.")
            return None
        tracker_port = cluster.get('frontend_port')
        if tracker_port == 0:
            self._logger.error("Tracker port needs to be configured.")
            return None
        user = cluster.get('user')
        if not user:
            self._logger.error("User needs to be configured.")
            return None
        path_to_store = path + "/torrents"
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = pwd.getpwnam(user).pw_gid
        if not os.path.exists(path_to_store):
            os.makedirs(path_to_store)
            os.chown(path_to_store, user_id, grp_id)
            os.chmod(path_to_store, 0644)
        uid = str(uuid.uuid4())
        tarfile_path = path_to_store + "/" + uid + ".tgz"
        image_path = self.get('path')
        try:
            tar_out = subprocess.Popen(['/usr/bin/tar',
                    '-C', image_path + '/.',
                    '--one-file-system',
                    '--xattrs',
                    '--selinux',
                    '--acls',
                    '--checkpoint=100',
                    '-c', '-z', '-f', tarfile_path, '.'], stderr=subprocess.PIPE) # dirty, but 4 times faster
            stat_symb = ['\\', '|', '/', '-']
            i = 0
            while True:
                line = tar_out.stderr.readline()
                if line == '':
                    break
                i = i + 1
                sys.stdout.write(stat_symb[i % len(stat_symb)])
                sys.stdout.write('\r')
        except:
            os.remove(tarfile_path)
            sys.stdout.write('\r')
            return None
        os.chown(tarfile_path, user_id, grp_id)
        os.chmod(tarfile_path, 0644)
        self.set('tarball', str(uid))
        return True

    def create_torrent(self):
        # TODO check if root
        tarball_uid = self.get('tarball')
        cluster = Cluster(mongo_db = self._mongo_db)
        if not bool(tarball_uid):
            self._logger.error("No tarball in DB.")
            return None
        tarball = cluster.get('path') + "/torrents/" + tarball_uid + ".tgz"
        if not os.path.exists(tarball):
            self._logger.error("Wrong path in DB.")
            return None
        tracker_address = cluster.get('frontend_address')
        if tracker_address == '':
            self._logger.error("Tracker address needs to be configured.")
            return None
        tracker_port = cluster.get('frontend_port')
        if tracker_port == 0:
            self._logger.error("Tracker port needs to be configured.")
            return None
        user = cluster.get('user')
        if not user:
            self._logger.error("User needs to be configured.")
            return None
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = pwd.getpwnam(user).pw_gid
        old_cwd = os.getcwd()
        os.chdir(os.path.dirname(tarball))
        uid = str(uuid.uuid4())
        torrentfile = str(cluster.get('path')) + "/torrents/" + uid
        fs = libtorrent.file_storage()
        libtorrent.add_files(fs, os.path.basename(tarball))
        t = libtorrent.create_torrent(fs)
        t.add_tracker("http://" + str(tracker_address) + ":" + str(tracker_port) + "/announce")
        t.set_creator(torrent_key)
        t.set_comment(uid)
        libtorrent.set_piece_hashes(t, ".")
        f = open(torrentfile, 'w')
        f.write(libtorrent.bencode(t.generate()))
        f.close()
        self.set('torrent', str(uid))
        os.chown(torrentfile, user_id, grp_id)
        shutil.move(torrentfile, torrentfile + ".torrent")
        os.chdir(old_cwd)
        return True

    def pack_boot(self):
        def mount(source, target, fs):
            subprocess.Popen(['/usr/bin/mount', '-t', fs, source, target])
            #ret = ctypes.CDLL('libc.so.6', use_errno=True).mount(source, target, fs, 0, options)
            #if ret < 0:
            #    errno = ctypes.get_errno()
            #    raise RuntimeError("Error mounting {} ({}) on {} with options '{}': {}".
            #        format(source, fs, target, options, os.strerror(errno)))
        def umount(source):
            subprocess.Popen(['/usr/bin/umount', source])
            #ret = ctypes.CDLL('libc.so.6', use_errno=True).umount(source)
            #if ret < 0:
            #    errno = ctypes.get_errno()
            #    raise RuntimeError("Error umounting {}: .".
            #        format(source, os.strerror(errno)))
        def prepare_mounts(path):
            mount('devtmpfs', path + '/dev', 'devtmpfs')
            mount('proc', path + '/proc', 'proc')
            mount('sysfs', path + '/sys', 'sysfs')
        def cleanup_mounts(path):
            umount(path + '/dev')
            umount(path + '/proc')
            umount(path + '/sys')
        cluster = Cluster(mongo_db = self._mongo_db)
        #boot_prefix = '/boot'
        image_path = str(self.get('path'))
        kernver = str(self.get('kernver'))
        tmp_path = '/tmp' # in chroot env
        initrdfile = str(self.name) + '-initramfs-' + kernver
        kernfile = str(self.name) + '-vmlinuz-' + kernver
        #kernel_image = kernel_name + '-' + kernver
        #kernel_path = image_path + boot_prefix +  '/' +  kernel_image
        path = cluster.get('path')
        if not path:
            self._logger.error("Path needs to be configured.")
            return None
        path = str(path)
        user = cluster.get('user')
        if not user:
            self._logger.error("User needs to be configured.")
            return None
        path_to_store = path + "/boot"
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = pwd.getpwnam(user).pw_gid
        if not os.path.exists(path_to_store):
            os.makedirs(path_to_store)
            os.chown(path_to_store, user_id, grp_id)
        modules_add = []
        modules_remove = []
        drivers_add = []
        drivers_remove = []
        dracutmodules = self.get('dracutmodules')
        if dracutmodules:
            dracutmodules = str(dracutmodules)
            modules_add =    sum([['--add', i]      for i in dracutmodules.split(',') if i[0] != '-'], [])
            modules_remove = sum([['--omit', i[1:]] for i in dracutmodules.split(',') if i[0] == '-'], [])
        kernmodules = self.get('kernmodules')
        if kernmodules:
            kernmodules = str(kernmodules)
            drivers_add =    sum([['--add-drivers',  i]     for i in kernmodules.split(',') if i[0] != '-'], [])
            drivers_remove = sum([['--omit-drivers', i[1:]] for i in kernmodules.split(',') if i[0] == '-'], [])
        prepare_mounts(image_path)
        real_root = os.open("/", os.O_RDONLY)
        os.chroot(image_path)

        try:
            dracut_modules = subprocess.Popen(['/usr/sbin/dracut', '--kver', kernver, '--list-modules'], stdout=subprocess.PIPE)
            luna_exists = False
            while dracut_modules.poll() is None:
                line = dracut_modules.stdout.readline()
                if line.strip() == 'luna':
                    luna_exists = True
            if not luna_exists:
                self._logger.error("No luna dracut module in osimage '{}'".format(self.name))
                raise RuntimeError
            dracut_cmd =  ['/usr/sbin/dracut', '--force', '--kver', kernver] + modules_add + modules_remove + drivers_add + drivers_remove + [tmp_path + '/' + initrdfile]
            dracut_create = subprocess.Popen(dracut_cmd, stdout=subprocess.PIPE)
            while dracut_create.poll() is None:
                line = dracut_create.stdout.readline()
        except:
            self._logger.error("Error on building initrd.")
            os.fchdir(real_root)
            os.chroot(".")
            os.close(real_root)
            cleanup_mounts(image_path)
            try:
                pass
                #os.remove(image_path + '/' + tmp_path + '/' + initrdfile)
            except:
                pass
            return None

        os.fchdir(real_root)
        os.chroot(".")
        os.close(real_root)
        cleanup_mounts(image_path)
        shutil.copy(image_path + tmp_path + '/' + initrdfile, path_to_store)
        shutil.copy(image_path + '/boot/vmlinuz-' + kernver, path_to_store + '/' + kernfile)
        os.chown(path_to_store + '/' + initrdfile, user_id, grp_id)
        os.chmod(path_to_store + '/' + initrdfile, 0644)
        os.chown(path_to_store + '/' + kernfile, user_id, grp_id)
        os.chmod(path_to_store + '/' + kernfile, 0644)
        self.set('kernfile', kernfile)
        self.set('initrdfile', initrdfile)

    def copy_boot(self):
        cluster = Cluster(mongo_db = self._mongo_db)
        image_path = str(self.get('path'))
        kernver = str(self.get('kernver'))
        tmp_path = '/tmp' # in chroot env
        initrdfile = str(self.name) + '-initramfs-' + kernver
        kernfile = str(self.name) + '-vmlinuz-' + kernver
        path = cluster.get('path')
        if not path:
            self._logger.error("Path needs to be configured.")
            return None
        path = str(path)
        user = cluster.get('user')
        if not user:
            self._logger.error("User needs to be configured.")
            return None
        path_to_store = path + "/boot"
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = pwd.getpwnam(user).pw_gid
        if not os.path.exists(path_to_store):
            os.makedirs(path_to_store)
            os.chown(path_to_store, user_id, grp_id)
        shutil.copy(image_path + '/boot/initramfs-' + kernver + '.img', path_to_store + '/' + initrdfile)
        shutil.copy(image_path + '/boot/vmlinuz-' + kernver, path_to_store + '/' + kernfile)
        os.chown(path_to_store + '/' + initrdfile, user_id, grp_id)
        os.chmod(path_to_store + '/' + initrdfile, 0644)
        os.chown(path_to_store + '/' + kernfile, user_id, grp_id)
        os.chmod(path_to_store + '/' + kernfile, 0644)
        self.set('kernfile', kernfile)
        self.set('initrdfile', initrdfile)
        self._logger.warning("Boot files was copied, but luna module might not being added to initrd. Please check /etc/dracut.conf.d in image")
        return True

    def grab_host(self, host, dry_run = True, verbose = False):
        grab_exclude_list = self.get('grab_exclude_list')
        grab_filesystems = self.get('grab_filesystems')
        osimage_path = self.get('path')
        #
        # chech if we can proceed
        #
        if grab_exclude_list == None:
            self._logger.error('No grab_exclude_list for osimage defined.')
            return None
        if grab_filesystems == None:
            self._logger.error('No grab_filesystems for osimage defined.')
            return None
        #
        # grab_filesystems will be array with at least single element '/'
        #
        if bool(grab_filesystems):
            grab_filesystems = grab_filesystems.split(',')
        else:
            grab_filesystems = ['/']
        #
        # Create temp file with exclude content
        #
        file_prefix = self.name + '.excl_list.rsync.'
        file_desc, exclude_file_name = tempfile.mkstemp(prefix = file_prefix)
        with open(exclude_file_name, 'a') as ex_file:
            ex_file.write(grab_exclude_list)
        #
        # Status symbols
        #
        stat_symb = ['\\', '|', '/', '-']
        #
        # Construct rsync command line
        #
        rsync_common_opts = r'''-avxz -HAX -e "/usr/bin/ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress --delete --exclude-from=''' + exclude_file_name + r''' '''
        if dry_run:
            rsync_opts = rsync_common_opts + r''' --dry-run '''
            verbose = True
        else:
            rsync_opts = rsync_common_opts
        #
        # enumarete all filesystems
        #
        for fs in grab_filesystems:
            ret_code = 0
            #
            # Sanitize fs
            #
            fs = fs.strip()
            if not fs:
                continue
            #
            # Use absolute path
            #
            if fs[-1] != '/':
                fs += '/'
            if fs[0] != '/':
                fs = '/' + fs
            self._logger.info("Fetching {} from {}".format(fs, host))
            #
            # Path on master where to grab. Create it locally if needed
            #
            local_fs = osimage_path + fs
            if not os.path.exists(local_fs) and not dry_run:
                os.makedirs(local_fs)
            #
            # Rsync comand. Finally
            #
            cmd = r'''/usr/bin/rsync ''' + rsync_opts + r''' root@''' + host + r''':''' + fs + r''' ''' + local_fs
            if verbose:
                self._logger.info('Running command: {}'.format(cmd))
            try:
                rsync_out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                i = 0
                while True:
                    line = rsync_out.stdout.readline()
                    if verbose:
                        self._logger.info(line.strip())
                    else:
                        #
                        # Draw status symbols
                        #
                        i = i + 1
                        sys.stdout.write(stat_symb[i % len(stat_symb)])
                        sys.stdout.write('\r')
                    #
                    # No lines in output? Exit.
                    #
                    if not line:
                        rsync_stdout, rsync_err = rsync_out.communicate()
                        ret_code = rsync_out.returncode
                        break
                #
                # If exit code of rsync is not 0, print stderr
                #
                if ret_code:
                    for l in rsync_err.split('\n'):
                        self._logger.error(l)
            #
            # Ctrl+C
            #
            except KeyboardInterrupt:
                sys.stdout.write('\r')
                self._logger.error('Interrupt.')
                ret_code = 1
            if ret_code:
                break
        self._logger.info('Success.')
        #
        # remove temp file
        #
        os.remove(exclude_file_name)
