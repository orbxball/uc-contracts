from uc.utils import waits
import logging
import gevent


def env(k, static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    n = 3
    sid = ('test_channel', None, None, (0, 1, 2), delta)
    static.write( (('sid', sid), ('crupt',)) )

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m.msg))
            pump.write('dump')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m.msg))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)

    z2p.write( ((sid,1), ('send', 2, ('pay', (8, 12, 1), 'P_s sig'), 0)) )
    waits(pump)

    z2p.write( ((sid,1), ('broadcast', ('hola',), 0)) )
    waits(pump)

    for _ in range(8):
        z2w.write( ((sid, 'F_Wrapper'),('poll',)), 1 )
        waits(pump)

    # z2a.write( ('A2W', ((sid, 'F_Wrapper'), ('exec', 2, 0)), 0) )
    # waits(pump)
    # z2a.write( ('A2W', ((sid, 'F_Wrapper'), ('exec', 2, 0)), 0) )
    # waits(pump)
    # z2a.write( ('A2W', ((sid, 'F_Wrapper'), ('exec', 2, 0)), 0) )
    # waits(pump)

    return transcript

from uc.itm import wrappedPartyWrapper, wrappedProtocolWrapper, GlobalFWrapper
from uc.adversary import DummyWrappedAdversary
from statechannel.channel import Broadcast_and_Offchain_Channel
from statechannel.prot_sprite import Prot_Sprite
from uc.syn_ours import Syn_FWrapper
from uc.execuc import execWrappedUC

t1 = execWrappedUC(
    128,
    env,
    [('F_channel', Broadcast_and_Offchain_Channel)],
    # wrappedProtocolWrapper(Prot_Sprite),
    wrappedPartyWrapper('F_channel'),
    GlobalFWrapper([Syn_FWrapper], ['F_Wrapper']),
    DummyWrappedAdversary,
    None
)

print('\ntransacript')
for i in t1:
    print(i)
