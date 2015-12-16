====================
Repository structure
====================

* contrib/fuel_mirror
  It is a command line utility that provides the same functionality
  and user interface as deprecated fuel-createmirror. It provides
  two major features:
  * clone/build mirror (full or partial)
  * update repository configuration in nailgun
  First one is a matter of packetary while second one should be left
  totally up to fuelclient. So this module is to be deprecated soon
  in favor of packetary and fuelclient.

  WARNING: It is not designed to be used on 'live' repositories
  that are available to clients during synchronization. That means
  repositories will be inconsistent during the update. Please use these
  scripts in conjunction with snapshots, on inactive repos, etc.

* debian
  Specs for DEB packages.

* doc
  Documentation for packetary module.

* packetary
  It is a Python library and command line utilty that allows
  one to clone and build rpm/deb repositories.
  Features:
  * Common interface for different package-managers.
  * Utility to build dependency graph for package(s).
  * Utility to create mirror of repository according to dependency graph.

* perestroika
  It is a set shell/python script that are used to build DEB/RPM
  packages. These scripts are widely used by Fuel Packaging CI.

* specs
  Specs for RPM packages.
