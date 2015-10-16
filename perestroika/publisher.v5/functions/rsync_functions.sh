#!/bin/bash -xe

export LANG=C

# define this vars before use
SNAPSHOT_FOLDER=${SNAPSHOT_FOLDER:-"snapshots"}
LATESTSUFFIX=${LATESTSUFFIX:-"-latest"}

export DATE=$(date "+%Y-%m-%d-%H%M%S")
export SAVE_LAST_DAYS=${SAVE_LAST_DAYS:-61}
export WARN_DATE=$(date "+%Y%m%d" -d "$SAVE_LAST_DAYS days ago")

function get_empty_dir() {
    echo $(mktemp -d)
}

function get_symlink() {
    local LINKDEST=$1
    local LINKNAME=$(mktemp -u)
    ln -s --force $LINKDEST $LINKNAME && echo $LINKNAME
}

function rsync_delete_file() {
    local RSYNCHOST=$1
    local RSYNCUSER=$2
    local FILENAME=$(basename $3)
    local FILEPATH=$(dirname $3)
    local EMPTYDIR=$(get_empty_dir)
    rsync -rv --delete --include=$FILENAME '--exclude=*' \
        $EMPTYDIR/ $RSYNCHOST::$RSYNCUSER/$FILEPATH/
    [ ! -z "$EMPTYDIR" ] && rm -rf $EMPTYDIR
}

function rsync_delete_dir() {
    local RSYNCHOST=$1
    local RSYNCUSER=$2
    local DIR=$3
    local EMPTYDIR=$(get_empty_dir)
    rsync --delete -a $EMPTYDIR/ $RSYNCHOST::$RSYNCUSER/$DIR/ \
        && rsync_delete_file $RSYNCHOST $RSYNCUSER $DIR
    [ ! -z "$EMPTYDIR" ] && rm -rf $EMPTYDIR
}

function rsync_create_dir() {
    local RSYNCHOST=$1
    local RSYNCUSER=$2
    local DIR=$3
    local EMPTYDIR=$(get_empty_dir)
    local OIFS="$IFS"
    IFS='/'
    local dir=''
    local _dir=''
    for _dir in $DIR ; do
      IFS="$OIFS"
      dir="${dir}/${_dir}"
      rsync -a $EMPTYDIR/ $RSYNCHOST::$RSYNCUSER/$dir/
      IFS='/'
    done
    IFS="$OIFS"
    [ ! -z "$EMPTYDIR" ] && rm -rf $EMPTYDIR
}

function rsync_create_symlink() {
    # Create symlink $3 -> $4
    # E.g. "create_symlink repos/6.1 files/6.1-stable"
    # wll create symlink repos/6.1 -> repos/files/6.1-stable
    local RSYNCHOST=$1
    local RSYNCUSER=$2
    local LINKNAME=$3
    local LINKDEST=$4
    local SYMLINK_FILE=$(get_symlink "$LINKDEST")
    rsync -vl $SYMLINK_FILE $RSYNCHOST::$RSYNCUSER/$LINKNAME
    rm $SYMLINK_FILE

    # Make text file for dereference symlinks
    local TARGET_TXT_FILE=$(mktemp)
    echo "$LINKDEST" > $TARGET_TXT_FILE
    rsync -vl $TARGET_TXT_FILE $RSYNCHOST::$RSYNCUSER/${LINKNAME}.target.txt
    rm $TARGET_TXT_FILE
}

function rsync_list() {
    local RSYNCHOST=$1
    local RSYNCUSER=$2
    local DIR=$3
    local TEMPFILE=$(mktemp)
    set +e
    rsync -l $RSYNCHOST::$RSYNCUSER/$DIR/ 2>/dev/null > $TEMPFILE
    local RESULT=$?
    [ "$RESULT" == "0" ] && cat $TEMPFILE | grep -v '\.$'
    rm $TEMPFILE
    set -e
    return $RESULT
}

function rsync_list_links() {
    local RSYNCHOST=$1
    local RSYNCUSER=$2
    local DIR=$3
    local TEMPFILE=$(mktemp)
    set +e
    rsync_list $RSYNCHOST $RSYNCUSER $DIR > $TEMPFILE
    local RESULT=$?
    [ "$RESULT" == "0" ] && cat $TEMPFILE | grep '^l' | awk '{print $(NF-2)" "$NF}'
    rm $TEMPFILE
    set -e
    return $RESULT
}

function rsync_list_dirs() {
    local RSYNCHOST=$1
    local RSYNCUSER=$2
    local DIR=$3
    local TEMPFILE=$(mktemp)
    set +e
    rsync_list $RSYNCHOST $RSYNCUSER $DIR > $TEMPFILE
    local RESULT=$?
    [ "$RESULT" == "0" ] && cat $TEMPFILE | grep '^d' | awk '{print $NF}'
    rm $TEMPFILE
    set -e
    return $RESULT
}

function rsync_list_files() {
    local RSYNCHOST=$1
    local RSYNCUSER=$2
    local DIR=$3
    local TEMPFILE=$(mktemp)
    set +e
    rsync_list $RSYNCHOST $RSYNCUSER ${DIR} > $TEMPFILE
    local RESULT=$?
    [ "$RESULT" == "0" ] && cat $TEMPFILE | grep -vE '^d|^l' | awk '{print $NF}'
    rm $TEMPFILE
    set -e
    return $RESULT
}

######################################################
function rsync_remove_old_versions() {
    # Remove mirrors older then $SAVE_LAST_DAYS and w/o symlinks on it
    local RSYNCHOST=$1
    local RSYNCUSER=$2
    local REMOTEPATH=$3
    local FOLDERNAME=$4
    DIRS=$(rsync_list_dirs $RSYNCHOST $RSYNCUSER $REMOTEPATH | grep "^$FOLDERNAME\-" )
    for dir in $DIRS; do
        ddate=$(echo $dir | awk -F '[-]' '{print $(NF-3)$(NF-2)$(NF-1)}')
        [ "$ddate" -gt "$WARN_DATE" ] && continue
        LINKS=$(rsync_list_links $RSYNCHOST $RSYNCUSER $REMOTEPATH | grep -F $dir ; rsync_list_links $RSYNCHOST $RSYNCUSER $(dirname $REMOTEPATH) | grep -F "$(basename $REMOTEPATH)/$dir")
        if [ "$LINKS" = "" ]; then
            rsync_delete_dir $RSYNCHOST $RSYNCUSER $REMOTEPATH/$dir
            continue
        fi
        echo "Skip because symlinks $LINKS points to $dir"
    done
}

######################################################
function rsync_transfer() {
    # sync files to remote host
    # $1 - remote host
    # $2 - rsync module
    # $3 - source dir 1/
    # $4 - remote dir 1/2/3/4/5
    # snapshots dir 1/2/3/4/snapshots
    local RSYNC_HOST=$1
    local RSYNC_USER=$2
    local SOURCE_DIR=$3
    local REMOTE_DIR=$4

    local SNAPSHOT_DIR=$(echo $REMOTE_DIR | sed "s|$(basename ${REMOTE_DIR})$|${SNAPSHOT_FOLDER}|")

    local SNAPSHOT_FOLDER=$(basename $SNAPSHOT_DIR) # snapshots
    local SNAPSHOT_PATH=$(dirname $SNAPSHOT_DIR) # 1/2
    local REMOTE_ROOT=$(echo $REMOTE_DIR | sed "s|^$SNAPSHOT_PATH/||")
    local REMOTE_ROOT=${REMOTE_ROOT%%/*} # 3
    rsync_list_dirs $RSYNC_HOST $RSYNC_USER $SNAPSHOT_DIR/${REMOTE_ROOT}-${DATE} \
        || rsync_create_dir $RSYNC_HOST $RSYNC_USER $SNAPSHOT_DIR/${REMOTE_ROOT}-${DATE}

    OPTIONS="--archive --verbose --force --ignore-errors --delete-excluded --no-owner --no-group \
          --delete --link-dest=/${SNAPSHOT_DIR}/${REMOTE_ROOT}${LATESTSUFFIX}"

    rsync ${OPTIONS} ${SOURCE_DIR}/ ${RSYNC_HOST}::${RSYNC_USER}/${SNAPSHOT_DIR}/${REMOTE_ROOT}-${DATE}/ \
       && rsync_delete_file $RSYNC_HOST $RSYNC_USER ${SNAPSHOT_DIR}/${REMOTE_ROOT}${LATESTSUFFIX} \
       && rsync_create_symlink $RSYNC_HOST $RSYNC_USER ${SNAPSHOT_DIR}/${REMOTE_ROOT}${LATESTSUFFIX} ${REMOTE_ROOT}-${DATE} \
       && rsync_delete_file $RSYNC_HOST $RSYNC_USER ${SNAPSHOT_PATH}/${REMOTE_ROOT} \
       && rsync_create_symlink $RSYNC_HOST $RSYNC_USER ${SNAPSHOT_PATH}/${REMOTE_ROOT} ${SNAPSHOT_FOLDER}/${REMOTE_ROOT}-${DATE} \
       && rsync_remove_old_versions $RSYNC_HOST $RSYNC_USER ${SNAPSHOT_DIR} ${REMOTE_ROOT}
    RESULT=$?
    [ $RESULT -ne 0 ] && rsync_delete_dir $RSYNC_HOST $RSYNC_USER ${SNAPSHOT_DIR}/${REMOTE_ROOT}-${DATE}

    return $RESULT
}
