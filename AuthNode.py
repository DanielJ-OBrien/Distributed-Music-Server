import socket
from _thread import *
from threading import Thread
import os
import time
import json
import random
import sys

class authMain:
    def __init__(self):
        self.users = {}
        self.host = "x"
        self.port = 0
        self.intt = 0
        self.name = "AuthNode" + str(random.randint(1, 999))
        self.authenticatedusers = {}
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
            print(f"User disconnected for AuthNode: {addr}")
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
            
    def login(self, conn, username, password):
        # Check if the username and password are correct
        if self.user_credentials.get(username) == password:
            # If the login is successful, store the user's connection and username
            self.authenticatedusers[conn] = username
            return True
        else:
            return False
        
    def register(self, username, password):
        # Check if the username is already taken
        if username in self.user_credentials:
            return False
        else:
            # Add the new user credentials
            self.user_credentials[username] = password
            # Save the updated user credentials to the file
            with open('users.json', 'w') as f:
                json.dump(self.user_credentials, f)
            return True
        
    def syncData(self, conn, message):
        # Iterates through login details in JSON file and sends them to the provided IP and PORT
        ip, port = message.split(' ', 1)
        for user in self.user_credentials:
            self.sendToBootstrap(ip, int(port), "register", (user + " " + self.user_credentials[user]))

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
                                self.sendData(conn, "connectto", (socket.gethostbyname(socket.gethostname()) + " " + str(50001)))
                            case "login":
                                username, password = message.split(' ', 1)
                                if self.login(conn, username, password):
                                    self.sendData(conn, "login", "True")
                                    self.sendData(conn, "displaymessage", "Logged in")
                                else:
                                    self.sendData(conn, "displaymessage", "Login failed")
                            case "register":
                                username, password = message.split(' ', 1)
                                if self.register(username, password):
                                    self.sendData(conn, "displaymessage", "Registered successfully. Please login")
                                else:
                                    self.sendData(conn, "displaymessage", "Registration failed")
                            case "close":
                                sys.exit()
                            case "syncdata":
                                self.syncData(conn, message)

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
            print(f"Authentiction node listening on {(self.host, self.port)} as {self.name}")

            self.sendToBootstrap(socket.gethostbyname(socket.gethostname()), 50001, "register", ("AuthNode" + " " + self.name + " "  + str(self.host) + " " + str(self.port)))  # Set your bootstrap node's IP and port

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
    authNode = authMain()
    authNodeThread = Thread(target = authNode.startNode, args =())
    authNodeThread.start()
    while True:
        pass