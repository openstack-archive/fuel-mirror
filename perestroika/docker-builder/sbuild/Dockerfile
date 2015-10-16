FROM ubuntu:trusty
MAINTAINER dburmistrov@mirantis.com

ENV MIRROR http://mirror.yandex.ru/ubuntu
ENV NAMESERV 172.18.80.136
ENV DIST trusty
ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN true

VOLUME ["/srv/images", "/srv/source"]

COPY sbuild-key.pub /var/lib/sbuild/apt-keys/sbuild-key.pub
COPY sbuild-key.sec /var/lib/sbuild/apt-keys/sbuild-key.sec

RUN rm -f /etc/apt/sources.list.d/proposed.list && \
    echo -e "\nnameserver $NAMESERV\n" >> /etc/resolv.conf && \
    echo "deb $MIRROR $DIST main universe multiverse restricted" > /etc/apt/sources.list && \
    echo "deb $MIRROR $DIST-updates main universe multiverse restricted" >> /etc/apt/sources.list && \
    apt-get update && apt-get -y install sbuild debhelper && \
    apt-get clean && \
    mkdir -p /srv/build && \
    sed -i '/^1/d' /etc/sbuild/sbuild.conf && \
    echo "\$build_arch_all = 1;" >> /etc/sbuild/sbuild.conf && \
    echo "\$log_colour = 0;" >> /etc/sbuild/sbuild.conf && \
    echo "\$apt_allow_unauthenticated = 1;" >> /etc/sbuild/sbuild.conf && \
    echo "\$apt_update = 0;" >> /etc/sbuild/sbuild.conf && \
    echo "\$apt_clean = 0;" >> /etc/sbuild/sbuild.conf && \
    echo "\$build_source = 1;" >> /etc/sbuild/sbuild.conf && \
    echo "\$build_dir = '/srv/build';" >> /etc/sbuild/sbuild.conf && \
    echo "\$log_dir = '/srv/build';" >> /etc/sbuild/sbuild.conf && \
    echo "\$stats_dir = '/srv/build';" >> /etc/sbuild/sbuild.conf && \
    echo "\$verbose = 100;" >> /etc/sbuild/sbuild.conf && \
    echo "\$mailprog = '/bin/true';" >> /etc/sbuild/sbuild.conf && \
    echo "\$purge_build_deps = 'never';" >> /etc/sbuild/sbuild.conf && \
    echo "1;" >> /etc/sbuild/sbuild.conf

COPY ./04tmpfs /etc/schroot/setup.d/04tmpfs
RUN chmod +x /etc/schroot/setup.d/04tmpfs

COPY ./precise-amd64-sbuild /etc/schroot/chroot.d/precise-amd64-sbuild
COPY ./trusty-amd64-sbuild /etc/schroot/chroot.d/trusty-amd64-sbuild
