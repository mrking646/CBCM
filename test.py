# from driver.PulseGen import PulseGen
# import pyvisa
# address = "TCPIP3::192.168.1.22::1234::SOCKET"

# pulseGen = PulseGen(address)
# with pulseGen.connect():
#     pulseGen.queryInstrument()

import socket

s = socket.socket()

s.connect(('192.168.1.22', 1234))
s.send('*IDN?\n')
print(s.recv(1024))