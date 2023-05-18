import csv
# from dataclasses import KW_ONLY
import time
from audioop import bias
from multiprocessing.sharedctypes import Value
import attrs
import enum
from typing import Union, Optional
from functools import wraps
import numpy as np
import nidcpower
import hightime
# import matplotlib.pyplot as plt
import multiprocessing
from itertools import repeat
import pandas as pd
import contextlib
# from driver.HP4156C import HP4156C


def ivi_synchronized(f):
    @wraps(f)
    def aux(*xs, **kws):
        session = xs[0]  # parameter 0 is 'self' which is the session object
        with session.lock():
            return f(*xs, **kws)
    return aux

class SMUType(enum.Enum):
    HP_415x     = 1
    NI_PXIe41xx = 2

@attrs.define
class ChnVoltBias:
    remarks     : str
    resource    : str

    # GND         : bool  = attrs.field(
    #                         default=True,
    #                         kw_only=True,
    # )
    V_force     : float                 # voltage forced by SMU on this channel [V]
    I_compl     : float = attrs.field(  # compliance current allowed on this channel [A]
                            default = 1e-3,
                            kw_only = True,
                            )
    apertureTime: float = attrs.field(
        default=1e-3,
        kw_only=True,
    )
    VoltSense   : bool = attrs.field(
                            default=False,
                            kw_only=True,
    )
    V_compl     : float = attrs.field(
                            default=3,
                            kw_only=True,
    )
    I_force     : float = attrs.field(
                            default=0,
                            kw_only=True,
    )
    source_delay: float = attrs.field(
                            default=3e-5,
                            kw_only=True,
                            
    )
    remote_sense: bool  = attrs.field(
                            default=False,
                            kw_only=True,
    )

    # V_force_stress: float = attrs.field(
    #                          default = 24,
    #                          kw_only = True,
    #
    # )
    # V_force_SILC: float = attrs.field(
    #                           default=5,
    #                           kw_only=True,
    # )
    # I_init       : float = attrs.field(
    #                            default=10-6,
    #                             kw_only=True,
    # )

@attrs.define
class chnGATE:
    resource                      : str
    vFB: float = attrs.field(
        kw_only=True,
        default=0,
    )
    V_force_stress: float = attrs.field(
        kw_only=True,
        default=0,
    )
    I_force_stress: float = attrs.field(
        kw_only=True,
        default=0,
    )
    V_force_SILC: float = attrs.field(
        kw_only=True,
        default=0,
    )
    I_start     : float
    I_stop      : float
    I_step      : float
    V_compl     : float = attrs.field(  # compliance current allowed on this channel [A]
                            default = 24,
                            kw_only = True,
                            )
    # V_start     : float = attrs.field(
    #     kw_only=True,
    # )
    # V_stop      : float = attrs.field(
    #     kw_only=True,
    # )
    # V_step      : float = attrs.field(
    #     kw_only=True,
    # )

    I_compl: float = attrs.field(
        default=1e-3,
        kw_only=True,
    )
    t_wait_before_SILC_measurement: float = attrs.field(
        default=2,
    )
    t_stress_time: float = attrs.field(
        default=50,
    )


@attrs.define
class TDDB:
    dieName                       : str
    chnStress                     : chnGATE
    biases                        : list[ChnVoltBias] = attrs.field(
                                    validator=attrs.validators.deep_iterable(member_validator=attrs.validators.instance_of(ChnVoltBias)),
                                    )

    @biases.validator
    def _checkNumBiases(self, attribute, value):
        if len(value) < 1 or len(value) > 24:
            raise ValueError

    # delay time after source voltage is applied and before measurement starts
    sourceDelay: float = attrs.field(
        default=30e-3,
        kw_only=True,
    )

    # integration time
    apertureTime: float = attrs.field(
        default=100e-3,
        kw_only=True,
    )

    # VFB                           : float = attrs.field(
    #                                 kw_only=True,
    # )
    # V_force_stress                : float
    # V_force_SILC                  : float

    # I_compl                       : float = attrs.field(
    #                                 default=1e-3,
    #                                 kw_only=True,
    # )
    # t_wait_before_SILC_measurement: float=attrs.field(
    #                                 default=2,
    # )
    # t_stress_time                 : float = attrs.field(
    #                                 default=50,
    # )
    I_SILC                        : float = attrs.field(
                                    default=0,
    )
    I_CVS                         : float = attrs.field(
                                    default=0,
    )
    Failed_in_pre                 : bool = attrs.field(
                                    default=False,
    )
    Failed_in_CSV                 : bool = attrs.field(
                                    default=False,
    )
    Failed_in_SILC                : bool = attrs.field(
                                    default=False,
    )
    Failed_in_post                : bool = attrs.field(
                                    default=False,
    )


@attrs.define
class ChnVoltSweep:
    remarks: str
    resource    : str
    V_start     : float
    V_stop      : float
    V_step      : float
    I_compl     : float = attrs.field(  # compliance current allowed on this channel [A]
                            default = 1e-3,
                            kw_only = True,
                            )
    remote_sense: bool = attrs.field(
                            default=False,
                            kw_only=True,
    )

@attrs.define
class ChnCurrentSweep:
    resource    : str
    I_start     : float
    I_stop      : float
    I_step      : float
    V_compl     : float = attrs.field(  # compliance current allowed on this channel [A]
                            default = 5,
                            kw_only = True,
                            )

@attrs.define
class IVSweep:
    # channel on which voltage is swept
    sweep           : ChnVoltSweep
    # sweepCurrent    : ChnCurrentSweep   = attrs.field(
    #                                     default=None,
    #
    # )
    # one or more channels on which constant bias is applied
    biases          : list[ChnVoltBias] = attrs.field(
                                    validator=attrs.validators.deep_iterable(member_validator=attrs.validators.instance_of(ChnVoltBias)),
                                    )
    @biases.validator
    def _checkNumBiases(self, attribute, value):
        if len(value)<1 or len(value)>24:
            raise ValueError

    # delay time after source voltage is applied and before measurement starts
    sourceDelay     : float = attrs.field(
                                    default = 10e-3,
                                    kw_only = True,
                                    )
    isMaster        : bool = attrs.field(
                                    default = False,
                                    kw_only = True,
    )

    measure_complete_event_delay : float = attrs.field(
                                    default = 10e-3,
                                    kw_only = True,
    )

    # integration time
    apertureTime    : float = attrs.field(
                                    default = 20e-3,
                                    kw_only = True,
                                    )
    # # integration time
    # apertureTime    : float = attrs.field(
    #                             default = 100e-3,
    #                             kw_only = True,
    #                             )


@attrs.define
class IVSweep_amp:
    # channel on which voltage is swept
    sweep           : ChnCurrentSweep
    # sweepCurrent    : ChnCurrentSweep   = attrs.field(
    #                                     default=None,
    #
    # )
    # one or more channels on which constant bias is applied
    biases          : list[ChnVoltBias] = attrs.field(
                                    validator=attrs.validators.deep_iterable(member_validator=attrs.validators.instance_of(ChnVoltBias)),
                                    )
    @biases.validator
    def _checkNumBiases(self, attribute, value):
        if len(value)<1 or len(value)>24:
            raise ValueError

    # delay time after source voltage is applied and before measurement starts
    sourceDelay     : float = attrs.field(
                                    default = 30e-3,
                                    kw_only = True,
                                    )

    # integration time
    apertureTime    : float = attrs.field(
                                default = 60e-3,
                                kw_only = True,
                                )


def emit(lstMeas, filename):
    with open(filename, "a", newline='') as csv_obj:
        writer = csv.writer(csv_obj)
        writer.writerow(lstMeas)



  
def drawTheCurve():
    pass

#
# class Session(nidcpower.Session):
#
#     @ivi_synchronized
#     def fetch_multiple(self, chn, count, timeout=hightime.timedelta(seconds=1.0)):
#
#         import collections
#         Measurement = collections.namedtuple('Measurement', ['chn', 'voltage', 'current', 'in_compliance'])
#
#         voltage_measurements, current_measurements, in_compliance = self._fetch_multiple(timeout, count)
#         # print("hello***************")
#         return [Measurement(chn=chn, voltage=voltage_measurements[i], current=current_measurements[i],
#                             in_compliance=in_compliance[i]) for i in range(count)]


def fetch_multiple(self, chn, count, timeout=hightime.timedelta(seconds=1.0)):
    import collections
    Measurement = collections.namedtuple('Measurement', ['chn', 'voltage', 'current', 'in_compliance'])
    voltage_measurements, current_measurements, in_compliance = self._fetch_multiple(timeout, count)
    return [Measurement(chn=chn, voltage=voltage_measurements[i], current=current_measurements[i],
                        in_compliance=in_compliance[i]) for i in range(count)]

def runIVSweeps(*lstIVSweep : IVSweep, CSV_name, measureTrigger, sourceTrigger):
    resources: dict[tuple[str, int], IVSweep] = {}

    def takeSecond(elem):
        return int(elem[1])

    def chnKey(chn):
        key = chn.split('/')
        if len(key) == 1:
            key.append(0)
        return tuple(key)

    for ivSweep in lstIVSweep:
        key = chnKey(ivSweep.sweep.resource)
        if key in resources:
            raise ValueError(f'SMU {ivSweep.sweep.resource} used more than once')
        resources[key] = ivSweep.sweep.resource
        for bias in ivSweep.biases:
            key = chnKey(bias.resource)
            if key in resources:
                raise ValueError(f'SMU {bias.resource} used more than once')
            resources[key] = bias.resource
    sorted_resources = sorted(resources)
    sorted_resources.sort(key=takeSecond)
    resources = [resources[key] for key in sorted_resources] # sorted channel names
    # print("resources", resources)
    session = nidcpower.Session(resource_name=resources)

    session.power_line_frequency = 50
    session.aperture_time_units = nidcpower.ApertureTimeUnits.SECONDS
    session.samples_to_average = 1
    session.measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE
    session.source_mode = nidcpower.SourceMode.SEQUENCE
    session.sense = nidcpower.Sense.LOCAL
    session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
    session.voltage_level_autorange = True
    # session.voltage_level_range = 6
    session.voltage_level = 0.0
    session.output_connected = True
    session.output_enabled = True
    session.autorange = True
    # session.autorange_aperture_time_mode = nidcpower.AutorangeApertureTimeMode.AUTO
    session.aperture_time = 20e-3
    # session.autorange_maximum_delay_after_range_change = 9
    # session.autorange_aperture_time_mode = nidcpower.AutorangeApertureTimeMode.AUTO
    # session.autorange_minimum_current_range = 10e-9
    # session.autorange_behavior = nidcpower.AutorangeBehavior.UP_AND_DOWN
    # session.autorange_threshold_mode = nidcpower.AutorangeThresholdMode.HIGH_HYSTERESIS
    # session.autorange_threshold_mode=nidcpower.AutorangeThresholdMode.NORMAL
    session.current_limit_autorange = True
    # session.transient_response = nidcpower.TransientResponse.NORMAL
    # session.aperture_time_auto_mode = nidcpower.ApertureTimeAutoMode.
    # session.autorange_maximum_delay_after_range_change = 0.1
    # session.measure_complete_event_delay
    sourceTriggerInputTerminal = None
    measureTriggerInputTerminal = None
    sourceTriggerInputTerminal = sourceTrigger
    measureTriggerInputTerminal = measureTrigger
    for ivSweep in lstIVSweep:
        
        chnSweep = session.channels[ivSweep.sweep.resource]
        if ivSweep.sweep.remote_sense == True:
            chnSweep.sense = nidcpower.Sense.REMOTE
        chnSweep.aperture_time = ivSweep.apertureTime
        # chnSweep.current_limit_range = ivSweep.sweep.I_compl
        chnSweep.current_limit       = ivSweep.sweep.I_compl
        chnSweep.measure_complete_event_delay = 5e-3
        # chnSweep.autorange_behavior = nidcpower.AutorangeBehavior.UP_AND_DOWN
        # chnSweep.source_trigger_type = nidcpower.TriggerType.SOFTWARE_EDGE
        # chnSweep.send_software_edge_trigger
        
        # chnSweep.current_level_range = 1e-6
        # chnSweep.measure_complete_event_delay = 1
        # chnSweep.source_trigger_type =
        V_start, V_stop, V_step = ivSweep.sweep.V_start, ivSweep.sweep.V_stop, ivSweep.sweep.V_step
        numStep = round(abs((V_stop-V_start)/V_step))+1
        # print(numStep)
        
        # vSteps = np.zeros(numStep+1)
        vSteps = np.linspace(V_start, V_stop, numStep, endpoint=True)
        vSteps = np.append(vSteps, 0)
        # print(vSteps)
        # vSteps = np.insert(vSteps, 0, 0)
        # chnSweep.source_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
        # chnSweep.digital_edge_source_trigger_input_terminal = sourceTriggerInputTerminal
        # chnSweep.digital_edge_measure_trigger_input_terminal = measureTriggerInputTerminal
        # chnSweep.source_complete_event_pulse_width = 300e-9  
        # chnSweep.measure_complete_event_pulse_width = 300e-9
        # chnSweep.source_complete_event_pulse_polarity = nidcpower.Polarity.HIGH
        # chnSweep.measure_complete_event_pulse_polarity = nidcpower.Polarity.HIGH
        # chnSweep.source_complete_event_output_terminal = "PXI_Trig2"
        # chnSweep.measure_complete_event_output_terminal = "PXI_Trig1"

        # chnSweep.source_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
        # chnSweep.measure_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
        # chnSweep.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
        # chnSweep.aperture_time = 200e-6


        # vSteps = np.insert(vSteps, -1, 1.5)

        # vSteps = np.arange(V_start, V_stop, V_step)
        # vSteps = np.insert(vSteps, 0, 0)
        # vSteps = np.insert(vSteps, -1, 1.5)
        # np.insert(vSteps, -1, 0)
        # vSteps *= V_step
        tSteps = [20e-3  for i in range(numStep+1)]
        tSteps[0] = 0.6
        # print(f"len of vStep is {len(vSteps)}, len of tSteps is {len(tSteps)}")
        chnSweep.set_sequence(vSteps, tSteps)
        device = ivSweep.sweep.resource.split("/")[0]
        channel = ivSweep.sweep.resource.split("/")[1]
        if ivSweep.isMaster:
            chnSweep.measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE
            chnSweep.measure_complete_event_delay = ivSweep.measure_complete_event_delay
            # sourceTriggerInputTerminal = sourceTrigger
            # measureTriggerInputTerminal = measureTrigger
            sourceTriggerInputTerminal = f"/{device}/Engine{channel}/SourceTrigger"
            measureTriggerInputTerminal = f"/{device}/Engine{channel}/SourceCompleteEvent"
            # chnSweep.exported_source_trigger_output_terminal = sourceTriggerInputTerminal
            # chnSweep.exported_measure_trigger_output_terminal = measureTriggerInputTerminal
            print(measureTriggerInputTerminal)
        tSteps = [15e-3  for i in range(numStep+1)]
        tSteps[0] = 0.5
        for bias in ivSweep.biases:
            if bias.VoltSense:
                chnBias = session.channels[bias.resource]
                chnBias.output_function = nidcpower.OutputFunction.DC_CURRENT
                chnBias.current_level_autorange = True
                chnBias.voltage_limit_range = bias.V_compl
                chnBias.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
                chnBias.aperture_time = bias.apertureTime
                chnBias.voltage_limit       = bias.V_compl
                chnBias.source_delay = bias.source_delay
                # chnBias.source_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
                chnBias.current_level = bias.I_force
                vSteps = np.zeros(numStep + 1)
                vSteps[:-1] = bias.I_force
                chnBias.set_sequence(vSteps, tSteps)
                chnBias.measure_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
                chnBias.digital_edge_measure_trigger_input_terminal = measureTriggerInputTerminal
                chnBias.digital_edge_source_trigger_input_terminal = sourceTriggerInputTerminal
                chnBias.source_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
            else:
                chnBias = session.channels[bias.resource]
                if bias.remote_sense == True:
                    chnBias.sense = nidcpower.Sense.REMOTE
                chnBias.aperture_time = ivSweep.apertureTime
                chnBias.source_delay = bias.source_delay
                # chnBias.autorange_behavior = nidcpower.AutorangeBehavior.UP
                # chnBias.autorange_threshold_mode = nidcpower.AutorangeThresholdMode.FAST_STEP

                # chnBias.current_limit_range = bias.I_compls
                chnBias.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
                # chnBias.source_delay = 0.3e-3
                chnBias.current_limit       = bias.I_compl
                chnBias.voltage_level = bias.V_force
                vSteps = np.zeros(numStep+1)
                vSteps[:-1] = bias.V_force
                chnBias.set_sequence(vSteps, tSteps)
                # print(chnBias.measure_record_delta_time)
                chnBias.measure_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
                chnBias.digital_edge_measure_trigger_input_terminal = measureTriggerInputTerminal
                chnBias.digital_edge_source_trigger_input_terminal = sourceTriggerInputTerminal
                chnBias.source_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE



    timeout = hightime.timedelta(seconds=1000)
    # print('Effective measurement rate: {0} S/s'.format(session.measure_record_delta_time / 1))

    # print('Channel           Num  Voltage    Current    In Compliance')
    # row_format = '{0:15} {1:3d}    {2:8.6f}   {3:8.6f}   {4}'
    df_meas_list = []
    for ivsweep in lstIVSweep:
        for bias in ivsweep.biases:
            chnBias = session.channels[bias.resource]
            chnBias.initiate() # slave initiate
        chnSweep = session.channels[ivSweep.sweep.resource]
        chnSweep.initiate() # master initiate
    # with session.initiate():
    session.wait_for_event(nidcpower.Event.SEQUENCE_ENGINE_DONE, timeout=timeout)
    for ivSweep in lstIVSweep:
        chnSweep = session.channels[ivSweep.sweep.resource]
        num = chnSweep.fetch_backlog
        measurements = fetch_multiple(chnSweep, chn=ivSweep.sweep.remarks, count=num, timeout=timeout)[:-1]
        df = pd.DataFrame(measurements)
        df_meas_list.append(df)


        for bias in ivSweep.biases:
            pretest_temp_list = []
            chnBias = session.channels[bias.resource]
            num = chnBias.fetch_backlog
            measurements = fetch_multiple(chnBias, chn=bias.remarks, count=num, timeout=timeout)[:-1]
            df = pd.DataFrame(measurements)

            df_meas_list.append(df)
    all_meas = pd.concat(df_meas_list, axis=1)
    all_meas.to_csv(CSV_name, mode="a+")
    print(all_meas)
    session.close()
    return all_meas


def measurement1pt():
    resource = ["SMU2/0","SMU3/0","SMU4/0","SMU5/0"]
    with nidcpower.Session(resource_name=resource, reset=True) as session:
        session.power_line_frequency = 50
        session.aperture_time_units = nidcpower.ApertureTimeUnits.SECONDS
        session.samples_to_average = 1
        session.source_mode = nidcpower.SourceMode.SINGLE_POINT
        session.measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE
        # session.source_mode = nidcpower.SourceMode.SEQUENCE
        session.sense = nidcpower.Sense.LOCAL
        session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
        session.voltage_level_autorange = True
        # session.voltage_level_range = 6
        session.voltage_level = 0.0
        session.output_connected = True
        session.output_enabled = True
        session.autorange = True
        session.current_limit_autorange = True
        session.transient_response = nidcpower.TransientResponse.NORMAL
        # session.measure_complete_event_delay
        sourceTriggerInputTerminal = f'/SMU2/Engine0/SourceTrigger'
        measureTriggerInputTerminal = f'/SMU2/Engine0/MeasureTrigger'
        # master 
        chnSweep = session.channels[resource[0]]
        chnSweep.aperture_time = 20e-3
        chnSweep.source_delay  = 10e-3
        chnSweep.current_limit_autorange = True
        chnSweep.voltage_limit_autorange = True
        chnSweep.autorange = True
        chnSweep.voltage_level = 1.5
        chnSweep.measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE

        # slave 
        for resourceChn in resource[1:]:
            chnBias =  session.channels[resourceChn]
            chnBias.aperture_time = 20e-3
            chnBias.source_delay  = 5e-5
            chnBias.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
            chnBias.measure_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
            chnBias.source_trigger_type = nidcpower.TriggerType.DIGITAL_EDGE
            chnBias.digital_edge_measure_trigger_input_terminal = measureTriggerInputTerminal
            chnBias.digital_edge_source_trigger_input_terminal = sourceTriggerInputTerminal
            chnBias.current_limit_autorange = True
            chnBias.voltage_limit_autorange = True
            chnBias.autorange = True
            chnBias.voltage_level = 0.1
        
        with contextlib.ExitStack() as ctxt:
            for resourceChn in resource[1:]:
                chnBias =  session.channels[resourceChn]
                ctxt.enter_context(chnBias.initiate())
            ctxt.enter_context(chnSweep.initiate())
            chnSweep.wait_for_event(nidcpower.Event.SOURCE_COMPLETE)
            timeout=hightime.timedelta(seconds=1.0)
            measurements=chnSweep.fetch_multiple(1)
            print("G",measurements)
            df_meas_list = []
            df = pd.DataFrame(measurements)
            df_meas_list.append(df)
            for resourceChn in resource[1:]:
                chnBias =  session.channels[resourceChn]
                measurements=chnBias.fetch_multiple(1)
                print("_",measurements)
                df = pd.DataFrame(measurements)
                df_meas_list.append(df)

    all_meas = pd.concat(df_meas_list, axis=1)
    print(all_meas)
    return all_meas


def fetch_multiple2(chn,count,voltage_measurements,current_measurements):
    import collections
    count = min(len(voltage_measurements),len(current_measurements))
    print(len(voltage_measurements),len(current_measurements))
    Measurement = collections.namedtuple('Measurement', ['chn', 'voltage', 'current'])
    return [Measurement(chn=chn, voltage=voltage_measurements[i], current=current_measurements[i]) for i in range(count)]




def _test():
    # with nidcpower.Session(resource_name="SMU2", reset=True, independent_channels=False) as session:
    #     # nidcpower.Session(resource_name="Dev2", reset=True, independent_channels=False) as session2:
    #     print('xxxx', session.instrument_model)
    #     # print('xxxx', session.channel_count)
    #     # print('xxxx', session.current_limit_range)
    #     #session.output_connected = False
    #     #session.output_enabled = False

    import datetime

   

    

    vtlin = IVSweep(ChnVoltSweep('G', 'SMU1/1', V_start=-0.5, V_stop=1.5, V_step=0.02, I_compl=1e-3, remote_sense=False),
                  [ChnVoltBias('D', 'SMU1/6', 0.1, I_compl=1e-3, remote_sense=False),
                  ChnVoltBias('S', 'SMU1/5', 0, I_compl=1e-3),
                  ChnVoltBias('B', 'SMU1/4', 0, I_compl=1e-3),
                   ],
                  apertureTime=20e-3,
                  sourceDelay=5e-5,
                  isMaster=1,
                  )

    CBCM = IVSweep(ChnVoltSweep('io1', 'SMU1/1', V_start=0, V_stop=1.2, V_step=0.02, I_compl=1e-3, remote_sense=False),
                    [ChnVoltBias('io2', 'SMU1/6', 0.0, I_compl=1e-3, remote_sense=False),
                        ChnVoltBias('DeviceBias', 'SMU1/5', 1.18, I_compl=1e-3),
                        ChnVoltBias('VDD', 'SMU1/4', 1.2, I_compl=1e-3),
                        ChnVoltBias('VSS', 'SMU1/3', 0, I_compl=1e-3),
                    ],
                    apertureTime=20e-3,
                    sourceDelay=5e-5,
                    isMaster=1,
                    )
                   

    diode_csv = ".csv"
    HQB_csv = "chuckFloating_NMOS12_wg10Lg0p13_2_3rd_0p5ms_SourceDelay.csv"
    demo= '4163_Core_HCI_NMOS_withTheDoorClosed__everythingClosed.csv'
    runIVSweeps(vtlin, CSV_name=demo)
    # test4156(CSV_name=demo)
    # runIVSweeps(HQ, CSV_name=HQ_csv)
    NBTI = "A2E049_w4_NBTI_PLR_HCI_4_die_0_0_Lg0p3.csv"

    t1 = datetime.datetime.now()





# _test()
# measurement1pt()