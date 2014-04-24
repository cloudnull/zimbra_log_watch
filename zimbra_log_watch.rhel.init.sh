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

# /etc/init.d/zimbra-log-watch: start and stop the zimbra-log-watch daemon
PROGRAM_NAME="zimbra_log_watch"

# change this line to the full location where you have placed the script
DAEMON="/soft/scripts/zimbra_log_watch.py"

CONFIG_FILE="/etc/zimbra-log-watch/zimbra-log-watch.conf"

PID_FILE="/var/run/${PROGRAM_NAME}.pid"

runlevel=$(set -- $(runlevel); eval "echo \$$#" )
export PATH="${PATH:+$PATH:}/usr/sbin:/sbin"


api_status() {
  if [ -f "$PID_FILE" ];then
    kill -0 $(cat $PID_FILE)
    RUNNING=$?
    if [ $RUNNING -eq 0 ];then
      echo "Process is already running"
      exit 0
    fi
  else
    echo "$PROGRAM_NAME is not running"
  fi
}

api_start() {
  api_status
	echo -n $"Starting $prog: "
	$DAEMON || exit 1 & 2>/dev/null
  PID=$!
	RETVAL=$?
	[ $RETVAL -eq 0 ] && touch $PID_FILE
  echo "$PID" | tee $PID_FILE
	return $RETVAL
}

api_stop() {
  if [ -f "$PID_FILE" ];then
    PID="$(cat $PID_FILE)"
  	echo "Stopping $PROGRAM_NAME: $PID"
  	pkill -TERM -P $PID
    RETVAL=$?
    [ $RETVAL -eq 0 ] && rm -f $PID_FILE
  fi
	
	# if we are in halt or reboot runlevel kill all running sessions
	if [ "x$runlevel" = x0 -o "x$runlevel" = x6 ] ; then
	    trap '' TERM
	    killall $PROGRAM_NAME 2>/dev/null
	    trap TERM
	fi
}


case "$1" in
  start)
        api_start
        ;;
  stop)
        api_stop
        if [ -f "$PID_FILE" ];then
        	rm -f $PID_FILE
        fi
        ;;
  status)
        api_status
        ;;
  *)
        echo "Usage: /etc/init.d/zimbra-log-watch {start|stop|status}"
        exit 1
esac

exit 0
