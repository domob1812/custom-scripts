#! /usr/bin/env python
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import * # noqa: F401
from future.utils import iteritems

from jmbase import jmprint, get_log
from jmclient import YieldGeneratorBasic, ygmain

# YIELD GENERATOR SETTINGS ARE NOW IN YOUR joinmarket.cfg CONFIG FILE
# (You can also use command line flags; see --help for this script).

# Optionally, the maker bot can be made to send coins from the lowest
# mixdepth to a list of external addresses (rather than keep them frozen
# in the lowest depth).  If the following array contains some addresses,
# then coins will be sent to those in order.  Each address will only be
# used once, and taken off the list once a transaction for it has been
# seen on the network.  (Although in a race condition it could happen
# that the same address is used twice.)
#
# Note:  When the script is restarted, all addresses will be considered
# available again.  So it is the user's responsibility to update the list
# on each restart according to what they need.  (Remove used addresses
# and perhaps add more unused ones.)
send_to = []


class YieldGeneratorAcyclic(YieldGeneratorBasic):
    """A yield-generator bot that sends funds linearly through the
    mixdepths, but not back from the "lowest" depth to the beginning.
    Instead, it lets funds accumulate there, so that they can then be manually
    sent elsewhere as needed."""

    def __init__(self, wallet_service, offerconfig):
        super(YieldGeneratorAcyclic, self).__init__(wallet_service, offerconfig)

    def get_available_mixdepths(self):
        balances = self.wallet_service.get_balance_by_mixdepth(verbose=False)

        # If we have external addresses (which we would use to send to from
        # the lowest mixdepth), then we can use coins from all mixdepths.
        if send_to:
            return balances

        # Otherwise, we only can spend from all but the last mixdepth.
        return {m: b for m, b in iteritems(balances)
                     if m < self.wallet_service.mixdepth}

    def select_output_address(self, input_mixdepth, offer, amount):
        assert input_mixdepth <= self.wallet_service.mixdepth
        if input_mixdepth == self.wallet_service.mixdepth:
            if not send_to:
                jlog.warning('no more external addresses left, cancelling')
                return None
            return send_to[0]

        return super(YieldGeneratorAcyclic, self)\
            .select_output_address(input_mixdepth, offer, amount)

    def on_tx_unconfirmed(self, offer, txid):
        # If the cjaddr is in our send_to list, remove it from there.
        # After that, we just continue processing as per the superclass.
        if offer['cjaddr'] in send_to:
            jlog.info('sent to external address %s' % offer['cjaddr'])
            send_to.remove(offer['cjaddr'])
            if not send_to:
                jlog.warning('all external addresses have been used')

        return super(YieldGeneratorAcyclic, self).on_tx_unconfirmed(offer, txid)


if __name__ == "__main__":
    ygmain(YieldGeneratorAcyclic, nickserv_password='')
    jmprint('done', "success")
