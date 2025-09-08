#!/bin/bash

# Aterx Daemon startup script
# Usage: ./start_aterxdaemon.sh [start|stop|restart|status|test]

DAEMON_NAME="aterxdaemon"
DAEMON_PATH="/home/monero/p2pooler/python"
DAEMON_SCRIPT="$DAEMON_PATH/aterxdaemon.py"
VENV_PATH="/home/monero/p2pooler/venv"
PID_FILE="/var/run/$DAEMON_NAME.pid"
LOG_FILE="/var/log/$DAEMON_NAME.log"

# Source virtual environment if it exists
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
fi

start_daemon() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "$DAEMON_NAME is already running (PID: $(cat $PID_FILE))"
        return 1
    fi
    
    echo "Starting $DAEMON_NAME..."
    cd "$DAEMON_PATH"
    
    nohup python3 "$DAEMON_SCRIPT" --daemon > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 2
    if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "$DAEMON_NAME started successfully (PID: $(cat $PID_FILE))"
    else
        echo "Failed to start $DAEMON_NAME"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_daemon() {
    if [ ! -f "$PID_FILE" ]; then
        echo "$DAEMON_NAME is not running"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    echo "Stopping $DAEMON_NAME (PID: $PID)..."
    
    if kill -TERM "$PID" 2>/dev/null; then
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            echo "Force killing $DAEMON_NAME..."
            kill -KILL "$PID" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        echo "$DAEMON_NAME stopped"
    else
        echo "$DAEMON_NAME was not running"
        rm -f "$PID_FILE"
    fi
}

status_daemon() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "$DAEMON_NAME is running (PID: $(cat $PID_FILE))"
    else
        echo "$DAEMON_NAME is not running"
        if [ -f "$PID_FILE" ]; then
            rm -f "$PID_FILE"
        fi
    fi
}

test_daemon() {
    echo "Testing $DAEMON_NAME configuration..."
    cd "$DAEMON_PATH"
    python3 "$DAEMON_SCRIPT" --test
}

case "$1" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        stop_daemon
        sleep 2
        start_daemon
        ;;
    status)
        status_daemon
        ;;
    test)
        test_daemon
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|test}"
        exit 1
        ;;
esac