from math import floor, ceil
from uc.itm import UCWrappedFunctionality
from uc.utils import wait_for
from collections import defaultdict
import logging


class Flags:
    OK = 0
    DISPUTE = 1
    PENDING = 2

class Contract_State:
    def __init__(self, update_f):
        self.bestRound = -1
        self.state = None
        self.flag = Flags.OK
        self.deadline = None
        self.applied = set()
        self.update_f = update_f

        self.cached_event = None

        self.deadline_amount = 7 # Q: is this the delta in sprite paper? why 7?
        self.received_input = defaultdict(bool)
        self.round_input = defaultdict(dict)

    def evidence(self, r, state_, out, sigs, tx):
        print('r: {}, state_: {}, out: {}, sigs: {}'.format(r, state_, out, sigs))
        if r > self.bestRound: return

        # TODO: check all signatures on r||state||out
        if self.flag == Flags.DISPUTE:
           self.flag = Flags.OK
           self.emit( ("EventOffChain", self.bestRound+1) )
        self.bestRound = r
        self.state = state_
        # TODO: invoke aux contract
        self.applied.add(r)

    def dispute(self, r, tx):
        T = self.block_number() # Q: how to get the current block number
        if r != self.bestRound+1: return
        if self.flag != Flags.OK: return

        self.flag = Flags.DISPUTE
        self.deadline = T + self.deadline_amount
        self.emit( ("EventDispute", r, self.dealine) )

    def resolve(self, r, tx):
        T = self.block_number()
        if r != self.bestRound + 1: return
        if self.flag != Flags.PENDING: return
        if T < self.deadline: return

        self.state, o = self.update_f(self.state, self.round_input[r], [])
        self.flag = Flags.OK
        self.emit( ("EventOnChain", r, self.state) )
        self.bestRound += 1

    def input(self, pid, r, _input, tx):
        if self.received_input[pid]: return
        self.received_input[pid] = True
        self.round_input[self.round][pid] = _input

    def party_msg(self, tx):
        print('tx', tx)
        getattr(self, tx['func'])(*tx['args'], tx)

    def emit(self, event):
        self.cached_event = event
