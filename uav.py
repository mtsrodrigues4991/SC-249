#!/usr/bin/env python

'This example creates a simple network topology with 1 AP and 2 stations'

import sys
import time
import os
import re
import threading
import socket
from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.telemetry import telemetry
from mn_wifi.wmediumdConnector import interference


def kill_process():
    os.system('pkill -9 -f coppeliaSim')
    os.system('pkill -9 -f simpleTest.py')
    os.system('pkill -9 -f setNodePosition.py')
    os.system('rm -f examples/uav/data/*')

    
def handle_client_connection(client_socket, net):
    try:
        while True:
            request = client_socket.recv(1024).decode('utf-8', errors='ignore')
            if not request:
                break  # Encerra a conexão se não receber dados
            print(f"Received: {request}")
            # Supondo que o comando recebido é para realizar um ping
            if request.startswith('ping'):
                target_ip = request.split(' ')[1]
                result = net.getNodeByName('dr1').cmd(f'ping -c 11 -i 1 {target_ip}')
                client_socket.send(result.encode('utf-8'))
                # Extrai todos os tempos de resposta usando expressões regulares
                response_times = re.findall(r'time=(\d+\.\d+) ms', result)
                if response_times:
                    # Ajusta o formato dos tempos de resposta
                    response_times_str = ", ".join(response_times)  # Formato ajustado
                    print("Response time:", response_times_str)
                else:
                    print("No ping response time found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client_socket.close()


def start_socket_server(net):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('192.168.15.76', 12345))
    server.listen(10)  # Máximo de 10 conexões
    print("Socket server listening on port 12345")
    while True:
        client_sock, _ = server.accept()
        client_handler = threading.Thread(target=handle_client_connection, args=(client_sock, net,))
        client_handler.start()
        
####################################

def topology():
    "Create a network."
    net = Mininet_wifi(link=wmediumd)#, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    sta_arg, ap_arg = {}, {}
    if '-v' in sys.argv:
        sta_arg = {'nvif': 2}
    else:
        # isolate_clientes: Client isolation can be used to prevent low-level
        # bridging of frames between associated stations in the BSS.
        # By default, this bridging is allowed.
        # OpenFlow rules are required to allow communication among nodes
        ap_arg = {'client_isolation': True}

    ap1 = net.addAccessPoint('ap1', ssid='simpletop2', mode='g', channel="6", position='40,40,0', range='100', **ap_arg) 
    net.setPropagationModel(model="logDistance", exp=4.5)                  

    dr1 = net.addStation('dr1', ip='10.0.0.1/8', position='70,50,0', **sta_arg)
    h1 = net.addStation('h1', ip='10.0.0.2/8', position='38,42,0')
    c0 = net.addController('c0')

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Associating Stations\n")
    net.addLink(dr1, ap1)
    net.addLink(h1, ap1)

    info("*** Starting network\n")
    net.build()
    c0.start()
    ap1.start([c0])

    if '-v' not in sys.argv:
        ap1.cmd('ovs-ofctl add-flow ap1 "priority=0,arp,in_port=1,'
                'actions=output:in_port,normal"')
        ap1.cmd('ovs-ofctl add-flow ap1 "priority=0,icmp,in_port=1,'
                'actions=output:in_port,normal"')
        ap1.cmd('ovs-ofctl add-flow ap1 "priority=0,udp,in_port=1,'
                'actions=output:in_port,normal"')
        ap1.cmd('ovs-ofctl add-flow ap1 "priority=0,tcp,in_port=1,'
                'actions=output:in_port,normal"')

    info("*** Starting Socket Server\n")
    server_thread = threading.Thread(target=start_socket_server, args=(net,))
    server_thread.daemon = True
    server_thread.start()

    info("*** Starting CoppeliaSim\n")
    path = os.path.dirname(os.path.abspath(__file__))
    os.system('{}/CoppeliaSim_Edu_V4_5_1_rev4_Ubuntu18_04/coppeliaSim.sh -s {}'
              '/simulation.ttt -gGUIITEMS_2 &'.format(path, path))
    time.sleep(10)

    nodes = net.stations + [ap1]
    telemetry(nodes=nodes, single=True, data_type='position')

    sta_drone = [n.name for n in net.stations]
    sta_drone_send = ' '.join(sta_drone)

    
    info("*** Configure the node position\n")
    setNodePosition = 'python {}/setNodePosition.py '.format(path) + sta_drone_send + ' &'
    os.system(setNodePosition)
    
    
    info("*** Perform a simple test\n")
    simpleTest = 'python {}/simpleTest.py '.format(path) + sta_drone_send + ' &'
    os.system(simpleTest)

    time.sleep(5)



    info("*** Simulation running for 15 seconds\n")
    time.sleep(15)  # A simulação opera por 15 segundos

    #info("*** Running CLI\n")
    #CLI(net)

    info("*** Stopping network\n")
    kill_process()
    net.stop()
    



if __name__ == '__main__':
    setLogLevel('info')
    topology()
