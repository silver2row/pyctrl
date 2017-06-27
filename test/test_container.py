import pytest
import time

HOST, PORT = "localhost", 9998
start_server = True
#start_server = False

def test_container():

    import pyctrl
    import numpy
    import pyctrl.block as block
    import pyctrl.block.system as system
    import pyctrl.block.logic as logic
    import pyctrl.block.random as blkrnd

    from pyctrl import BlockType
    from pyctrl.block.container import Container
    container = Container()

    # initial signals
    _signals = container.list_signals()
    _sinks = container.list_sinks()
    _sources = container.list_sources()
    _filters = container.list_filters()

    assert not container.is_enabled()
    
    container.add_signal('_test_')
    assert '_test_' in container.list_signals()

    #with pytest.raises(pyctrl.block.container.ContainerException):
    container.add_signal('_test_')

    assert container.get_signal('_test_') == 0

    container.set_signal('_test_', 1.2)
    assert container.get_signal('_test_') == 1.2

    container.remove_signal('_test_')
    assert '_test_' not in container.list_signals()

    with pytest.raises(pyctrl.block.container.ContainerException):
        container.set_signal('_test_', 1.2)

    container.add_signals('_test1_', '_test2_')
    assert '_test1_' in container.list_signals()
    assert '_test2_' in container.list_signals()

    container.remove_signal('_test1_')
    container.remove_signal('_test2_')
    assert '_test1_' not in container.list_signals()
    assert '_test2_' not in container.list_signals()

    # test info
    assert isinstance(container.info(), str)
    assert isinstance(container.info('summary'), str)
    assert isinstance(container.info('source','sink'), str)
    
    # test sink

    container.add_signal('clock')

    container.add_sink('_logger_', block.Logger(), ['_test_'])
    assert '_logger_' in container.list_sinks()
    assert '_test_' in container.list_signals()

    assert container.get_sink('_logger_') == {'current': 0, 'auto_reset': False, 'page': 0, 'enabled': True}

    assert container.get_sink('_logger_', 'current', 'auto_reset') == {'current': 0, 'auto_reset': False}
    
    assert container.get_sink('_logger_','current') == 0
    
    container.set_sink('_logger_',current = 1)

    assert container.get_sink('_logger_','current') == 1
    
    # try to remove signal _test_
    container.remove_signal('_test_')
    assert '_test_' in container.list_signals()

    container.add_sink('_logger_', block.Logger(), ['clock'])
    assert '_logger_' in container.list_sinks()
    
    # TODO: test for changed signals

    container.set_sink('_logger_', reset = True)

    log = container.read_sink('_logger_')
    assert isinstance(log, numpy.ndarray)
    assert log.shape == (0, 0)

    with pytest.raises(block.BlockException):
        container.set_sink('_logger_', _reset = True)

    container.set_enabled(True)
    container.run()
    container.run()
    container.set_enabled(False)
        
    log = container.read_sink('_logger_')

    #print(log)
    assert isinstance(log, numpy.ndarray)
    assert log.shape[0] > 1
    assert log.shape[1] == 1

    container.set_sink('_logger_', reset = True)
    log = container.read_sink('_logger_')
    assert isinstance(log, numpy.ndarray)
    assert log.shape == (0,1)

    container.remove_sink('_logger_')
    assert '_logger_' not in container.list_sinks()

    container.add_signal('_test_')

    container.add_sink('_logger_', block.Logger(), ['clock', '_test_'])
    assert '_logger_' in container.list_sinks()

    container.set_enabled(True)
    container.run()
    container.run()
    container.set_enabled(False)

    log = container.read_sink('_logger_')
    assert isinstance(log, numpy.ndarray)
    assert log.shape[0] > 1
    assert log.shape[1] == 2

    container.set_sink('_logger_', reset = True)
    log = container.read_sink('_logger_')
    assert isinstance(log, numpy.ndarray)
    assert log.shape == (0,2)

    container.remove_sink('_logger_')
    assert '_logger_' not in container.list_sinks()

    # test source

    container.add_source('_rand_', blkrnd.Uniform(), ['clock'])
    assert '_rand_' in container.list_sources()

    container.add_source('_rand_', blkrnd.Uniform(), ['_test_'])
    assert '_rand_' in container.list_sources()

    assert container.get_source('_rand_') == {'demux': False, 'mux': False, 'low': 0, 'high': 1, 'enabled': True, 'seed': None, 'm': 1}

    assert container.get_source('_rand_', 'low', 'high') == {'low': 0, 'high': 1}
    
    assert container.get_source('_rand_','low') == 0

    container.set_source('_rand_', low = 1)

    assert container.get_source('_rand_','low') == 1
    
    # TODO: test for changed signals

    container.set_source('_rand_', reset = True)

    a = container.read_source('_rand_')
    assert isinstance(a[0], float)
    assert 0 <= a[0] <= 1

    with pytest.raises(block.BlockException):
        container.set_source('_rand_', _reset = True)

    container.remove_source('_rand_')
    assert '_rand_' not in container.list_sources()

    # test filter

    container.add_signal('_output_')

    container.add_source('_rand_', blkrnd.Uniform(), ['_test_'])
    assert '_rand_' in container.list_sources()

    container.add_filter('_gain_', block.ShortCircuit(), 
                          ['_test_'], 
                          ['_output_'])
    assert '_gain_' in container.list_filters()
    
    # TODO: test for changed block

    container.add_filter('_gain_', system.Gain(gain = 2), 
                          ['_test_'], 
                          ['_output_'])
    assert '_gain_' in container.list_filters()
        
    assert container.get_filter('_gain_') == {'demux': False, 'enabled': True, 'gain': 2, 'mux': False}

    assert container.get_filter('_gain_', 'demux', 'gain') == {'demux': False, 'gain': 2}
    
    assert container.get_filter('_gain_','gain') == 2
    
    container.add_sink('_logger_', block.Logger(), ['_test_', '_output_'])
    assert '_logger_' in container.list_sinks()

    container.set_enabled(True)
    container.run()
    container.run()
    container.set_enabled(False)

    log = container.read_sink('_logger_')
    assert isinstance(log, numpy.ndarray)
    assert log.shape[0] > 1
    assert log.shape[1] == 2

    assert numpy.all(numpy.fabs(log[:,1] / log[:,0] - 2) < 1e-6)

    # test reset
    signals = container.list_signals()
    sinks = container.list_sinks()
    sources = container.list_sources()
    filters = container.list_filters()
    print(signals, sources, filters, sinks)

    print(container.info('all'))

    container.reset()

    container = Container()
    
    signals = container.list_signals()
    sinks = container.list_sinks()
    sources = container.list_sources()
    filters = container.list_filters()
    print(signals, sources, filters, sinks)

    assert signals == _signals
    assert sources == _sources
    assert filters == _filters
    assert sinks == _sinks

    print(container.info('all'))

    container.add_signal('timer')
    container.add_timer('timer',
                         block.Constant(value = 1),
                         None, ['timer'], 1, False)

    print(container.info('all'))

    assert container.get_signal('timer') == 0

    assert container.get_timer('timer') == {'enabled': True, 'demux': False, 'mux': False, 'value': 1}

    assert container.get_timer('timer', 'enabled', 'demux') == {'enabled': True, 'demux': False}
    
    assert container.get_timer('timer','enabled') == True
    
    container.set_enabled(True)
    container.run()
    time.sleep(2)
    container.run()
    container.set_enabled(False)

    assert container.get_signal('timer') == 1

    container.set_signal('timer', 0)
    assert container.get_signal('timer') == 0

    container.set_enabled(True)
    container.run()
    time.sleep(.5)
    container.run()
    container.set_enabled(False)

    assert container.get_signal('timer') == 0

    container.set_signal('timer', 0)
    assert container.get_signal('timer') == 0

    container.add_timer('stop',
                         block.Constant(value = 0),
                         None, ['is_running'], 2, False)
    
    print('##########')
    container.set_enabled(True)
    container.run()
    print('##########')

    time.sleep(3)
    
    container.run()


    container.set_enabled(False)

    assert container.get_signal('timer') == 1


    # test set
    import pyctrl
    
    container = Container()

    print('* * * TEST SET * * *')

    print(container.info('all'))

    container.add_signals('s1', 's2')
    
    container.add_source('const',
                          block.Constant(value = 1),
                          ['s1'])
    
    container.add_sink('set1',
                        logic.SetBlock(blocktype = BlockType.SOURCE,
                                       label = 'const',
                                       on_rise = {'value': 0.6},
                                       on_fall = {'value': 0.4}),
                        ['s2'])

    container.set_enabled(True)
    container.run()
    container.set_enabled(False)

    print(container.get_source('const'))
        
    assert container.get_signal('s2') == 0
    assert container.get_source('const', 'value') == 1

    container.set_enabled(True)
    container.run()
    container.set_signal('s2', 1)
    container.run()
    container.set_enabled(False)

    assert container.get_signal('s2') == 1
    assert container.get_source('const', 'value') == 0.6
    
    container.set_enabled(True)
    container.run()
    container.set_signal('s2', 0)
    container.run()
    container.set_enabled(False)

    assert container.get_signal('s2') == 0
    assert container.get_source('const', 'value') == 0.4
            
def test_container_input_output():

    import pyctrl
    import pyctrl.block as block

    from pyctrl.block.container import Container, Input, Output
    from pyctrl.block.system import Gain
    
    container = Container()

    container.add_signal('s1')

    container.add_source('input1',
                         Input(),
                         ['s1'])
    
    container.add_sink('ouput1',
                       Output(),
                       ['s1'])

    container.set_enabled(True)
    container.write(1)
    values = container.read()
    container.set_enabled(False)

    assert values == (1,)
    
    container.add_sink('ouput2',
                       Output(),
                       ['s1'])
    
    container.set_enabled(True)
    container.write(1)
    values = container.read()
    container.set_enabled(False)

    assert values == (1,1)
    
    container.add_source('input2',
                         Input(),
                         ['s2'])
    
    container.add_sink('ouput2',
                       Output(),
                       ['s2'])

    container.set_enabled(True)
    container.write(1,2)
    values = container.read()
    container.set_enabled(False)

    assert values == (1,2)
    
    container.add_filter('gain1',
                         Gain(gain = 3),
                         ['s1'],['s1'])
    
    container.set_enabled(True)
    container.write(1,2)
    values = container.read()
    container.set_enabled(False)
    
    assert values == (3,2)
    
    container.add_sink('ouput1',
                       Output(),
                       ['s3'])
    
    container.add_filter('gain1',
                         Gain(gain = 3),
                         ['s1'],['s3'])
    
    container.set_enabled(True)
    container.write(1,2)
    values = container.read()
    container.set_enabled(False)
    
    assert values == (2,3)