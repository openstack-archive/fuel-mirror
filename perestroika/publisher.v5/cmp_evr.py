import os
from rpmUtils import miscutils

S = os.environ

# Results:
#  1 - A is newer than B
#  0 - A and B have the same version
# -1 - A is older than B

print miscutils.compareEVR(
    (S['A_EPOCH'], S['A_VERSION'], S['A_RELEASE']),
    (S['B_EPOCH'], S['B_VERSION'], S['B_RELEASE']))
