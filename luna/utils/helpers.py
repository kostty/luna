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

from luna.config import *
import logging
import pymongo
import ConfigParser
import urllib
import sys
import os
import errno 
import subprocess

def set_mac_node(mac, node, mongo_db = None):
    logging.basicConfig(level=logging.INFO)
#    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    if not mongo_db:
        try:
            mongo_client = pymongo.MongoClient(get_con_options())
        except:
            logger.error("Unable to connect to MongoDB.")
            raise RuntimeError
        logger.debug("Connection to MongoDB was successful.")
        mongo_db = mongo_client[db_name]
    mongo_collection = mongo_db['mac']
    mongo_collection.remove({'mac': mac})
    mongo_collection.remove({'node': node})
    mongo_collection.insert({'mac': mac, 'node': node})

def get_con_options():
    conf = ConfigParser.ConfigParser()
    if not conf.read("/etc/luna.conf"):
        return "localhost"
    try:
        replicaset = conf.get("MongoDB", "replicaset")
    except:
        replicaset = None
    try:
        server = conf.get("MongoDB", "server")
    except:
        server = 'localhost'
    try:
        authdb = conf.get("MongoDB", "authdb")
    except:
        authdb = 'admin'
    try:
        user = conf.get("MongoDB", "user")
        password = urllib.quote_plus(conf.get("MongoDB", "password"))
    except:
        user = None
        password = None
    if user and password and replicaset:
        auth_str = 'mongodb://' + user + ':' + password + '@' + server + '/' + authdb + '?replicaSet=' + replicaset
        return auth_str
    if user and password:
        auth_str = 'mongodb://' + user + ':' + password + '@' + server + '/' + authdb
        return auth_str
    return "localhost"

def clone_dirs(path1 = None, path2 = None):

    if not path1 or not path2:
        sys.stderr.write("Source and target paths need to be specified.\n")
        sys.exit(1)
    path1 = os.path.abspath(path1)
    path2 = os.path.abspath(path2)
    if not os.path.exists(path1):
        sys.stderr.write("Source dir {} does not exist.\n".format(path1))
        sys.exit(1)
    if not os.path.isdir(path1):
        sys.stderr.write("Source dir {} should be directory.\n".format(path1))
    path1 = path1 + "/"

    # check if someone run rsync already
    pidfile = "/run/luna_rsync.pid"
    try:
        pf = file(pidfile,'r')
        pid = int(pf.read().strip())
        pf.close()
    except IOError:
        pid = None

    if pid:
        message = "pidfile %s already exist.\n"
        sys.stdout.write(message % pidfile)
        try:
            os.kill(pid, 0)
        except OSError:
            pass
        else:
            message = "Process %s is running.\n"
            sys.stderr.write(message % pid)
            sys.exit(1)

    pf = file(pidfile,'w+')
    pid = os.getppid()
    pf.write("%s\n" % pid)
    pf.close()
    
    # create target dir if needed
    try:
        os.makedirs(path2)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path2):
            pass
        else:
            raise

    cmd = r'''/usr/bin/rsync -av -HAX --progress ''' + path1 + r''' ''' + path2
    try:
        rsync_out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stat_symb = ['\\', '|', '/', '-']
        i = 0
        while True:
            line = rsync_out.stdout.readline()
            if line == '':
                break
            i = i + 1
            sys.stdout.write(stat_symb[i % len(stat_symb)])
            sys.stdout.write('\r')
    except:
        os.remove(pidfile)
        sys.stdout.write('\r')
        sys.stderr.write("Interrupt.")
        sys.exit(1)
    os.remove(pidfile)
    return True

def rsync_data(host = None, lpath = None, rpath = None):

    if not host or not lpath:
        sys.stderr.write("Hostname or path did not specified")
        sys.exit(1)
    lpath = os.path.abspath(lpath)
    if not rpath:
        rpath = os.path.dirname(lpath)

    # check if someone run rsync already
    pidfile = "/run/luna_rsync.pid"
    try:
        pf = file(pidfile,'r')
        pid = int(pf.read().strip())
        pf.close()
    except IOError:
        pid = None

    if pid:
        message = "pidfile %s already exist.\n"
        sys.stdout.write(message % pidfile)
        try:
            os.kill(pid, 0)
        except OSError:
            pass
        else:
            message = "Process %s is running.\n"
            sys.stderr.write(message % pid)
            sys.exit(1)

    pf = file(pidfile,'w+')
    pid = os.getppid()
    pf.write("%s\n" % pid)
    pf.close()

    # check if someone run rsync on other node to prevent circular syncing
    ssh_proc = subprocess.Popen(['/usr/bin/ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null', host,
            'ls', pidfile],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        close_fds=True)
    streamdata = ssh_proc.communicate()[0]

    if not ssh_proc.returncode:
        message = "Pidfile %s exists on node %s. Probably syncronization is going from remote to local node. Exiting.\n"
        sys.stderr.write(message % (pidfile, host))
        os.remove(pidfile)
        sys.exit(1)

    cmd = r'''/usr/bin/rsync -avz -HAX -e "/usr/bin/ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress --delete ''' + lpath + r''' root@''' + host + r''':''' + rpath
    try:
        rsync_out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stat_symb = ['\\', '|', '/', '-']
        i = 0
        while True:
            line = rsync_out.stdout.readline()
            if line == '':
                break
            i = i + 1
            sys.stdout.write(stat_symb[i % len(stat_symb)])
            sys.stdout.write('\r')
    except:
        os.remove(pidfile)
        sys.stdout.write('\r')
        sys.stderr.write("Interrupt.")
        sys.exit(1)
    os.remove(pidfile)
    return True

def format_output(out):
    # get number of columns
    num_col = len(out['header'])
    len_content = 0
    for elem in out['content']:
        len_content += 1
        if len(elem) > num_col:
            num_col = len(elem)
    # get max length of line and
    # create new array out of input
    lengths=[0] * num_col
    header_tmp = [[]] * (num_col + 1)
    content_tmp = [[[] for x in range(num_col + 1)] for y in range(len_content)]
    
    # last element of the array will contain the maximum number of the new lines
    header_tmp[-1] = 1
    for i in range(len(out['header'])):
        elem=out['header'][i]
        lines = str(elem).split('\n')
        header_tmp[i] = lines
        newlines = 1
        for line in lines:
            newlines += 1
            if len(line) > lengths[i]:
                lengths[i] = len(line)
            if newlines > header_tmp[-1]:
                header_tmp[-1] = newlines
    content_line = 0
    total_num_of_new_lines = 1
    for out_line in out['content']:
        content_tmp[content_line][-1] = 1
        for i in range(len(out_line)):
            elem=out_line[i]
            lines = str(elem).split('\n')
            content_tmp[content_line][i] = lines
            newlines = 1
            for line in lines:
                newlines += 1
                if len(line) > lengths[i]:
                    lengths[i] = len(line)
                if newlines > content_tmp[content_line][-1]:
                    content_tmp[content_line][-1] = newlines
        total_num_of_new_lines += content_tmp[content_line][-1] - 1
        content_line += 1
    
    # need to have transponded matrix to ease output
    header_array = [['' for x in range(num_col)] for y in range(header_tmp[-1] - 1)]
    content_array = [['' for x in range(num_col)] for y in range(total_num_of_new_lines - 1)]

    for i in range(num_col):
        for j in range(len(header_tmp[i])):
            header_array[j][i] = header_tmp[i][j]
    relative_pointer = 0
    for content_line in content_tmp:
        for i in range(num_col):
            for j in range(len(content_line[i])):
                content_array[relative_pointer + j][i] = content_line[i][j]
        relative_pointer += content_line[-1] - 1

    return (lengths, header_array, content_array)
