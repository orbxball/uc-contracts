from uc.itm import UCWrappedProtocol
from uc.utils import wait_for
import logging
log = logging.getLogger(__name__)

class Prot_Sprite(UCWrappedProtocol):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.id = sid[2]
        self.delta = sid[2]

        UCWrappedProtocol.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)

        self.nonce = 0
        self.state = (self.b_s, self.b_r, self.nonce)
        #self.states = [] # (nonce) => {nonce, balances}
        #self.sigs = [] # (nonce) => [None] * self.n
        self.flag = 'OPEN'


    def check_sig(self, _sig, _state, _signer):
        return True

    def pay(self, v):
        if self.b_s >= v:
            self.b_s -= v
            self.b_r += v
            self.nonce += 1
            self.state = (self.b_s, self.b_r, self.nonce)
            self.write('p2f', 
                ((self.sid, 'F_contract'), # (sid, tag)
                 ("send", self.P_r, ("pay", self.state, 'P_s sig'), 0) # msg
                )
            )
            assert wait_for(self.channels['f2p']).msg[1] == 'OK'
            self.write('p2z', 'OK')
        else:
            self.pump.write('')

    def close(self):
        if self.flag == "OPEN":
            self.flag = "CLOSE"
            self.write('p2f', 
                ((self.sid, 'F_contract'), # (sid, tag)
                 ('close', self.state, '') # msg
                )
            )
            assert wait_for(self.channels['f2p']).msg[1] == 'OK'
        self.write('p2z', 'OK')
        

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp

        if msg[0] == "pay" and self.pid == self.P_s:
            _, v = msg
            self.pay(v)
        elif msg[0] == "close":
            self.close()
        elif msg[0] == "balance":
            if self.pid == self.P_s: self.write('p2z', ('balance', self.b_s))
            else: self.write('p2z', ('balance', self.b_r))
        else:
            self.pump.write('')

    def recv_pay(self, _state, _sig):
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

