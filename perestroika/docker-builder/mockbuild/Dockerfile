FROM centos:centos7
# Authors: Dmitry Burmistrov <dburmistrov@mirantis.com>
#          Igor Gnatenko <ignatenko@mirantis.com>
MAINTAINER Igor Gnatenko <ignatenko@mirantis.com>


RUN yum -y --disableplugin=fastestmirror install http://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm && \
    yum -y --disableplugin=fastestmirror install --enablerepo=epel-testing mock && \
    yum clean --enablerepo=epel-testing all && \
    useradd abuild -g mock

COPY mock_configure.sh /
RUN /mock_configure.sh; \
    rm -f /mock_configure.sh
