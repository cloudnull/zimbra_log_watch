#! /usr/bin/env bash

### BEGIN INIT INFO
# Provides:          Zimbra Log Watch
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Should-Start:      $named
# Default-Start:     2 3 4 5
# Default-Stop:
# Short-Description: Zimbra Log Watch
# Description:       Zimbra Log Watch
### END INIT INFO

set -e

# /etc/init.d/zimbra-log-watch: start and stop the zimbra-log-watch daemon
PROGRAM_NAME="zimbra-log-watch"

DAEMON="/root/scripts/${PROGRAM_NAME}"

CONFIG_FILE="/etc/zimbra-log-watch/zimbra-log-watch.conf"

PID_FILE="/var/run/${PROGRAM_NAME}.pid"

DAEMON_APP="start-stop-daemon || daemon"

source /lib/lsb/init-functions
export PATH="${PATH:+$PATH:}/usr/sbin:/sbin"

api_start() {
    if [ ! -s "$CONFIG_FILE" ]; then
        log_failure_msg "missing or empty config file $CONFIG_FILE"
        log_end_msg 1
        exit 0
    fi
        if start-stop-daemon --start --quiet --background \
        --pidfile $PID_FILE --make-pidfile --exec $DAEMON
    then
        rc=0
        sleep 1
        if ! kill -0 $(cat $PID_FILE) >/dev/null 2>&1; then
            rc=1
        fi
    else
        rc=1
    fi

    if [ $rc -eq 0 ]; then
        log_end_msg 0
    else
        log_failure_msg "${PROGRAM_NAME} daemon failed to start"
        log_end_msg 1
        rm -f $PID_FILE
    fi
}


case "$1" in
  start)
        log_daemon_msg "Starting ${PROGRAM_NAME} daemon" "${PROGRAM_NAME}"
        if [ -s $PID_FILE ] && kill -0 $(cat $PID_FILE) >/dev/null 2>&1; then
            log_progress_msg "zimbra-log-watch is already running"
            log_end_msg 0
            exit 0
        fi
        api_start
        ;;
  stop)
        log_daemon_msg "Stopping ${PROGRAM_NAME} daemon" "${PROGRAM_NAME}"
        start-stop-daemon --stop --quiet --oknodo --pidfile $PID_FILE
        log_end_msg $?
        rm -f $PID_FILE
        ;;
  restart)
        set +e
        log_daemon_msg "Restarting ${PROGRAM_NAME} daemon" "${PROGRAM_NAME}"
        if [ -s $PID_FILE ] && kill -0 $(cat $PID_FILE) >/dev/null 2>&1; then
            start-stop-daemon --stop --quiet --oknodo --pidfile $PID_FILE || true
            sleep 1
        else
            log_warning_msg "${PROGRAM_NAME} daemon not running, attempting to start."
            rm -f $PID_FILE
        fi
        api_start
        ;;

  status)
        status_of_proc -p $PID_FILE "$DAEMON" zimbra-log-watch
        exit $?
        ;;
  *)
        echo "Usage: /etc/init.d/zimbra-log-watch {start|stop|restart|status}"
        exit 1
esac

exit 0
