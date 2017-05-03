# Disclaimer

Luna is a baremetal provisioning tool that uses an image based approach. It delivers full images of operating systems and not a 'recipe' on how to configure one.
It also dramatically speeds up installation time, and reduces administrative efforts.

# Overview

Luna uses the BitTorrent protocol to provision nodes. As such, every booting node helps the others to boot.

Once a node is fully booted it stops being a torrent seeder and other nodes can no longer use it to download the image. The torrent client only acts in the initrd environment.

Luna does not require any additional services to run on a node. By default it changes very a limited number of files on provisioned nodes.
It us usually limited to `/etc/hostname` and `/etc/sysconfig/network-scripts/ifcfg-*` files.

|Number of nodes|Time for cold boot, min|xCAT cold boot, min|
|:-------------:|:---------------------:|:-----------------:|
|              1|                      3|                  9|
|             36|                      4|                 26|
|             72|                      4|                 53|

Image size is 1GB. Provisioning node is equiped with a 1Gb ethernet interface.

In a cluster of 300 nodes. Boot time using luna has been measured to be aproximately 5 minutes. This includes BIOS POST procedures and all starting systemd services.

# Getting started

Let's assume you have a server using the IP address `10.30.255.254` to provision the cluster

## Server preparation

### Build RPM
```
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum -y install wget python-docutils gcc-c++ rb_libtorrent-devel boost-devel make rpm-build redhat-rpm-config
wget https://github.com/clustervision/luna/archive/v1.1.tar.gz
rpmbuild -ta v1.1.tar.gz
```
### Install hostlist
Source code is available [here](https://www.nsc.liu.se/~kent/python-hostlist/)
```
wget https://www.nsc.liu.se/~kent/python-hostlist/python-hostlist-1.17.tar.gz
rpmbuild -ta python-hostlist-1.17.tar.gz
yum -y install python-hostlist-1.17-1.noarch.rpm
```
### Install Luna
```
yum -y install luna-1.1-2.el7.centos.x86_64.rpm
```

### Setup environment

```
[ -f /root/.ssh/id_rsa ] || ssh-keygen -t rsa -f /root/.ssh/id_rsa -N ''

# Disable SELINUX

sed -i -e 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
setenforce 0

# Configure xinetd

mkdir /tftpboot
sed -e 's/^\(\W\+disable\W\+\=\W\)yes/\1no/g' -i /etc/xinetd.d/tftp
sed -e 's|^\(\W\+server_args\W\+\=\W-s\W\)/var/lib/tftpboot|\1/tftpboot|g' -i /etc/xinetd.d/tftp
cp /usr/share/ipxe/undionly.kpxe /tftpboot/luna_undionly.kpxe

# Configure nginx and named

cp /usr/share/luna/nginx-luna.conf /etc/nginx/conf.d/luna.conf

echo 'include "/etc/named.luna.zones";' >> /etc/named.conf
touch /etc/named.luna.zones

# Enable and start services

systemctl enable nginx
systemctl enable mongod
systemctl enable named
systemctl enable xinetd

systemctl restart xinetd
systemctl restart mongod
systemctl restart nginx
systemctl restart named
```

### Generate a CentOS image

```
mkdir -p /opt/luna/os/compute/var/lib/rpm
rpm --root /opt/luna/os/compute --initdb
yum -y install yum-utils
yumdownloader centos-release
rpm --root /opt/luna/os/compute -ivh centos-release\*.rpm
yum --installroot=/opt/luna/os/compute -y groupinstall Base
yum --installroot=/opt/luna/os/compute -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum --installroot=/opt/luna/os/compute -y install luna-client-1.1-2.el7.centos.x86_64.rpm
```

#### Setup sshd, paswordless access and password for the root user in osimage

```
mkdir /opt/luna/os/compute/root/.ssh
chmod 700 /opt/luna/os/compute/root/.ssh

mount -t devtmpfs devtmpfs /opt/luna/os/compute/dev/
chroot  /opt/luna/os/compute

ssh-keygen -f /etc/ssh/ssh_host_ecdsa_key -N '' -t ecdsa
abrt-auto-reporting enabled
passwd
exit
umount /opt/luna/os/compute/dev/

cat /root/.ssh/id_rsa.pub >> /opt/luna/os/compute/root/.ssh/authorized_keys
chmod 600 /opt/luna/os/compute/root/.ssh/authorized_keys
```

### Configure a new luna cluster

```
luna cluster init
luna cluster change --frontend_address 10.30.255.254
luna network add -n cluster -N 10.30.0.0 -P 16
luna cluster makedhcp --network cluster --start_ip 10.30.128.1 --end_ip 10.30.140.255
systemctl start lweb ltorrent
systemctl enable lweb ltorrent
luna osimage add -n compute -p /opt/luna/os/compute
luna osimage pack -n compute
luna bmcsetup add -n base
luna network add -n ipmi -N 10.31.0.0 -P 16
luna switch add -n switch01 --oid .1.3.6.1.2.1.17.7.1.2.2.1.2 --network ipmi --ip 10.31.253.21
luna group add -n compute -i eth0 -o compute
luna group change -n compute -b base
luna group change -n compute --boot_if eth0
luna group change -n compute --interface eth0 --setnet cluster
echo -e "DEVICE=eth0\nONBOOT=yes" | luna group change  --name compute --interface eth0 -e
luna group change -n compute --bmcnetwork --setnet ipmi
luna node add -g compute
luna cluster makedns
```

Please note that in this case we assume that the nodes can reach the cluster using an interface called `eth0`.
To figure out the proper name of the interface you can specify any interface name (e.g. eth0) then boot a node in service mode using:

```
luna node change -n node001 --service y
```

In service mode you can perform an inventory of the interfaces, local disks, BMC features

##### (Optional) Configure storage partitioning

You can boot the nodes in diskless mode, or write your own partitioning script using:

```
luna group change -n compute --partscript -e
```

Sample partitioning script for a device called `/dev/sda`:

```
parted /dev/sda -s 'mklabel msdos'
parted /dev/sda -s 'rm 1; rm 2'
parted /dev/sda -s 'mkpart p ext2 1 256m'
parted /dev/sda -s 'mkpart p ext3 256m 100%'
parted /dev/sda -s 'set 1 boot on'

mkfs.ext2 /dev/sda1
mkfs.ext4 /dev/sda2

mount /dev/sda2 /sysroot
mkdir /sysroot/boot
mount /dev/sda1 /sysroot/boot
```

###### (Optional) Install a bootloader on the nodes using a  postscript

`cat << EOF | luna group change -n compute  --post -e`

```
mount -o bind /proc /sysroot/proc
mount -o bind /dev /sysroot/dev
chroot /sysroot /bin/bash -c "/usr/sbin/grub2-mkconfig -o /boot/grub2/grub.cfg; /usr/sbin/grub2-install /dev/sda"
umount /sysroot/dev
umount /sysroot/proc
EOF
```

## Add a node to the cluster

```
luna node add -g compute
```

A node name will be automatically generated using the default nodeXXX format

```
luna node change -n node001 -s switch01
luna node change -n node001 -p 1

```
## Start luna's services

```
ltorrent start
lweb start
```

## Check that everything is working properly

```
curl "http://10.30.255.254:7050/luna?step=boot"
wget "http://10.30.255.254:7050/boot/compute-vmlinuz-3.10.0-327.10.1.el7.x86_64"
curl "http://10.30.255.254:7050/luna?step=install&node=node001"
```

## Update DHCP and DNS configurations

```
luna cluster makedhcp -N cluster -s 10.30.128.1 -e 10.30.255.200
luna cluster makedns
```

## Boot a node

Luna supports multiple modes of booting a node:

- Booting from localdisk:

```
luna node change -n node001 --localboot y
```

- Booting into service mode for diagnostics:

```
luna node change -n node001 --service y
```

- Configure the BMC when booting:

```
luna node change -n node001 --setupbmc y
```

# Using luna in an HA configuration

## MongoDB config

By default MongoDB listens only loopback interface and provides no credentials checking.

To set up a replica set, `/etc/mongod.conf` needs to be updated

Sample config:

```
bind_ip = 127.0.0.1,10.30.255.254
replSet = luna
```

Then mongod needs to be restarted:

```
systemctl restart mongod
```

Using mongo CLI, setup a replica set:

```
rs.initiate()
```

Then restart mongod and back to CLI

- Add root user:

```
use admin
db.createUser({user: "root", pwd: "<password>", roles: [ { role: "root", db: "admin" } ]})
```
edit config mongod to enable auth:
```
auth = true
```
restart mongod:
```
systemctl restart mongod
```
Enter to mongo shell:
```
mongo -u root -p <password> --authenticationDatabase admin
```
Create user for Luna:
```
use luna
db.createUser({user: "luna", pwd: "<password>", roles: [{role: "dbOwner", db: "luna"}]})
```
Now we are ready to create config file for connection:
```
cat << EOF > /etc/luna.conf
[MongoDB]
replicaset=luna
server=localhost
authdb=luna
user=luna
password=<password>
EOF
```
## Configure luna for HA

Consider you have:

|IP                       | Name      |
|------------------------:|:----------|
|           10.30.255.251 |   master1 |
|           10.30.255.252 |   master2 |
|(floating) 10.30.255.254 |   master  |

```
openssl rand -base64 741 > /etc/mongo.key
chown mongodb: /etc/mongo.key
chmod 400 /etc/mongo.key
```
Add parameter to  /etc/mongod.conf
```
keyFile = /etc/mongo.key
```
Copy files to other master
```
scp -pr /etc/mongo.key 10.30.255.252:/etc/
scp /etc/mongod.conf 10.30.255.252:/etc/
```

Edit mongod.conf to to change the ip address there:
```
sed -i -e 's/10.30.255.251/10.30.255.252/' /etc/mongod.conf
```
Restart mongo instances on both servers:
```
systemctl restart mongod
```
In mongo shell add another member:
```
rs.add("10.30.255.252")
```
Then restart mongod instance on other master.

Check status:
```
luna:PRIMARY> rs.status()
```

## (Optional) Adding a mongodb arbiter

For HA setups with two nodes, the following configuration is suggested:

On each node, you will have MongoDB with full data sets ready to handle data requests. As we have only 2 instances, in case one fails, the live instance will decide that a split-brain situation has occured and will demote itself to secondary and will refuse to handle requests.

To avoid such a situation, we need to have a tie-breaker - the arbiter. It is a tiny service (in terms of memory footprint and service logic) which adds one vote to the master election in a mongodb replicaset.
We will have a copy of the arbiter on the two nodes. And we will use pacemaker to bring one and only one copy of the arbiter online. Pacemaker should have STONITH configured.
This way even is the pacemaker cluster is down the regular mongodb instances will still have 2 votes out of 3 and service will still be available.


Copy mongod config:
```
cp /etc/mongod.conf /etc/mongod-arbiter.conf
```

Change the following:

```
bind_ip = 127.0.0.1,10.30.255.254   # 255.254 will be cluster (floating) ip here
port = 27018                        # non standart port not to conflict with other MongoDB instancess
pidfilepath = /var/run/mongodb-arbiter/mongod.pid
logpath = /var/log/mongodb/mongod-arbiter.log
unixSocketPrefix = /var/run/mongodb-arbiter
dbpath = /var/lib/mongodb-arbiter
nojournal = true                    # disable journal in order to reduce amount of data in dbpath
noprealloc = true                   # disable noprealloc for the same reason
smallfiles = true                   # same considerations
```

Create an environmental file:

```
cat << EOF > /etc/sysconfig/mongod-arbiter
> OPTIONS="--quiet -f /etc/mongod-arbiter.conf"
> EOF
```

For initialization you need to bring the floating IP up on one of the nodes:

```
ip a add 10.30.255.254/16 dev eth1
```

Create a systemd unit for the arbiter:

```
cat << EOF > /etc/systemd/system/mongod-arbiter.service
[Unit]
Description=Arbiter for MongoDB
After=syslog.target network.target

[Service]
Type=forking
User=mongodb
PermissionsStartOnly=true
EnvironmentFile=/etc/sysconfig/mongod-arbiter
ExecStartPre=-/usr/bin/mkdir /var/run/mongodb-arbiter
ExecStartPre=/usr/bin/chown -R mongodb:root /var/run/mongodb-arbiter
ExecStart=/usr/bin/mongod $OPTIONS run
ExecStopPost=-/usr/bin/rm -rf /var/run/mongodb-arbiter
PrivateTmp=true
LimitNOFILE=64000
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
```

Create paths for arbiter:

```
mkdir /var/lib/mongodb-arbiter
chown mongodb:root /var/lib/mongodb-arbiter
chmod 750 /var/lib/mongodb-arbiter
```

Start the arbiter service:

```
systemctl start mongodb-arbiter
```

Once arbiter is live, you need to add it to MongoDB's replicaset. Connect to mongo shell with root priviledges:

```
mongo -u root -p <password> --authenticationDatabase admin
```

Add arbiter to replica's config:

```
rs.addArb("10.30.255.254:27018")
```

Check status:
```
luna:PRIMARY> rs.status()
```

At this point you are ready to copy data and configuration to the other node.

Shutdown the arbiter on the first node:

```
systemctl stop mongod-arbiter
```

Copy the configuration files:

```
for f in /etc/mongod-arbiter.conf /etc/sysconfig/mongod-arbiter /etc/systemd/system/mongod-arbiter.service /var/lib/mongodb-arbiter; do scp -pr $f master2:$f ; done
```

On the second node fix ownership and permissions:

```
chown -R mongodb:root /var/lib/mongodb-arbiter
chmod 750 /var/lib/mongodb-arbiter
```

Bring floating ip down on first node:

```
ip a del 10.30.255.254/16 dev eth1
```
And bring it up on second

```
ip a add 10.30.255.254/16 dev eth1
```

Run the arbiter on the second node

```
systemctl start mongod-arbiter
```

Connect to mongo shell and make sure that you have all instances up:

```
luna:PRIMARY> rs.status()
```
