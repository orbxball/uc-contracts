from uc.itm import UCWrappedFunctionality
from uc.utils import wait_for
import logging
log = logging.getLogger(__name__)

class Broadcast_and_Offchain_Channel(UCWrappedFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):    
        self.ssid = sid[0]
        self.func = sid[1]
        self.contract = sid[2]
        self.parties = sid[3]
        self.delta = sid[4] # time unit of mining block
        
        UCWrappedFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
        
        self.leakbuffer = None
        self.flag = 'OffChain'
        self.nonce = 0
        self.balances = [0] * len(self.parties)
        self.T_settle = 2 * self.delta
        self.T_deadline = -1
        self.state = (self.balances, self.nonce)


    def clock_round(self):
        ret = self.write_and_wait(
            ch='f2w', msg=(
                (self.sid, 'F_Wrapper'), ('clock-round',)
            ),
            read='w2f'
        )
        return ret[1]


    def party_msg(self, d):
        (_sid, _sender), msg = d.msg
        imp = d.imp

        if msg[0] == "broadcast":
            _, _msg, _imp = msg
            self.broadcast(_msg, _imp)
        elif msg[0] == "send":
            _, _to, _msg, _imp = msg
            if imp >= _imp:
                self.send_to(_to, _msg, _imp)
            self.write('f2p', ((_sid, _sender), 'OK'))
        else:
            self.pump.write('')


    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp
        (_sid, _from), (msg) = msg
        
        if msg[0] == 'exec':
            _,name,args = msg
            f = getattr(self, name)
            f(*args)
        else:
            self.pump.write('')


    def process_send_to(self, to, msg, imp):
        self.write('f2p', (to, msg), imp)

    def send_to(self, to, msg, imp):
        ret = self.write_and_wait_expect(
            ch='f2w', msg=(
                (self.sid, 'F_Wrapper'), 
                ('schedule', 'process_send_to', ((self.sid, to), msg, imp), 1)
            ),
            read='w2f', expect=((self.sid, 'F_Wrapper'), ('OK',))
        )
        self.leak(('send', msg), 0)


    def broadcast(self, msg, imp):
        print(f"\n broadcast to {self.parties}\n")
        for p in range(len(self.parties)):
            self.send_to(p, msg, imp)
        self.leak(('broadcast', msg), 0)
        self.pump.write('')
