import socket
import sys
import os
import time
from signal import signal, SIGINT

class NoDeviceError(Exception):

    def __init__(self, device_name):
        self.device_name = device_name
    
    def __str__(self):
        return "NoDeviceError: This experiment doesn't have a device, '{0}'".format(self.device_name)

class Experiment(object):

    def __init__(self):
        self.devices = {}
        self.socket_path = ''
        self.socket = None
        self.connection = None
        self.client_address = None

    def add_device(self, device):
        self.devices[device.name] = device
    
    def set_socket_path(self, path):
        self.socket_path = path
    
    def __wait_to_connect(self):
        print("Awaiting Connection...")
        while True:
            try:
                self.connection, self.client_address = self.socket.accept()
                print("Client Address is {0}".format(self.client_address))
                self.__data_connection(self.connection)
                time.sleep(0.01)
            except socket.timeout:
                continue
            except socket.error as err:
                print("Socket Error: {0}".format(err))
                break

    def __data_connection(self, connection):
        while True:
            try:
                while True:
                    data = self.connection.recv(1024)
                    if data:
                        self.command_handler(data)
                    else:
                        break
                    time.sleep(0.01)
            except socket.error as err:
                print("Connected Socket Error: {0}".format(err))
                return
            finally:
                self.close_handler()
    
    def device_names(self):
        names = []
        for device_name in self.devices:
            names.append(device_name)
        return names

    def command_handler(self, data):
        data = data.decode('utf-8')
        device_name, command, params = data.strip().split("/")
        params = params.split(",")
        if device_name not in self.devices:
            raise NoDeviceError(device_name)
        self.devices[device_name].cmd_handler(command, params)
        

    def exit_handler(self, signal_received, frame):
        print("\r\nAttempting to exit")
        if self.socket is not None:
            self.socket.close()
        for device_name, device in self.devices.items():
            device.reset()
            device.cleanup()
        print("Everything shutdown properly. Exiting.")
        exit(0)
    
    def close_handler(self):
        if self.connection is not None:
            self.connection.close()
        for device_name, device in self.devices.items():
            device.reset()


    def setup(self):
        try:
            if not os.path.exists(self.socket_path):
                f = open(self.socket_path, 'w')
                f.close()
            os.unlink(self.socket_path)
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            signal(SIGINT, self.exit_handler)
            self.socket.bind(self.socket_path)
            self.socket.listen(1)
            self.socket.settimeout(1)
            self.__wait_to_connect()
        except OSError:
            if os.path.exists(self.socket_path):
                print("Error accessing {0}\nTry running 'sudo chown pi: {0}'".format(self.socket_path))
                os._exit(0)
                return
            else:
                print("Socket file not found. Did you configure uv4l-uvc.conf to use {0}?".format(self.socket_path))
                raise
        except socket.error as err:
            print("socket error: {0}".format(err))



    
    