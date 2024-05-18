import socket
from _thread import *
from threading import Thread
import os
import time
import json
import random
import os
import glob
import sys
import hashlib

class contentMain:
    def __init__(self):
        self.users = {}
        self.host = "x"
        self.port = 0
        self.intt = 0
        self.name = "ContentNode" + str(random.randint(1, 999))
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bootstrap_node = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not os.path.exists('users.json'):
            # If the file doesn't exist, create it with an empty dictionary
            with open('users.json', 'w') as f:
                json.dump({}, f)
        # Load user credentials from the file
        with open('users.json', 'r') as f:
            self.user_credentials = json.load(f)

    def sendToBootstrap(self, ip, port, command, message):
        try:
            bootstrap_node = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bootstrap_node.connect((ip, port))
            time.sleep(1)  # Wait for the connection to be established
            bootstrap_node.send((str(command) + ' ' + str(message)).encode('utf-8'))
            bootstrap_node.close()
            print("Data sent to bootstrap node")
        except ConnectionRefusedError:
            print("Bootstrap node is not available")
            time.sleep(1)
            self.sendToBootstrap(ip, port, command, message)

    def disconnect(self, conn, addr):
        try:
            print(f"User disconnected for ContentNode: {addr}")
            if conn in self.users:
                del self.users[conn]
            self.sendToBootstrap(socket.gethostbyname(socket.gethostname()), 50001, "reducecount", self.name)
        except Exception as e:
            print(f"Error on disconnection: {e}")

    def sendData(self, conn, command, message):
        try:
            full_message = str(command) + ' ' + str(message)
            full_message = full_message.encode('utf-8')
            if conn == 0:
                self.bootstrap_node.send(full_message)
            else:
                conn.send(full_message)
        except Exception as e:
            print(f"Error sending message: {e}")
            
    def listMp3Files(self, conn):
        # Get the 'music' directory
        music_directory = os.path.join(os.getcwd(), 'music')
        # Get all MP3 files in the 'music' directory
        mp3_files = glob.glob(os.path.join(music_directory, '*.mp3'))
        mp3_files_str = ', '.join(mp3_files)
        self.sendData(conn, "displaymessage", mp3_files_str)
        
    def send_mp3_file(self, conn, filename):
        try:
            # Get the size of the file
            file_path = os.path.join('music', filename)
            file_size = os.path.getsize(file_path)
            
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            checksum = hash_md5.hexdigest()

            # Send the "getfile" command, the filename, and the file size
            conn.sendall(b"sendfile " + filename.encode('utf-8') + b" " + checksum.encode('utf-8') + b" " + str(file_size).encode('utf-8'))

            # Open the file in binary mode
            with open(file_path, 'rb') as file:
                # Read the file
                data = file.read()
                # Send the file over the socket
                conn.sendall(data)

            print("Finished sending file")
        except Exception as e:
            print(f"Error sending file: {e}")

    def dataProcessor(self, conn, addr):
        self.sendData(conn, "displaymessage", f"Connected to: " + self.name + "(" + str(self.host) + ":" + str(self.port) + ")")
        while True:
            try:
                # Check for data from connected clients
                if(conn in self.users):
                    try:
                        rData = conn.recv(1024).decode('utf-8')
                        command, message = rData.split(' ', 1)
                        match command:
                            case "return":
                                self.sendData(conn, "connectto", (50001, socket.gethostbyname(socket.gethostname())))
                            case "listfiles":
                                self.listMp3Files(conn)
                            case "getfile":
                                self.send_mp3_file(conn, message)
                            case "close":
                                sys.exit()

                    except Exception as e:
                        print(f"Error processing recieved data from {addr}: {e}")
                        self.disconnect(conn, addr)
                        return
                        
                else:
                    #Runs if the user has never been seen before. This is done by checking the user dictionary.
                    try:
                        print(f"New client registered: {addr}")
                        self.users[conn] = {"Guest"}
                    except Exception as e:
                        print(f"Error sending message: {e}")

            except Exception as e:
                print(f"Error in data processing: {e}")
                return

    def startServer(self):
        try:
            self.host = socket.gethostbyname(socket.gethostname())
            self.port = 50000 + self.intt
            try:
                self.server.bind((self.host, self.port))
            except:
                self.intt+=1
                self.startServer()
            self.server.listen()
            self.port = self.server.getsockname()[1]
            print(f"Content node listening on {(self.host, self.port)} as {self.name}")

            self.sendToBootstrap(socket.gethostbyname(socket.gethostname()), 50001, "register", ("ContentNode" + " " + self.name + " "  + str(self.host) + " " + str(self.port)))  # Set your bootstrap node's IP and port

            while True:
                try:
                    conn, addr = self.server.accept()
                    start_new_thread(self.dataProcessor, (conn, addr))
                    
                except KeyboardInterrupt:
                    print("Caught keyboard interrupt, exiting")

        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.server.close()
            self.bootstrap_node.close()
    
    def startNode(self):
        self.startServer()  # Set the host and port for the load balancer

if __name__ == "__main__":
    contentNode = contentMain()
    contentNodeThread = Thread(target = contentNode.startNode, args =())
    contentNodeThread.start()
    while True:
        pass