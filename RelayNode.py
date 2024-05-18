import socket
from _thread import *
from threading import Thread
import os
import time
import json
import random
import os
import sys
import AuthNode
import ContentNode

class relayMain:
    def __init__(self):
        self.users = {}
        self.host = "x"
        self.port = 0
        self.intt = 0
        self.name = "RelayNode" + str(random.randint(1, 999))
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
            print(f"User disconnected from RelayNode: {addr}")
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
            
    def spawnAuthNode(self):
        start_new_thread(AuthNode.authMain().startNode, ())
        
    def spawnContentNode(self):
        start_new_thread(ContentNode.contentMain().startNode, ())
        print("Content node started")

    def dataProcessor(self, conn, addr):
        self.sendData(conn, "displaymessage", f"Connected to: " + self.name + "(" + str(self.host) + ":" + str(self.port) + ")")
        while True:
            try:
                # Check for data from connected clients
                if(conn in self.users):
                    try:
                        rData = conn.recv(1024).decode('utf-8')
                        command, message = rData.split(' ', 1)
                        print(command, message)
                        match command:
                            case "spawnContentNode":
                                self.spawnContentNode()
                            case "spawnAuthNode":	
                                self.spawnAuthNode()
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
            print(f"Relay node listening on {(self.host, self.port)} as {self.name}")

            self.sendToBootstrap(socket.gethostbyname(socket.gethostname()), 50001, "register", ("RelayNode" + " " + self.name + " "  + str(self.host) + " " + str(self.port)))  # Set your bootstrap node's IP and port

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
    relayNode = relayMain()
    relayNodeThread = Thread(target = relayNode.startNode, args =())
    relayNodeThread.start()
    while True:
        pass