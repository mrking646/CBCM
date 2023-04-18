import argparse
import nidigital
import os
import sys
import nidcpower
from dcpowerSweep import runIVSweeps, IVSweep, ChnVoltSweep, ChnVoltBias

def example(resource_name, options, trigger_source=None, trigger_edge=None):

    with nidigital.Session(resource_name=resource_name, options=options) as session:

        dir = os.path.join(os.path.dirname(__file__)) # Path to the .pinmap, .specs, .digilevels, .digitiming, and .digipat files
        

        # Load the pin map (.pinmap) created using the Digital Pattern Editor
        pin_map_filename = os.path.join(dir, 'PinMap.pinmap')
        session.load_pin_map(pin_map_filename)

        # Load the specifications (.specs), levels (.digilevels), and timing (.digitiming) sheets created using the Digital Pattern Editor
        spec_filename = os.path.join(dir, 'Specifications.specs')
        levels_filename = os.path.join(dir, 'PinLevels.digilevels')
        timing_filename = os.path.join(dir, 'Timing.digitiming')
        session.load_specifications_levels_and_timing(spec_filename, levels_filename, timing_filename)
        
        # session.conditional_jump_trigger_type = nidigital.TriggerType.DIGITAL_EDGE
        # session.digital_edge_conditional_jump_trigger_source = 'PXI_Trig2'
        # session.digital_edge_conditional_jump_trigger_edge = nidigital.DigitalEdge.RISING
        # sourceTrigger = 'PXI_Trig0'
        # measureTrigger = 'PXI_Trig1'
        # sourceCompleteEvent = 'PXI_Trig2'
        # measureCompleteEvent = 'PXI_Trig3'
        # session.conditional_jump_triggers[2].digital_edge_conditional_jump_trigger_source = sourceCompleteEvent
        # session.conditional_jump_triggers[0].digital_edge_conditional_jump_trigger_source = measureCompleteEvent
    
        VDD = 1.5
        cbcm = IVSweep(ChnVoltSweep('io1', 'SMU1/1', V_start=0, V_stop=1.2, V_step=0.02, I_compl=1e-3, remote_sense=False),
                  [ChnVoltBias('io2', 'SMU1/6', 0.0, I_compl=1e-3, remote_sense=False),
                  ChnVoltBias('DeviceBias', 'SMU1/5', 0, I_compl=1e-3),
                  ChnVoltBias('VDD', 'SMU1/4', 1.2, I_compl=1e-3),
                  ChnVoltBias('VSS', 'SMU1/5', 0, I_compl=1e-3),
                   ],
                  apertureTime=20e-3,
                  sourceDelay=5e-5,
                  isMaster=1,
                  )



        # session.pattern_opcode_events[0].exported_pattern_opcode_event_output_terminal = measureTrigger # send measureTrigger to PXI_Trig0
        # session.pattern_opcode_events[2].exported_pattern_opcode_event_output_terminal = sourceTrigger # send sourceTrigger to PXI_Trig1
        # Apply the settings from the levels and timing sheets we just loaded to the session
        session.apply_levels_and_timing(levels_filename, timing_filename)

        # Loading the pattern file (.digipat) created using the Digital Pattern Editor
        pattern_filename = os.path.join(dir, 'Pattern.digipat')
        session.load_pattern(pattern_filename)
        # session.write_sequencer_register(reg=nidigital.SequencerRegister.REGISTER0, value=2000)
        # print(session.read_sequencer_register(reg=nidigital.SequencerRegister.REGISTER0))

        if trigger_source is None:
            print('Start bursting pattern')
        else:
            # Specify a source and edge for the external start trigger
            session.start_trigger_type = nidigital.TriggerType.DIGITAL_EDGE
            session.digital_edge_start_trigger_source = trigger_source
            session.digital_edge_start_trigger_edge = nidigital.DigitalEdge.RISING if trigger_edge == 'Rising' else nidigital.DigitalEdge.FALLING
            print('Wait for start trigger and then start bursting pattern')

        # If start trigger is configured, waiting for the trigger to start bursting and then blocks until the pattern is done bursting
        # Else just start bursting and block until the pattern is done bursting
        session.burst_pattern(start_label='new_pattern')

        # Disconnect all channels using programmable onboard switching
        session.selected_function = nidigital.SelectedFunction.DISCONNECT
    print('Done bursting pattern')

def dcBias():
    pass



def _main(argsv):
    parser = argparse.ArgumentParser(description='Demonstrates how to create and configure a session that bursts a pattern on the digital pattern instrument using a start trigger', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-n', '--resource-name', default='PXI1Slot2,PXI1Slot3', help='Resource name of a NI digital pattern instrument. Ensure the resource name matches the instrument name in the pinmap file.')
    parser.add_argument('-s', '--simulate', default='True', choices=['True', 'False'], help='Whether to run on simulated hardware or real hardware')
    subparser = parser.add_subparsers(dest='command', help='Sub-command help')
    start_trigger = subparser.add_parser('start-trigger', help='Configure start trigger')
    start_trigger.add_argument('-ts', '--trigger-source', default='/PXI1Slot2/PXI_Trig0', help='Source terminal for the start trigger')
    start_trigger.add_argument('-te', '--trigger-edge', default='Rising', choices=['Rising', 'Falling'], help='Trigger on rising edge or falling edge of start trigger')
    args = parser.parse_args(argsv)

    example(args.resource_name,
            'Simulate=1, DriverSetup=Model:6571' if args.simulate == 'True' else '',
            args.trigger_source if args.command == 'start-trigger' else None,
            args.trigger_edge if args.command == 'start-trigger' else None)


def main():
    _main(sys.argv[1:])


def test_main():
    _main([])
    _main(['start-trigger'])


def test_example():
    resource_name = 'PXIe6570'
    options = {'simulate': False, 'driver_setup': {'Model': '6570'}, }
    example(resource_name, options)

    trigger_source = '/PXI1Slot2/PXI_Trig0'
    trigger_edge = 'Rising'
    example(resource_name, options, trigger_source, trigger_edge)


if __name__ == '__main__':
    test_example()