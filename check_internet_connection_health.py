import logging
import logging.handlers
import os
import json
import sys
import threading
import subprocess
import socket
import time

sleep_time = 10

def setup_logger(level):
    APPNAME = 'internet_connection_monitor'
    logger = logging.getLogger(APPNAME)
    logger.propagate = False
    logger.setLevel(level)

    # File Handler for writing logs to a file
    log_path = os.path.join(os.getcwd(), 'internet_connection_monitor.log')
    file_handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=2500000, backupCount=5)
    formatter = logging.Formatter(
        json.dumps({
            'time': '%(asctime)s',
            'level': '%(levelname)s',
            'app': APPNAME,
            'details': '%(message)s'
        })
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream Handler for writing logs to stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

logger = setup_logger(logging.INFO)

def ping_server(address):
    while True:
        try:
            subprocess.check_output(["ping", "-c", "1", address], timeout=10)
        except subprocess.CalledProcessError:
            logger.info({'details': f"Ping check failed for {address}"})
        time.sleep(sleep_time)

def tcp_check(server_info):
    while True:
        try:
            with socket.create_connection(server_info, timeout=10):
                pass
        except OSError:
            logger.info({'details': f"Failed to establish TCP connection with {server_info[0]}"})
        time.sleep(sleep_time)

servers_to_ping = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
tcp_test_server = ("google.com", 80)

for server in servers_to_ping:
    threading.Thread(target=ping_server, args=(server,), daemon=True).start()

threading.Thread(target=tcp_check, args=(tcp_test_server,), daemon=True).start()

while True:
    time.sleep(10)