# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import PoolMeta, Pool
from trytond.model import fields
from trytond.pyson import Eval
from trytond.transaction import Transaction


class Purchase(metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    allow_draft = fields.Function(
        fields.Boolean("Allow Draft Purchase"), 'get_allow_draft')

    @classmethod
    def __setup__(cls):
        super().__setup__()

        cls._transitions |= set((('processing', 'draft'),))
        cls._buttons['draft']['invisible'] = ~Eval('allow_draft', False)
        cls._buttons['draft']['depends'] += ['allow_draft']

    def get_allow_draft(self, name):
        if (self.state in ('draft', 'done')
                or any([m for line in self.lines for m in line.moves
                        if m.state not in ('draft', 'cancelled')])
                or any([x for line in self.lines for x in line.invoice_lines
                        if x.invoice and x.invoice.state not in (
                            'draft', 'cancelled')])):
            return False
        return True

    @classmethod
    def draft(cls, purchases):
        pool = Pool()
        Move = pool.get('stock.move')
        Shipment = pool.get('stock.shipment.in')
        ShipmentReturn = pool.get('stock.shipment.in.return')
        InvoiceLine = pool.get('account.invoice.line')
        Invoice = pool.get('account.invoice')
        LineRecreated = pool.get('purchase.line-recreated-stock.move')
        LineIgnored = pool.get('purchase.line-ignored-stock.move')

        moves = []
        shipments = []
        shipment_return = []
        invoices = []
        invoice_lines = []
        for purchase in purchases:
            if not purchase.allow_draft:
                continue
            moves += [m for line in purchase.lines for m in line.moves]
            shipments += purchase.shipments
            shipment_return += purchase.shipment_returns
            invoices += purchase.invoices
            invoice_lines += [il for line in purchase.lines
                for il in line.invoice_lines if not il.invoice]
        if moves:
            line_recreateds = LineRecreated.search([
                    ('move', 'in', moves),
                    ])
            with Transaction().set_user(0):
                LineRecreated.delete(line_recreateds)
            line_ignoreds = LineIgnored.search([
                    ('move', 'in', moves),
                    ])
            with Transaction().set_user(0):
                LineIgnored.delete(line_ignoreds)
                Move.delete(moves)
        with Transaction().set_user(0):
            Shipment.delete(shipments)
            ShipmentReturn.delete(shipment_return)
            InvoiceLine.delete(invoice_lines)
            Invoice.delete(invoices)
        super().draft(purchases)
