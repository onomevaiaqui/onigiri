"""POSIX serial Sabertooth transport; instantiated only by explicit motor service."""
import fcntl
import os
import termios
import time

class SerialSabertooth:
    def __init__(self,port,baud,addresses,model):
        if not port.startswith('/dev/'):raise ValueError("Selecione uma porta /dev/")
        if len(set(addresses))!=len(addresses) or any(not 128<=a<=135 for a in addresses):raise ValueError("Endereços inválidos ou repetidos")
        self.addresses=addresses;self.fd=None
        fd=os.open(port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            attrs=termios.tcgetattr(fd);attrs[0]=0;attrs[1]=0;attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL;attrs[3]=0
            attrs[4]=attrs[5]={9600:termios.B9600,19200:termios.B19200,38400:termios.B38400}[baud]
            attrs[6][termios.VMIN]=0;attrs[6][termios.VTIME]=1
            termios.tcsetattr(fd,termios.TCSANOW,attrs);self.fd=fd
            if model=='sabertooth2x60':self._write(bytes([170]));time.sleep(.1)
            self.stop()
            for address in addresses:self._write(self.packet(address,14,3))
        except Exception:
            os.close(fd);self.fd=None;raise
    @staticmethod
    def packet(address,command,value):
        return bytes([address,command,value,(address+command+value)&127])
    def _write(self,data):
        deadline=time.monotonic()+.1
        while data:
            try:
                size=os.write(self.fd,data)
                if size:data=data[size:]
            except BlockingIOError:pass
            if time.monotonic()>deadline:raise TimeoutError("Escrita serial excedeu 100 ms")
    def write(self,powers):
        import math
        if len(powers)!=len(self.addresses)*2:raise ValueError("Número de canais incorreto")
        output=bytearray()
        for i,power in enumerate(powers):
            if not math.isfinite(power) or abs(power)>1:raise ValueError("Potência inválida")
            command=(0 if i%2==0 else 4)+(1 if power<0 else 0)
            output.extend(self.packet(self.addresses[i//2],command,round(abs(power)*127)))
        self._write(output)
    def stop(self):self.write([0]*(2*len(self.addresses)))
    def close(self):
        if self.fd is not None:
            try:self.stop()
            finally:os.close(self.fd);self.fd=None
