import socket
import sys
import time
import os
import re
import subprocess
import json


from mininet.log import info

try:
    import sim
except ImportError:
    info('--------------------------------------------------------------')
    info('"sim.py" could not be imported. This means very probably that')
    info('either "sim.py" or the remoteApi library could not be found.')
    info('Make sure both are in the same folder as this file,')
    info('or appropriately adjust the file "sim.py"')
    info('--------------------------------------------------------------')
    sys.exit()

def send_ping_command(target_ip='10.0.0.2'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(('192.168.15.76', 12345))
            # Envio do comando ping
            command = f"ping 10.0.0.2"
            #command = ["ping", "-c", "1", "{target_ip}"]
            print(f"Sending command: {command}")
            sock.sendall(command.encode('utf-8'))
            full_response = sock.recv(4096).decode('utf-8', errors='ignore')
            print("Full response received:", full_response)
            
            # Extrai todos os tempos de resposta usando expressões regulares
            response_times = re.findall(r'time=(\d+\.\d+) ms', full_response)
            if response_times:
                # Juntando todos os tempos de resposta em uma string formatada
                response_times_str = ", ".join([f"time={time} ms" for time in response_times])### jeito certo join([f"{time}" for time in response_times])
                #print("Response times:", response_times_str)
                return response_times_str
            else:
                print("No ping response time found.")
                return "No response time found."
            
        except ConnectionRefusedError:
            print("Failed to connect to the server. Is the Mininet-WiFi script running?")
            return "Ping Failed"





def drone_position(args):
    drones = [[] for _ in range(1)]
    drones_names = ['Quadricopter_base']
    nodes = []
    data = [[] for _ in range(1)]
    ping_count = 0
    max_pings = 1
    pings_done = False
    control = True

    if len(args) > 1:
        nodes = args[1:]
    else:
        info("No nodes defined")
        sys.exit()

    info('Program started')
    sim.simxFinish(-1)
    clientID = sim.simxStart('192.168.15.76', 12345, True, True, 5000, 5)

    if clientID != -1:
        info('Connected to remote API server')
        for i in range(len(drones)):
            _, drones[i] = sim.simxGetObjectHandle(clientID, drones_names[i], sim.simx_opmode_oneshot_wait)

        time.sleep(2)

        for drone in drones:
            sim.simxGetObjectPosition(clientID, drone, -1, sim.simx_opmode_streaming)

        while control == True:
            # Getting the positions as buffers
            for i in range(0, len(drones)):
                # Try to retrieve the streamed data
                returnCode, data[i] = sim.simxGetObjectPosition(clientID,
                                                                 drones[i],
                                                                -1,
                                                                sim.simx_opmode_buffer)

            # Storing the position in data files
            send_file_position(data[i], nodes[i] + '_position') #trying to obten a diferent file   

            while not pings_done:
                if ping_count < max_pings:
                    info("*** Executando o ping")
                    latency_response = send_ping_command('10.0.0.2')  #testando
                    send_file_latency(latency_response, nodes[i] + '_latency')
                    ping_count += 1
                if ping_count >= max_pings:
                    pings_done = True
                    break

            time.sleep(1)
            if pings_done:
                control = False
                break                

            time.sleep(1)


        # Now close the connection to CoppeliaSim:
        sim.simxFinish(clientID)
    else:
        info('Failed connecting to remote API server')
    info('Program ended')


def send_file_position(data, node):
    path = os.path.dirname(os.path.abspath(__file__))
    file_name = f"{path}/data/{node}.txt"
    with open(file_name, "a") as f:
        file_position = ','.join(map(str, data))
        f.write(file_position + '\n')

def send_file_latency(data, node):
    path = os.path.dirname(os.path.abspath(__file__))
    file_name = f"{path}/data/{node}.txt"
    with open(file_name, "a") as f:
        f.write(data + '\n')

if __name__ == '__main__':
    drone_position(sys.argv)

