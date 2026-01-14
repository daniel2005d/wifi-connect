import threading
import time
import signal
import sys
import argparse

from wpa_supplicant.core import WpaSupplicantDriver
from twisted.internet.selectreactor import SelectReactor

target_network = None
interface = None

def signal_handle(sig, frame):
    try: interface.disconnect_network()
    except: pass
    try: interface.remove_network(target_network)
    except: pass

    sys.exit(0)

def get_wpa_supplicant(authentication, ssid, username=None, password=None):
    network_params = None
    if authentication == "wpa-enterprise":
        network_params = {
            "ssid": ssid,
            "key_mgmt": "WPA-EAP",
            "eap": "PEAP",
            'identity': username,
            'password': password,
            "phase2": "auth=MSCHAPV2",
        }
    elif authentication == "OPN":
        network_params = {
            "ssid": ssid,
            "key_mgmt": "NONE"
        }
    elif authentication == "wpa2":
        network_params = {
            "ssid": ssid,
            "key_mgmt": "NONE",
            "wep_key0": password,
            "wep_txidx":0
        }

    return network_params

def connect(ssid, iface, supplicant, authentication, username=None, password=None, 
            domain=None):
    
    if domain:
        username = f'{domain}\{username}'

    network_params = get_wpa_supplicant(authentication, ssid, username, password)
    if network_params:
         # Remove all the networks currently assigned to this interface
        for network in iface.get_networks():
            network_path = network.get_path()
            iface.remove_network(network_path)

        # Add target network to the interface and connect to it 
        iface.add_network(network_params)
        target_network = iface.get_networks()[0].get_path()

        iface.select_network(target_network)
        seconds_passed = 0
        while seconds_passed <= 4.5:
            try:
                print(f'\r\033[KConnecting...', end='')
                state = iface.get_state()
                if state == "completed":
                    credentials_valid = 1
                    break
            except Exception as e:
                print(e)
                break

            time.sleep(0.01)   
            seconds_passed += 0.01
        
        if credentials_valid == 1:
            print(f'\r\033[KConnected to {ssid}', end='')

def main(args):

    ssid = args.ssid
    device = args.iface
    username = args.username
    password = args.password
    domain = args.domain
    authentication = args.authentication


    signal.signal(signal.SIGINT, signal_handle)

    reactor = SelectReactor()
    threading.Thread(target=reactor.run, kwargs={'installSignalHandlers': 0}).start()
    time.sleep(0.1)  # let reactor start

    # Start Driver
    driver = WpaSupplicantDriver(reactor)

    # Connect to the supplicant, which returns the "root" D-Bus object for wpa_supplicant
    supplicant = driver.connect()

    # Register an interface w/ the supplicant, this can raise an error if the supplicant
    # already knows about this interface

    
    try:
        interface = supplicant.get_interface(device)
    except:
        interface = supplicant.create_interface(device)

    ssid="wifi-guest"


    connect("wifi-guest", interface,supplicant, "OPN")

parser = argparse.ArgumentParser()
parser.add_argument("--ssid", help="AP name", required=True)
parser.add_argument("--username", help="Username for Enterprise connection")
parser.add_argument("--password", help="Password of the SSID or the username")
parser.add_argument("--domain", help="Domain for Enterprise connection")
parser.add_argument("--authentication", help="Cipher authentication types", choices=["wpa-enterprise","OPN", "wpa2"])
parser.add_argument("iface", help="Interface name used to connect")

args = parser.parse_args()
main(args)