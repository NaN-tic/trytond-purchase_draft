# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import PoolMeta, Pool
from trytond.model import fields
from trytond.pyson import Eval


class Purchase(metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    allow_draft = fields.Function(
        fields.Boolean("Allow Draft Purchase"), 'get_allow_draft')

    @classmethod
    def __setup__(cls):
        super().__setup__()

        cls._transitions |= set((('processing', 'draft'),))
        cls._buttons['draft']['invisible'] = ~Eval('allow_draft', False)
        cls._buttons['draft']['depends'] += tuple(['allow_draft'])

    @classmethod
    def get_allow_draft(cls, purchases, name):
        res = dict((x.id, False) for x in purchases)

        for purchase in purchases:
            if purchase.state in ('draft', 'done'):
                continue
            moves = [m for line in purchase.lines for m in line.moves
                + line.moves_ignored + line.moves_recreated 
                if m.state != 'draft']
            if moves:
                continue
            shipments = [s for s in purchase.shipments
                if s.state != 'draft']
            shipment_return = [
                s for s in purchase.shipment_returns if s.state != 'draft']
            if shipments or shipment_return:
                continue
            invoices = [i for i in purchase.invoices
                if i.state != 'draft']
            invoic_liness = [il for line in purchase.lines
                for il in line.invoice_lines if not il.invoice]
            if invoices or invoic_liness:
                continue
            # in case not continue, set to True
            res[purchase.id] = True
        return res

    @classmethod
    def draft(cls, purchases):
        pool = Pool()
        Move = pool.get('stock.move')
        Shipment = pool.get('stock.shipment.in')
        ShipmentReturn = pool.get('stock.shipment.in.return')
        InvoiceLine = pool.get('account.invoice.line')
        Invoice = pool.get('account.invoice')

        moves = []
        shipments = []
        shipment_return = []
        invoices = []
        invoic_liness = []
        for purchase in purchases:
            moves.extend([m for line in purchase.lines for m in line.moves
                if m.state == 'draft' and not m.shipment])
            shipments.extend(
                [s for s in purchase.shipments if s.state == 'draft'])
            shipment_return.extend(
                [s for s in purchase.shipment_returns if s.state == 'draft'])
            invoices.extend([i for i in purchase.invoices
                if i.state == 'draft'])
            invoic_liness.extend([il for line in purchase.lines
                for il in line.invoice_lines if not il.invoice])

        Move.delete(moves)
        Shipment.delete(shipments)
        ShipmentReturn.delete(shipment_return)
        InvoiceLine.delete(invoic_liness)
        Invoice.delete(invoices)

        super().draft(purchases)
