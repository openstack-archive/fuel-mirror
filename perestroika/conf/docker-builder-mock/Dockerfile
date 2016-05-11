FROM centos:centos7
# Authors: Dmitry Burmistrov <dburmistrov@mirantis.com>
MAINTAINER Dmitry Burmistrov <dburmistrov@mirantis.com>


RUN yum -y --disableplugin=fastestmirror install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm && \
    yum -y --disableplugin=fastestmirror install mock yum-plugin-priorities && \
    yum clean all && \
    useradd abuild -g mock
