"""A payment layer with one real job and a lot of ceremony."""
from abc import ABC, abstractmethod


class PaymentGateway(ABC):
    """Abstract seam priced for swappable gateways."""
    @abstractmethod
    def charge(self, amount): ...


class StripeGateway(PaymentGateway):
    def charge(self, amount):
        return {"ok": True, "amount": amount}


class PaymentManager:
    """Forwards to the gateway. That is all it does."""
    def __init__(self, gateway):
        self._g = gateway

    def charge(self, amount):
        return self._g.charge(amount)


def do_charge(manager, amount):
    return manager.charge(amount)


def process(amount, currency="usd", retries=3, dry_run=False):
    """`retries` and `dry_run` are knobs no caller ever turns."""
    mgr = PaymentManager(StripeGateway())
    return do_charge(mgr, amount)


class LegacyRefundHelper:
    """Nothing references this. Pure unpaid load."""
    def refund(self, txn):
        return {"refunded": txn}
