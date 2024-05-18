import socket
from _thread import *
from threading import Thread
import os
import time
import random
import AuthNode
import ContentNode

class serverMain():

    def __init__(self):
        
        #User dictionaries. _Users holds a list of every user and their conn. When a user first connects the are in unverified. They get moved to verified when they log in.
        self._ContentNodes = {}
        self._AuthNodes = {}
        self._RelayNodes = {}
        self._Users = {}
        self.name = "BootstrapNode"
        self.HOST = "x"
        self.PORT = 50001
        self.targetNode = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #Makes socket accessible to entire class.
        
        self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def Disconnect(self, conn, addr):
        # A function that iterates through each user dictionary, and remove any with the passed conn. It then closes the connection.
        try:
            print(f"User disconnected: {addr}")
            for x in list(self._Users.keys()):  # Create a copy of the keys
                if x == conn:
                    del self._Users[conn]  # Delete the item from the original dictionary
        except Exception as e:
            print(f"5. {e}")
            pass
        
    def SendData(self, conn, command, message):
        #VERY important function. Sends a message to the passed conn.
        try:
            #Adds combines passed elements
            message = str(command) + " " + str(message)
            message = message.encode('utf-8')
            if conn == 0:
                self.targetNode.send(message)
            else:
                conn.send(message)
        except Exception as e:
            print(f"10. {e}")
            pass
        
    def Register(self, conn, message):
        nodeType, name, ip, port = message.split(' ', 3)
        if(nodeType == "AuthNode"):
            self._AuthNodes[name] = [ip, port, 0]
            print("Auth node registered")
            if(len(self._AuthNodes) > 1):
                first_authnode = list(self._AuthNodes.keys())[0]
                ogip, ogport, _ = self._AuthNodes[first_authnode]
                self.SendToSocket(ogip, ogport, "syncdata", (ip + " " + port))
                print("Auth nodes synced")
        elif(nodeType == "ContentNode"):
            self._ContentNodes[name] = [ip, port, 0]
            print("Content node registered")
        elif(nodeType == "RelayNode"):
            self._RelayNodes[name] = [ip, port, 0]
            print("Relay node registered")
        elif(nodeType == "User"):
            self._Users[conn] = {"User"}
            print("User registered")
        else:
            print(nodeType, ip, port)
            
    def RetrieveInfo(self, conn, message):
        # Used to retrieve the IP and port of a node using the libraries.
        for library in [self._AuthNodes, self._ContentNodes]:
            for x in library:
                if str(x) == message:
                    ip, port, count = list(library[x])
                    self.SendData(conn, "displaymessage", (port, ip))
                    return
            
    def SendAuthIP(self, conn, message):
        try:
            # Used to send a user to an auth node.
            if self._AuthNodes:  # Check if _AuthNodes is not empty
                node_name = ""
                for(x) in self._AuthNodes:
                    ip, port, count = list(self._AuthNodes[x])
                    if(int(count) < 1):
                        node_name = x
                        break
                ip, port, count = list(self._AuthNodes[x])
                self.SendData(conn, "connectto", (ip, port))
                count = int(count) + 1
                self._AuthNodes[node_name] = [ip, port, count]
                print("Auth node sent")
                if(count == 1):
                    print("Limit reached, new auth node started")
                    if len(self._AuthNodes) % 2 == 0 and len(self._RelayNodes) >= 1:
                        print("Auth node started remotely")
                        for(x) in self._RelayNodes:
                            ip, port, count = list(self._RelayNodes[x])
                            if(int(count) < 1):
                                node_name = x
                                break
                        ip, port, count = list(self._RelayNodes[x])
                        self.SendToSocket(ip, port, "spawnAuthNode", "please")
                    else:
                        start_new_thread(self.startNodes, ("0"))
                        print("Auth node started")
            else:
                print("No auth nodes available")
        except Exception as e:
            print(f"6. {e}")
            pass
        
    def SendContentIP(self, conn, message):
        # Used to send a user to a content node.
        if self._ContentNodes:  # Check if _ContentNodes is not empty
            # Find the node with the lowest count value that is less than 5
            suitable_nodes = {k: v for k, v in self._ContentNodes.items() if v[2] < 5}
            if suitable_nodes:
                node_name = min(suitable_nodes, key=lambda x: suitable_nodes[x][2])
                ip, port, count = list(self._ContentNodes[node_name])
                self.SendData(conn, "connectto", f"{ip} {port}")
                self._ContentNodes[node_name] = {ip, port, count + 1}
                print("Content node sent")
                if(count == 5):
                    if len(self._ContentNodes) % 2 == 0 and len(self._RelayNodes) > 1:
                        print("Content node started remotely")
                        for(x) in self._RelayNodes:
                            ip, port, count = list(self._RelayNodes[x])
                            if(int(count) < 5):
                                node_name = x
                                break
                        ip, port, count = list(self._RelayNodes[x])
                        self.SendToSocket(ip, port, "spawnContentNode", "please")
                    else:
                        start_new_thread(self.startNodes, ("1"))
                        print("Content node started")
            else:
                print("No suitable content nodes available")
        else:
            print("No content nodes available")
            
    def startNodes(self, nodeType):
        time.sleep(1)
        if(nodeType == "0"):
            start_new_thread(AuthNode.authMain().startNode, ())
            print("Auth node started")
        else:
            start_new_thread(ContentNode.contentMain().startNode, ())
            print("Content node started")
            
    def reduceCount(self, conn, message):
        name = message
        for library in [self._AuthNodes, self._ContentNodes]:
            for x in library:
                if str(x) == name:
                    ip, port, count = list(library[x])
                    count = int(count) - 1
                    library[x] = [ip, port, count]
                    if(count == 0 and len(self._AuthNodes) > 1):
                        self.SendToSocket(ip, port, "close", "null")
                        del library[name]
                        print("Node closed due to lack of users.")
                    return
                
    def SendToSocket(self, ip, port, command, message):
        try:
            self.targetNode.connect((ip, int(port)))
            time.sleep(1)  # Wait for the connection to be established
            self.SendData(0, command, message)
            self.targetNode.close()
            print("Message sent") 
        except ConnectionRefusedError:
            print("Message failed to send")
        

    def Main(self, conn, addr):
        #The main, threaded function.
        while True:
            if(conn in self._Users):
                try:
                    rData = conn.recv(1024).decode("utf-8")
                    #These lines will always run, and pick out the useful parts of the message
                    command, message = rData.split(' ', 1)
                    #Matches the command recieved by the client to call the correct function.
                    match command:
                        case "register": # Register connected client
                            self.Register(conn, message)
                        case "retrieveinfo": # Retrieve port and IP from name
                            self.RetrieveInfo(conn, message)
                        case "authoriserequest": # Send user to an auth node
                            self.SendAuthIP(conn, message)
                        case "playmusic":
                            self.SendContentIP(conn, message)
                        case "reducecount":
                            self.reduceCount(conn, message)

                except Exception as e:
                    #Calls for a disconnect when the main function encounters a significant error, disconnecting the user.
                    print(e)
                    self.Disconnect(conn, addr)
                    return
                
            else:
                #Runs if the user has never been seen before. This is done by checking the user dictionary.
                try:
                    print(f"New client registered: {addr}")
                    self.SendData(conn, "displaymessage", f"Connected to: " + self.name + "(" + str(self.HOST) + ":" + str(self.PORT) + ")")
                    self._Users[conn] = {"Guest"}
                except Exception as e:
                    print(f"5. {e}")
                    pass

    def RunServer(self):
        #Sets up basic sockets and threading.
        threadCount = os.cpu_count()
        hostName = socket.gethostname()
        self.HOST = socket.gethostbyname(hostName)
        self._s.bind((self.HOST, self.PORT))
        self._s.listen()
        print(f"Bootstrap node listening on {(self.HOST, self.PORT)}")  
        
        #Starts the original auth and content nodes.
        start_new_thread(self.startNodes, ("0",))
        start_new_thread(self.startNodes, ("1",))
        
        #Keeps looping. When a user connects, a new thread it created to listen for data.
        while True:
            try:
                conn, addr = self._s.accept()
                start_new_thread(self.Main, (conn, addr))
                    
            except KeyboardInterrupt:
                print("Caught keyboard interrupt, exiting")

if __name__ == "__main__":
    #Creates instance of main class and runs the starter function.
    client = serverMain()
    client.RunServer()