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

        self.nonce = -1
        self.balances = [10]*len(self.parties) # pid => balance of pid
        self.states = [] # (nonce) => {nonce, balances}
        self.sigs = [] # (nonce) => [None] * self.n

        self.isDealer = False
        if self.pid == self.parties[0]: self.isDealer == True

        self.sk = SigningKey.generate()
        self.vk = self.sk.verifying_key

        self.start = True; # whether it's just spawn or not
        self.flag = "OPEN" # OPEN: has a channel open; CLOSE: no channel open


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


    def pay(self, _from, _to, _amount):
        if self.balances[_from] >= _amount:
            self.balances[_from] -= _amount
            self.balances[_to] += _amount
            self.nonce += 1
            self.state = (self.balances, self.nonce)
            self.write('p2f',
                ((self.sid, 'F_channel'), # (sid, tag)
                 ("send", _to, ("pay", (_from, _to, _amount), self.state, 'P_s sig'), 0) # msg
                )
            )
            assert wait_for(self.channels['f2p']).msg[1] == 'OK'
            self.write('p2z', 'OK')
        else:
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

        if msg[0] == "pay":
            _sender = self.pid
            _recipient, _amount = msg[1]
            self.pay(_sender, _recipient, _amount)
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


    def recv_pay(self, _info, _state, _sig):
        # TODO: actions on receiving off-chain payment
        _sender, _recipient, _amount = _info
        _balances, _nonce = _state
        if self.flag == "OPEN" and _nonce == self.nonce + 1 and self.check_sig(_sig, _state, _sender):
            self.balances[_sender] -= _amount
            self.balances[_recipient] += _amount
            self.nonce = _nonce
            assert self.balances == _balances

            self.states.append(_state)
            self.sigs.append(_sig)

            self.write('p2z', ("pay", _info))
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
        ((_sid, _from), msg) = msg

        if msg[0] == "pay":
            _, _info, _state, _sig = msg
            self.recv_pay(_info, _state, _sig)
        elif msg[0] == "UnCoopClose" and self.pid == self.P_r:
            _, _state, _deadline = msg
            self.recv_uncoopclose(_state, _deadline)
        elif msg[0] == "closed":
            _, _state = msg
            self.write('p2z', ('close', _state[0], _state[1]))
        else: self.pump.write('')

