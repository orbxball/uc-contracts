from uc.itm import UCWrappedProtocol
from uc.utils import wait_for

from ecdsa import VerifyingKey, SigningKey, NIST384p

import logging
log = logging.getLogger(__name__)


class Prot_Sprite(UCWrappedProtocol):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.func = sid[1]
        self._what_is_this = sid[2] # Q: what is this argument
        self.parties = sid[3]
        self.delta = sid[4]

        UCWrappedProtocol.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)

        self.nonce = 0
        self.balances = [0]*len(self.parties) # pid => balance of pid
        self.states = [] # (nonce) => {nonce, balances}
        self.sigs = [] # (nonce) => [None] * self.n

        self.isDealer = False
        if self.pid == self.parties[0]: self.isDealer == True

        self.sk = SigningKey.generate()
        self.vk = self.sk.verifying_key

        self.start = True; # whether it's just spawn or not


    def register_key(self):
        _import = 0
        ret = self.write_and_wait_expect(
            ch='p2w', msg=(
                (self.sid, 'G_Ledger'), ('register_key', (self.vk,), _import)
            ),
            read='w2p', expect=((self.sid, 'G_Ledger'), ('OK',))
        )

    def get_keys(self):
        _import = 0
        ret = self.write_and_wait_for(
            ch='p2w', msg=(
                (self.sid, 'G_Ledger'), ('get_keys', (self.vk,), _import)
            ),
            read='w2p'
        )
        _sender, _keys_dict = ret.msg
        return _sender, _keys_dict

    def check_sig(self, _sig, _state, _signer):
        # TODO: verify signatutre
        return True


    def open(self):
        # TODO: open a sprite channel by spawning a contract
        self.pump.write('')


    def pay(self, v):
        # TODO: off chain payment
        self.pump.write('')


    def close(self):
        # TODO: close the sprite channel
        self.pump.write('')


    def env_msg(self, d):
        if self.start:
            print('Prot_Sprite::env:: on spawn')
            self.register_key()
            self.start = False
            print('Prot_Sprite::env:: finish spawn actions')

        msg = d.msg
        imp = d.imp

        if msg[0] == "pay" and self.pid == self.P_s:
            _, v = msg
            self.pay(v)
        elif msg[0] == "close":
            self.close()
        elif msg[0] == "input":
            # TODO: receive 'input' instruction from env
            self.pump.write('')
        elif msg[0] == "balance":
            _balance = self.balances[self.pid]
            self.write('p2z', ('balance', _balance))
        elif msg[0] == "get_keys":
            _sender, _keys = self.get_keys()
            print(f"keys are here: {_keys}")
            self.write('p2z', ('keys', _keys))
        else:
            self.pump.write('')


    def recv_pay(self, _state, _sig):
        # TODO: actions on receiving off-chain payment
        _b_s, _b_r, _nonce = _state
        if self.flag == "OPEN" and _b_s <= self.b_s and _b_s >= 0 and _b_r >= self.b_r and _nonce == self.nonce + 1 and self.check_sig(_sig, _state, self.P_s):
            v = self.b_s - _b_s
            self.state = _state
            self.b_s = _b_s
            self.b_r = _b_r
            self.nonce = _nonce
            self.write('p2z', ("pay", v))
        else: self.pump.write('')


    def recv_uncoopclose(self, _state, _deadline):
        # TODO: actions on receiving uncooperative close notification
        if self.flag == "OPEN":
            _b_s, _b_r, _nonce = _state
            print('always recognize as an uncoopclose')
            self.write('p2f', 
                ((self.sid, 'F_contract'), # (sid, tag)
                 ('challenge', self.state, 'P_r sig') # msg
                )
            )
            assert wait_for(self.channels['f2p']).msg[1] == 'OK'
            self.flag = "CLOSE"
        self.pump.write('')


    def func_msg(self, d):
        if self.start:
            print('Prot_Sprite::func:: on spawn')
            self.register_key()
            self.start = False
            print('Prot_Sprite::func:: finish spawn actions')

        msg = d.msg
        imp = d.imp
        (sender, msg) = msg
        if msg[0] == "pay" and self.pid == self.P_r:
            _, _state, _sig = msg
            self.recv_pay(_state, _sig)
        elif msg[0] == "UnCoopClose" and self.pid == self.P_r:
            _, _state, _deadline = msg
            self.recv_uncoopclose(_state, _deadline)
        elif msg[0] == "closed":
            _, _state = msg
            self.write('p2z', ('close', _state[0], _state[1]))
        else: self.pump.write('')

