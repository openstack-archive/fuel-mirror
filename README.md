fuel-createmirror
=================

Script for partial deb repositories mirroring with sanity check.



# Description

WARNING: This set of scripts is not designed to be used on 'live' repositories
that are available to clients during synchronization, because it violates
common synchronization order (packages first, metadata later) to provide
partial mirroring capability. It means that repositories will be
inconsistent during the update. Please use these scripts in conjunction
with snapshots, on inactive repos, etc.

Only rsync mirrors are supported.