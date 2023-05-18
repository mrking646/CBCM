import  pyvisa
import logging
from strenum import StrEnum

logger = logging.getLogger(__name__)
class PulseGen():
    class OutputPort(StrEnum):
        Output1 = 'OUTP1'
        Output2 = 'OUTP2'



    def __init__(self, address):
        self.address = address
        self.com = None

    def connect(self):
        try:
            rm = pyvisa.ResourceManager()
            self.com = rm.open_resource(self.address)
            self.com.query_delay = 0.0
            self.com.timeout = 5000
            print(self.com.query("*IDN?"))
        except Exception as e:
            msg = f'Unable to connect to {self.__class__.__name__} at {self.address}, error: {str(e)}'
            raise RuntimeError(msg)
        return self
    
    def reset(self):
        self.com.write('*RST')
        self.com.write('*CLS')
        return self

    def __enter__(self):
        if self.com is None:
            self.connect()
        self.com.write('*RST')
        self.com.write('*CLS')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, Exception):
            try:
                logger.warning(f'Reset instrument due to unhandled exception: {exc_val}')
                self.reset()
            except Exception as e:
                logger.warning(f'Encountered another exception while handling one: {e}')
        else:
            self.com.write('CL')
            if self.flexMode:
                self.com.write(':PAGE')
        self.com.close()
        return False
    
    def queryInstrument(self):
        print(self.com.query('*IDN?'))

    def setFrequency(self, freq):
        self.com.write(f':FREQ {freq}')
        return self

    def armSource(self, source):
        self.com.write(f':ARM:SOUR {source}')
        return self
    
    def setDutyCycle(self, outputport:int, ratio):
        self.com.write(f':PULSe:DCYCle{outputport} {ratio}')
        return self
    
    def setLeadingEdge(self, outputport:int, time):
        self.com.write(f':PULSe:LEADing{outputport} {time}')
        return self
    
    def setTrailingEdge(self, outputport:int, time):
        self.com.write(f':PULSe:TRAiling{outputport} {time}')
        return self
    
    def setVoltageHigh(self, outputport:int, voltage:float):
        self.com.write(f':VOLTage{outputport}:HIGH{outputport} {voltage}V')
        return self
    
    def setVoltageLow(self, outputport:int, voltage:float):
        self.com.write(f':VOLTage{outputport}:LOW{outputport} {voltage}V')
        return self
    
    def setPeriod(self, period):
        self.com.write(f':PULSe:PERiod {period}')
        return self
    
    def setPulseWidth(self, outputport, width):
        self.com.write(f':PULSe:WIDTh{outputport} {width}')
        return self
    
    def turnOffAutoTrailing(self, outputport):
        self.com.write(f':PULSe:TRANsition1{outputport}:TRAILing:AUTO OFF')
        return self
    
    def setOffsetVoltage(self, outputport, offset):
        self.com.write(f':VOLTage{outputport}:OFFSet {offset}V')
        return self
    
    def setAmplitude(self, outputport, amplitude):
        self.com.write(f':VOLTage{outputport}: {amplitude}V')
        return self
    

