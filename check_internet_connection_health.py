import logging
import logging.handlers
import os
import json
import sys
import threading
import subprocess
import socket
import time
from datetime import datetime

sleep_time = 10

def setup_logger(level):
    APPNAME = 'internet_connection_monitor'
    logger = logging.getLogger(APPNAME)
    logger.propagate = False
    logger.setLevel(level)

    log_path = os.path.join(os.getcwd(), 'internet_connection_monitor.log')
    file_handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=2500000, backupCount=5)
    
    # Expecting a simple message string; the log message itself will be JSON-formatted
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream Handler for writing logs to stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


logger = setup_logger(logging.INFO)

# Initialize a lock and shared state
state_lock = threading.Lock()
connection_states = {
    'ping': {'last_state': None, 'connection_start_time': None},
    'tcp': {'last_state': None, 'connection_start_time': None},
    'dns': {'last_state': None, 'connection_start_time': None},
}

def update_state(strategy, state, connection_start_time=None):
    with state_lock:
        connection_states[strategy]['last_state'] = state
        if connection_start_time:
            connection_states[strategy]['connection_start_time'] = connection_start_time

def get_state(strategy):
    with state_lock:
        return connection_states[strategy]['last_state'], connection_states[strategy]['connection_start_time']


max_elapsed_time_refresh_event_secs = 30

# Example usage within a check function (e.g., ping_server)
def ping_server(address):
    last_state, connection_start_time = get_state('ping')
    while True:
        try:
            subprocess.check_output(["ping", "-c", "1", address], timeout=10)
            if last_state == 'down' or last_state is None:
                message = json.dumps({'strategy': 'ping', 'details': f"Connection restored (via ping to {address})", 'status': 'restored'})
                logger.info(message)
                connection_start_time = datetime.now()
            elif connection_start_time and (datetime.now() - connection_start_time).seconds >= max_elapsed_time_refresh_event_secs:
                message = json.dumps({'strategy': 'ping', 'details': f"Connection stable for {(datetime.now() - connection_start_time).seconds} seconds (via ping to {address})", 'status': 'stable'})
                logger.info(message)
            last_state = 'up'
        except subprocess.CalledProcessError:
            if last_state == 'up' or last_state is None:
                message = json.dumps({'strategy': 'ping', 'details': f"Connection lost (via ping to {address})", 'status': 'lost'})
                logger.info(message)
            else:
                message = json.dumps({'strategy': 'ping', 'details': f"Connection still down (via ping to {address})", 'status': 'still down'})
                logger.info(message)
            last_state = 'down'
            connection_start_time = None
        time.sleep(sleep_time)

        
      
def tcp_check(server_info):
    last_state, connection_start_time = get_state('tcp')
    while True:
        try:
            with socket.create_connection(server_info, timeout=10):
                if last_state == 'down' or last_state is None:
                    message = json.dumps({'strategy': 'tcp', 'details': f"TCP connection established with {server_info[0]}", 'status': 'restored'})
                    logger.info(message)
                    connection_start_time = datetime.now()
                    update_state('tcp', 'up', connection_start_time)
                elif connection_start_time and (datetime.now() - connection_start_time).seconds >= max_elapsed_time_refresh_event_secs:
                    message = json.dumps({'strategy': 'tcp', 'details': f"TCP connection stable for {(datetime.now() - connection_start_time).seconds} seconds with {server_info[0]}", 'status': 'stable'})
                    logger.info(message)
                last_state = 'up'
        except OSError:
            if last_state == 'up' or last_state is None:
                message = json.dumps({'strategy': 'tcp', 'details': f"Failed to establish TCP connection with {server_info[0]}", 'status': 'lost'})
                logger.info(message)
            else:
                message = json.dumps({'strategy': 'tcp', 'details': f"TCP connection still down with {server_info[0]}", 'status': 'still down'})
                logger.info(message)
            last_state = 'down'
            connection_start_time = None
        time.sleep(sleep_time)


def dns_check(hostname):
    last_state, connection_start_time = get_state('dns')
    while True:
        try:
            socket.gethostbyname(hostname)
            if last_state == 'down' or last_state is None:
                message = json.dumps({'strategy': 'dns', 'details': f"DNS resolution successful for {hostname}", 'status': 'restored'})
                logger.info(message)
                connection_start_time = datetime.now()
                update_state('dns', 'up', connection_start_time)
            elif connection_start_time and (datetime.now() - connection_start_time).seconds >= max_elapsed_time_refresh_event_secs:
                message = json.dumps({'strategy': 'dns', 'details': f"DNS resolution stable for {(datetime.now() - connection_start_time).seconds} seconds for {hostname}", 'status': 'stable'})
                logger.info(message)
            last_state = 'up'
        except (socket.error, socket.gaierror):
            if last_state == 'up' or last_state is None:
                message = json.dumps({'strategy': 'dns', 'details': f"DNS resolution failed for {hostname}", 'status': 'lost'})
                logger.info(message)
            else:
                message = json.dumps({'strategy': 'dns', 'details': f"DNS resolution still failing for {hostname}", 'status': 'still down'})
                logger.info(message)
            last_state = 'down'
            connection_start_time = None
        time.sleep(sleep_time)




servers_to_ping = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
tcp_test_server = ("google.com", 80)
hostnames_to_resolve = ["google.com", "amazon.com", "facebook.com"]


for server in servers_to_ping:
    threading.Thread(target=ping_server, args=(server,), daemon=True).start()

threading.Thread(target=tcp_check, args=(tcp_test_server,), daemon=True).start()

# Update your loop to start a DNS check thread for each hostname
for hostname in hostnames_to_resolve:
    threading.Thread(target=dns_check, args=(hostname,), daemon=True).start()


while True:
    time.sleep(10)