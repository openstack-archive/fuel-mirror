FROM ubuntu:trusty
# Authors: Dmitry Burmistrov <dburmistrov@mirantis.com>
MAINTAINER Dmitry Burmistrov <dburmistrov@mirantis.com>

ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN true

COPY ./sbuild-key.pub /var/lib/sbuild/apt-keys/sbuild-key.pub
COPY ./sbuild-key.sec /var/lib/sbuild/apt-keys/sbuild-key.sec

RUN rm -f /etc/apt/sources.list.d/proposed.list && \
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
