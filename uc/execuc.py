from uc.itm import ProtocolWrapper, FunctionalityWrapper, PartyWrapper, GenChannel, WrappedFunctionalityWrapper, WrappedProtocolWrapper, WrappedPartyWrapper
import gevent
from numpy.polynomial.polynomial import Polynomial
import random, os

def createUC(k, fs, ps, adv, poly, importargs={}):
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
    pump = GenChannel('ol pump and dump')

    env_channels = {'f2z':f2z, 'z2f':z2f, 'p2z':p2z, 'z2p':z2p, 'a2z':a2z, 'z2a':z2a}
    func_channels = {'f2z':f2z, 'z2f':z2f, 'f2p':f2p, 'p2f':p2f, 'f2a':f2a, 'a2f':a2f}
    party_channels = {'p2z':p2z, 'z2p':z2p, 'p2a':p2a, 'a2p':a2p, 'p2f':p2f, 'f2p':f2p}
    adv_channels = {'a2z':a2z, 'z2a':z2a, 'a2f':a2f, 'f2a':f2a, 'a2p':a2p, 'p2a':p2a}
    
    channels = {}
    channels.update(env_channels)
    channels.update(func_channels)
    channels.update(party_channels)
    channels.update(adv_channels)
   
    static = GenChannel('static')

    # initialize random bits
    rng = random.Random(os.urandom(32))
    
    def _exec():
        r = gevent.wait( objects=[static], count=1)[0]
        m = r.read().msg
        static.reset()
        sid_msg,crupt_msg = m
        assert sid_msg[0] == 'sid'
        print('sid', sid_msg)
        sid = sid_msg[1]

        assert crupt_msg[0] == 'crupt'
        print('crupted', crupt_msg)
        crupt = set()
        for _s,_p in crupt_msg[1:]:
            crupt.add( (_s,_p))

        f = FunctionalityWrapper(k, rng, crupt, sid, func_channels, pump, poly, importargs)
        for t,c in fs:
            f.newcls(t,c)
        gevent.spawn( f.run )
        p = ps(k, rng, crupt, sid, party_channels, pump, poly, importargs)

        gevent.spawn(p.run)
        # TODO change to wrapped adversray
        advitm = adv(k, rng, crupt, sid, -1, adv_channels, pump, poly, importargs)
        gevent.spawn(advitm.run)
    
    gevent.spawn(_exec)
    return channels,static,pump

def execUC(k, env, fs, ps, adv, poly):
    c,static,pump = createUC(k, fs, ps, adv, poly)
    return env(k, static, c['z2p'], c['z2f'], c['z2a'], c['a2z'], c['f2z'], c['p2z'], pump)

'''
    Execwrappeduc is basically the GUC (or EUC experiment) where there is a protocol
    a functionality and a global functionality that is present in both real and ideal worlds.
    * k: security parameter,
    * fs: the functionality wrapper parameterized with some functioanlity like a synchronous channel between parties
    * wrapper: the global functionality, can be a single global functionality or the GlobalFunctionalityWrapper for more than one global fuctionality
    * adv: the adversary to run: could be dummy adversary
    * importargs lets caller pass in an ITM context or a polynomial. when the simulator runs an internal simulation, it would create a UC instance internally where the ITM context given to all simulated parties is its own context so that they all use the same pool of import/potential.
'''
def createWrappedUC(k, fs, ps, wrapper, adv, poly, importargs={}):
    # create all the channels that will be used
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    f2w,w2f = GenChannel('f2w'),GenChannel('w2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    p2w,w2p = GenChannel('p2w'),GenChannel('w2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
    z2w,w2z = GenChannel('z2w'),GenChannel('w2z')
    w2a,a2w = GenChannel('w2a'),GenChannel('a2w')
    pump = GenChannel('big ol dump')

    # these are the dictionaries that will be passed to each of the spawned ITMs
    env_channels = {'f2z':f2z, 'z2f':z2f, 'p2z':p2z, 'z2p':z2p, 'a2z':a2z, 'z2a':z2a, 'w2z':w2z, 'z2w':z2w}
    func_channels = {'f2z':f2z, 'z2f':z2f, 'f2p':f2p, 'p2f':p2f, 'f2a':f2a, 'a2f':a2f, 'f2w':f2w, 'w2f':w2f}
    party_channels = {'p2z':p2z, 'z2p':z2p, 'p2a':p2a, 'a2p':a2p, 'p2f':p2f, 'f2p':f2p, 'p2w':p2w, 'w2p':w2p}
    adv_channels = {'a2z':a2z, 'z2a':z2a, 'a2f':a2f, 'f2a':f2a, 'a2w':a2w, 'w2a':w2a, 'a2p':a2p, 'p2a':p2a}
    wrapper_channels = {'w2a':w2a, 'a2w':a2w, 'w2f':w2f, 'f2w':f2w, 'w2p':w2p, 'p2w':p2w, 'w2z':w2z, 'z2w':z2w}

    channels = {}
    channels.update(env_channels)
    channels.update(func_channels)
    channels.update(party_channels)
    channels.update(adv_channels)
    channels.update(wrapper_channels)

    # static channel is used by the environment to communicate to ExecUC
    # what sid to use and the list of corrupted parties
    static = GenChannel()
    rng = random.Random(os.urandom(32))
    
    ''' 
        This function waitso to read sid and corrupt list from the environment
        these values are then used to spawn the other ITMs
    '''
    def _exec():
        r = gevent.wait( objects=[static], count=1)[0]
        m = r.read().msg
        static.reset()
        # read sid, crupt list

        sid_msg,crupt_msg = m
        assert sid_msg[0] == 'sid'
        print('sid', sid_msg)

        # set the sid and creat crupt set 
        sid = sid_msg[1]
        assert crupt_msg[0] == 'crupt'
        crupt = set()
        for _s,_p in crupt_msg[1:]:
            crupt.add( (_s,_p) )

        # global functionality (don't worry that it's alled "wrapper" here) is spawned with the channels it needs and the sid and crupt list it needs
        w = wrapper(k, rng, crupt, sid, {'f2w':f2w, 'w2f':w2f, 'p2w':p2w, 'w2p':w2p, 'a2w':a2w, 'w2a':w2a, 'z2w':z2w, 'w2z':w2z}, pump, poly, importargs)
        gevent.spawn(w.run)
        
        # wrapped functionality wrapper because we have global functionalities that local functionalities can interact with
        f = WrappedFunctionalityWrapper(k, rng, crupt, sid, func_channels, pump, poly, importargs)
        # defin what functionalities can be spawned with the tag of the functionality and the class to use to spawn it
        for t,c in fs:
            f.newcls(t,c)
        gevent.spawn( f.run )
        print('execuc crupt', crupt)

        # party wrapper or protocol wrapper being spawned
        p = ps(k, rng, crupt, sid, {'z2p':z2p, 'p2z':p2z, 'f2p':f2p, 'p2f':p2f, 'a2p':a2p, 'p2a':p2a, 'w2p':w2p, 'p2w':p2w}, pump, poly, importargs)
        gevent.spawn(p.run)
        # TODO change to wrapped adversray
        advitm = adv(k, rng, crupt, sid, -1, adv_channels, pump, poly, importargs)
        gevent.spawn(advitm.run)

    gevent.spawn(_exec)
    return channels,static,pump

def execWrappedUC(k, env, fs, ps, wrapper, adv, poly=Polynomial([1])):
    # creates the full UC execution and then returns the return value of the environment
    c,static,pump = createWrappedUC(k, fs, ps, wrapper, adv, poly)
    print('type', type(env))
    return env(k, static, c['z2p'], c['z2f'], c['z2a'], c['z2w'], c['a2z'], c['p2z'], c['f2z'], c['w2z'], pump)


'''
    Same as above but for an exeution being simulated inside a simulator 
'''
def createWrappedSimulation(k, fs, ps, wrapper, adv, poly, importargs={}):
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    f2w,w2f = GenChannel('f2w'),GenChannel('w2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    p2w,w2p = GenChannel('p2w'),GenChannel('w2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
    z2w,w2z = GenChannel('z2w'),GenChannel('w2z')
    w2a,a2w = GenChannel('w2a'),GenChannel('a2w')
    pump = GenChannel('big ol dump')

    env_channels = {'f2z':f2z, 'z2f':z2f, 'p2z':p2z, 'z2p':z2p, 'a2z':a2z, 'z2a':z2a, 'w2z':w2z, 'z2w':z2w}
    func_channels = {'f2z':f2z, 'z2f':z2f, 'f2p':f2p, 'p2f':p2f, 'f2a':f2a, 'a2f':a2f, 'f2w':f2w, 'w2f':w2f}
    party_channels = {'p2z':p2z, 'z2p':z2p, 'p2a':p2a, 'a2p':a2p, 'p2f':p2f, 'f2p':f2p, 'p2w':p2w, 'w2p':w2p}
    adv_channels = {'a2z':a2z, 'z2a':z2a, 'a2f':a2f, 'f2a':f2a, 'a2w':a2w, 'w2a':w2a, 'a2p':a2p, 'p2a':p2a}
    wrapper_channels = {'w2a':w2a, 'a2w':a2w, 'w2f':w2f, 'f2w':f2w, 'w2p':w2p, 'p2w':p2w, 'w2z':w2z, 'z2w':z2w}

    channels = {}
    channels.update(env_channels)
    channels.update(func_channels)
    channels.update(party_channels)
    channels.update(adv_channels)
    channels.update(wrapper_channels)

    static = GenChannel()
    itms = GenChannel()
    rng = random.Random(os.urandom(32))
    
    def _exec():
        r = gevent.wait( objects=[static], count=1)[0]
        m = r.read().msg
        static.reset()
        sid_msg,crupt_msg = m
        assert sid_msg[0] == 'sid'
        print('sid', sid_msg)
        sid = sid_msg[1]

        assert crupt_msg[0] == 'crupt'
        crupt = set()
        for _s,_p in crupt_msg[1:]:
            crupt.add( (_s,_p) )

        w = wrapper(k, rng, crupt, {'f2w':f2w, 'w2f':w2f, 'p2w':p2w, 'w2p':w2p, 'a2w':a2w, 'w2a':w2a, 'z2w':z2w, 'w2z':w2z}, pump, poly, importargs)
        gevent.spawn(w.run)

        #f = WrappedFunctionalityWrapper(k, rng, crupt, p2f, f2p, a2f, f2a, z2f, f2z, w2f, f2w, pump, poly, importargs)
        f = WrappedFunctionalityWrapper(k, rng, crupt, sid, func_channels, pump, poly, importargs)
        for t,c in fs:
            f.newcls(t,c)
        gevent.spawn( f.run )
        #p = ps(k, sid, z2p, p2z, f2p, p2f, a2p, p2a, w2p, p2w, pump, poly, importargs)
        print('execuc crupt', crupt)
        p = ps(k, rng, crupt, sid, {'z2p':z2p, 'p2z':p2z, 'f2p':f2p, 'p2f':p2f, 'a2p':a2p, 'p2a':p2a, 'w2p':w2p, 'p2w':p2w}, pump, poly, importargs)
        gevent.spawn(p.run)
        # TODO change to wrapped adversray
        advitm = adv(k, rng, crupt, sid, -1, adv_channels, pump, poly, importargs)
        gevent.spawn(advitm.run)

        itms.write( (w, f, p, advitm) )


    gevent.spawn(_exec)
    return channels,static,pump,itms
