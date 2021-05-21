from uc.utils import waits
from ecdsa import VerifyingKey, SigningKey, NIST384p
import gevent
import logging

logging.basicConfig(level=1)

def update_f(state, inputs, aux_in):
    state_ = state
    if state_ is None: state_ = 0
    print('\nstate', state_)
    print('\ninputs', inputs)
    for pid in inputs.keys():
        if inputs[pid]: state_ += inputs[pid]
    return state_, []

def env(k, static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 2
    P_1 = 0
    P_2 = 1
    P_3 = 2
    sid = ('sid', update_f, None, (P_1, P_2, P_3), delta)
    static.write( (('sid', sid), ('crupt',)) )

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m.msg))
            pump.write('')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m.msg))
            pump.write('')

    gevent.spawn(_a2z)
    gevent.spawn(_p2z)


    # generate a key
    sender_sk = SigningKey.generate()
    sender_vk = sender_sk.verifying_key
    receiver_sk = SigningKey.generate()
    receiver_vk = receiver_sk.verifying_key

    print(f"sender key: {sender_sk}")
    print(f"receiver key: {receiver_sk}")

    # sign msg
    print()
    tx = "hello"
    tx_sender_sig = sender_sk.sign(str(tx).encode())
    print(f">>> sender signed msg {tx_sender_sig}")

    # verify msg
    print(f">>> msg: {str(tx).encode()}")
    is_verified = sender_vk.verify(tx_sender_sig, str(tx).encode())
    print(f">>> verfication: {is_verified} \n")


    z2p.write( ((sid,P_1), ('balance',)) )
    waits(pump)

    z2p.write( ((sid,P_1), ('get_keys',)) )
    waits(pump)

    z2p.write( ((sid,P_1), ('pay', (P_3, 3) )) )
    waits(pump)

    for _ in range(3):
        z2w.write( ((sid, 'F_Wrapper'),('poll',)), 1 )
        waits(pump)

    z2p.write( ((sid,P_1), ('balance',)) )
    waits(pump)

    z2p.write( ((sid,P_2), ('balance',)) )
    waits(pump)

    z2p.write( ((sid,P_3), ('balance',)) )
    waits(pump)

    # z2a.write( ('A2W', ((sid, 'F_Wrapper'), ('exec', 7, 0,)), 0) )
    # waits(pump)

    # z2a.write( ('A2W', ((sid, 'F_Wrapper'), ('callme', 6)), 0) )
    # waits(pump)

    # z2p.write( ((sid, P_3), ('input', 1)) )
    # waits(pump)

    # for _ in range(3):
    #     z2w.write( ((sid, 'F_Wrapper'),('poll',)), 1 )
    #     waits(pump)

    return transcript

from uc.itm import wrappedPartyWrapper, wrappedProtocolWrapper, GlobalFWrapper
from uc.adversary import DummyWrappedAdversary
from g_ledger import G_Ledger
from contract_state import Contract_State
from statechannel.prot_sprite import Prot_Sprite
from statechannel.channel import Broadcast_and_Offchain_Channel
from statechannel.f_state import F_State
from uc.syn_ours import Syn_FWrapper
from uc.execuc import execWrappedUC


# t1 = execWrappedUC(
#     128,
#     env,
#     [('F_state', F_State)],
#     wrappedPartyWrapper('F_state'),
#     GlobalFWrapper([Syn_FWrapper, G_Ledger], ['F_Wrapper', 'G_Ledger']),
#     DummyWrappedAdversary,
#     None
# )

t2 = execWrappedUC(
    128,
    env,
    [('F_channel', Broadcast_and_Offchain_Channel)],
    wrappedProtocolWrapper(Prot_Sprite),
    GlobalFWrapper([Syn_FWrapper, G_Ledger], ['F_Wrapper', 'G_Ledger']),
    DummyWrappedAdversary,
    None
)

print('\nTranscript')
for i in t2:
    print(i)
