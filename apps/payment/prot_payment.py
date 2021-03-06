from uc.itm import UCWrappedProtocol, MSG
from uc.syn_ours import Syn_Channel
from math import ceil, floor
from uc.utils import wait_for, waits
from collections import defaultdict
from numpy.polynomial.polynomial import Polynomial
import logging

log = logging.getLogger(__name__)

class Syn_Payment_Protocol(UCWrappedProtocol):
    #def __init__(self, sid, pid, channels):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.n = sid[1] # number of parties, in uni/bi-directional is 2
        self.delta = sid[2] # the basic unit of delay

        self.id = sid[4]
        self.nonce = -1
        self.states = [] # (nonce) => {nonce, balances}
        self.sigs = [] # (nonce) => [None] * self.n

        self.balances = sid[3]
        self.flag = 'OPEN'
        ## Following is for general case, above is for channel's already open
        # self.balances = [0] * self.n
        # self.flag = 'CLOSED'    # {'CLOSED', 'OPEN', 'CHALLANGE'}
        #                         # 'CLOSED': channel closed
        #                         # 'OPEN': channel open
        #                         # 'CHALLANGE': enter into challenge period
        UCWrappedProtocol.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)


    def _sign(self, state):
        # TODO
        # use it's private key to sign the state s
        return signed_state


    def normal_offchain_payment(self, data):
        nonce = data['nonce']
        assert nonce == self.nonce+1

        self.states.append(data['state'])
        self.sigs.append(data['sig'])
        self.nonce += 1

        s = data['sender']
        r = data['receiver']
        a = data['amount']
        assert r == self.id
        assert a <= self.balances[s]
        self.balances[r] += a
        self.balances[s] -= a


    def react_challenge(self, data, imp):
        self.flag = 'CHALLANGE'

        _s = data['state']
        _n = _s['nonce']
        _b = _s['balances']
        _sig = data['sig']
        # basically P_recv doesnt need to check anything above
        # just sign send the latest state to challenge is fine

        if self.nonce == -1:
            state = {'nonce': self.nonce, 'balances': self.balances}
            sig = data['sig']
        else
            state = self.states[self.nonce]
            sig = self.sigs[self.nonce]
        sig[self.id] = self._sign(state)

        msg = {
            'msg': 'challenge',
            'imp': imp,
            'data': {
                'sender': self.id,
                'states': state,
                'sig': sig
            }
        }
        self.write('p2f', msg)


    def recv_close_channel(self, data):
        self.nonce = -1
        self.balances = [0] * self.n
        self.states.clear()
        self.sigs.clear()
        self.flag = 'CLOSED'

    def recv_init_channel(self, data):
        s = data['sender']
        a = data['amount']
        self.balances[s] += amount
        self.flag = 'OPEN'


    # functionality handler
    # receive msg from the smart contract ideal functionality in the real world
    # b/c it's in a hybrid model
    def func_msg(self, msg):
        log.debug('Protocol/Receive msg from F in real world: {}'.format(msg))
        command = msg['msg']
        tokens = msg['imp']
        data = msg['data']
        if command == 'send':
            # normal offchain payment
            self.normal_offchain_payment(data)
        elif command == 'challenge':
            # entering into challenge
            self.react_challenge(data, tokens)
        elif command == 'init_channel':
            self.recv_init_channel(data)
        elif command == 'close_channel':
            self.recv_close_channel(data)
        else:
            self.pump.write("dump")


    # wrapper handler
    def wrapper_msg(self, msg):
        self.pump.write("dump")


    # adv handler
    def adv_msg(self, msg):
        self.pump.write("dump")


    def close_channel(self, _from, imp):
        if not self.flag == 'CLOSED': # could be either OPEN or CHALLENGE
            if self.nonce == -1:
                state = {'nonce': -1, 'balances': self.balances}
                sig = [None] * self.n
                sig[_from] = self._sign(state)
            else
                state = self.states[self.nonce]
                sig = self.sigs[self.nonce]

            msg = {
                'msg': 'close',
                'imp': imp,
                'data': {
                    'sender': _from
                    'state': state
                    'sig': sig
                }
            }
            self.write('p2f', msg)


    def init_channel(self, _from, imp):
        if self.flag == 'CLOSED': 
            msg = {
                'msg': 'init',
                'imp': imp,
                'data': {
                    'sender': _from,
                    'amount': amount
                }
            }
            self.write('p2f', msg)


    def pay(self, _from, _to, amount, imp):
        if not self.flag == 'OPEN': return # if channel is not open, maybe CLOSED or CHALLENGE, cannot pay offchain
        if amount > self.balances[_from]: return # not enough balance

        self.balances[_from] -= amount
        self.balances[_to] += amount

        self.nonce += 1
        state = {
            'nonce': self.nonce,
            'balances': self.balances
        }
        self.states.append(state)

        self.sigs.append([None] * self.n)
        self.sigs[self.nonce][_from] = self._sign(state)

        msg = {
            'msg': 'send', # united interface with synchronous channel
            'imp': imp,
            'data': {
                'sender': _from,
                'receiver': _to,
                'amount': amount,
                'nonce': self.nonce,
                'state': self.states[self.nonce]
                'sig': self.sigs[self.nonce]
            }
        }
        self.write('p2f', msg)
        

    # env handler
    def env_msg(self, msg):
        log.debug('Prot/Receive message from Z in real world: {}'.format(msg))
        command = msg['msg']
        tokens = msg['imp']
        data = msg['data']
        if command == 'pay':
            # Z tells P_i to pay another P_j
            sender = data['sender']
            assert sender = self.id
            receiver = data['receiver']
            amount = data['amount']
            self.pay(sender, receiver, amount, tokens)
        elif command == 'read':
            # Z tells P_i to read its own balance
            self.write('p2z', self.balances[self.id])
        elif command == 'init':
            # Z tells P_i to init a channel
            sender = data['sender']
            amount = data['amount']
            init_channel(sender, amount, tokens)
        elif command == 'close':
            # Z tells P_i to close a channel
            sender = data['sender']
            close_channel(sender, tokens)
        # elif command == 'deposit':
        #     # Z tells P_i to init a channel
        #     pass
        # elif command == 'withdraw':
        #     # Z tells P_i to close a channel
        #     pass
        else:
            self.pump.write("dump")
            return
        self.write('p2z', 'OK')


from uc.itm import ProtocolWrapper, WrappedProtocolWrapper
from uc.adversary import DummyWrappedAdversary
from uc.syn_ours import Syn_FWrapper, Syn_Channel
from uc.execuc import execWrappedUC
from uc.utils import z_get_leaks

def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    n = 3
    #sid = ('one', (1,2,3), delta)
    sid = ('one', tuple(range(1,n+1)), delta)
    static.write( ('sid', sid) )

    z2p.write( ((sid,1), ('input', 2)), n*(4*n + 1) )
    #wait_for(p2z)
    waits(pump, p2z)

    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')

    z2a.write( ('A2W', ('get-leaks',)) )
    msgs = waits(pump, a2z)
    print('\033[91m [Leaks] \033[0m', '\n'.join(str(m) for m in msgs.msg))


if __name__ == '__main__':
    execWrappedUC(env1, [('F_chan',Syn_Channel)], WrappedProtocolWrapper, Syn_FWrapper, Syn_Bracha_Protocol, DummyWrappedAdversary)
