import dump
import comm
import gevent
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties, ITMPrinterAdversary
from utils import z_mine_blocks, z_send_money, z_get_balance
from g_ledger import Ledger_Functionality, LedgerITM
from collections import defaultdict
from gevent.queue import Queue, Channel
from f_paymentchannel import PaymentChannel_Functionality, PayITM
from protected_wrapper import Protected_Wrapper, ProtectedITM

'''
Blockchain Functionality
'''
g_ledger = Ledger_Functionality('sid1', 0)
protected,ledger_itm = ProtectedITM('sid1', 0, g_ledger)
comm.setFunctionality(ledger_itm)

'''
Payment Channel functionality
'''
idealf, pay_itm = PayITM('sid2',1, ledger_itm, 2, 3)
comm.setFunctionality(pay_itm)

'''
Ideal world parties
'''
iparties = createParties('sid2', range(2,4), pay_itm)
comm.setParties(iparties)
for party in iparties:
    gevent.spawn(party.run)

''' 
Extra party
'''
simparty = ITMPassthrough('sid2', 23)
comm.setParty(simparty)
simparty.init(ledger_itm)
gevent.spawn(simparty.run)

#################### EXPERIMENT ########################
p1 = iparties[0]
p2 = iparties[1]

'''Adversary'''
adversary = ITMAdversary('sid2',6)
comm.setAdversary(adversary)
#g_ledger.set_backdoor(adversary.leak)
#idealf.set_backdoor(adversary.leak)
adversary.addParty(p1); adversary.addParty(p2)
gevent.spawn(adversary.run)


'''
Start functionality itms
'''
gevent.spawn(ledger_itm.run)
gevent.spawn(pay_itm.run)

'''p1 and p2 needs funds, so mine blocks and send them money'''
z_mine_blocks(1, simparty, ledger_itm)
z_send_money(10, p1, simparty, ledger_itm)
z_send_money(10, p2, simparty, ledger_itm)
z_mine_blocks(8, simparty, ledger_itm)

'''
Users deposit
'''
p1.input.set( ('deposit', 10) )
dump.dump_wait()
z_mine_blocks(1, simparty, ledger_itm)
p2.input.set( ('deposit', 1) )
dump.dump_wait()
z_mine_blocks(8, simparty, ledger_itm)

'''Check channel balanace is correct'''
balance = p1.subroutine_call(
    ('balance',)
)
print('balance', balance)
assert balance[0] == 10 and balance[1] == 1
'''Send my homeboi p2 some money bruh
    ....ok....
'''
p1.input.set(
    ('pay', 2)
)
dump.dump_wait()
balance = p2.subroutine_call(
    ('balance',)
)
print('balance', balance)
assert balance[0] == 10-2 and balance[1] == 1+2, 'p1:(%d), p2:(%d)' % (balance[0], balance[1])


''' p1 multiple pays'''
p1.input.set(
    ('pay', 1)
)
dump.dump_wait()
p1.input.set(
    ('pay', 1)
)
dump.dump_wait()
p1.input.set(
    ('pay', 1)
)
dump.dump_wait()
p1.input.set(
    ('pay', 1)
)
dump.dump_wait()

balance = p2.subroutine_call(
    ('balance',)
)
print('balance', balance)
assert balance[0] == 10-2-4 and balance[1] == 1+2+4, 'p1:(%d), p2:(%d)' % (balance[0], balance[1])


print('ADVERSARY corrupting p2 and sending payment...')
''' Adversray corrupt p2'''
adversary.input.set(
    ('party-input', (p1.sid,p1.pid), 
        ('pay', 2))
)
dump.dump_wait()
