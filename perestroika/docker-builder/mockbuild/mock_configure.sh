#!/bin/bash
# Generate mock configuration files:
#     /etc/mock/centos-7-x86_64.cfg
#     /etc/mock/centos-6-x86_64.cfg
# both for el6, el7,
# Add configuration param:
#     config_opts['macros']['%dist'] = '.${DIST}${DISTSUFFIX}'

set -e

for cfg in /etc/mock/epel-{6,7}-x86_64.cfg; do
    DIST=$(awk -F"'" "/config_opts\['dist'\]/ {print \$4}" "${cfg}")
    sed -e "/config_opts\['dist'\]/s/$/\nconfig_opts['macros']['%dist'] = '.${DIST}${DISTSUFFIX}'/" $cfg \
        >${cfg/epel/centos}
done
# Enable tmpfs mock plugin
cat > /etc/mock/site-defaults.cfg <<HEREDOC
config_opts['plugin_conf']['tmpfs_enable'] = True
config_opts['plugin_conf']['tmpfs_opts'] = {}
config_opts['plugin_conf']['tmpfs_opts']['required_ram_mb'] = 2048
config_opts['plugin_conf']['tmpfs_opts']['max_fs_size'] = '25g'
config_opts['plugin_conf']['tmpfs_opts']['mode'] = '0755'
config_opts['plugin_conf']['tmpfs_opts']['keep_mounted'] = False
HEREDOC
