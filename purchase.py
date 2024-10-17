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
        cls._buttons['draft']['depends'] += ['allow_draft']

    @classmethod
    def get_allow_draft(cls, purchases, name):
        res = dict((x.id, False) for x in purchases)

        for purchase in purchases:
            if purchase.state in ('draft', 'done'):
                continue
            moves = [m.id for line in purchase.lines for m in line.moves
                + line.moves_ignored
                if m.state != 'draft']
            moves_recreated = [m.id for line in purchase.lines
                for m in line.moves_recreated]
            if ((moves and not moves_recreated)
                        or (moves and moves_recreated
                            and sorted(moves) != sorted(moves_recreated))):
                continue
            invoices = [i for i in purchase.invoices + purchase.invoices_ignored
                if i.state != 'draft']
            invoices_recreated = [i for i in purchase.invoices_recreated]
            if ((invoices and not invoices_recreated)
                        or (invoices and invoices_recreated
                            and sorted(invoices) != sorted(invoices_recreated))):
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
        LineRecreated = pool.get('purchase.line-recreated-stock.move')

        moves = []
        shipments = []
        shipment_return = []
        invoices = []
        invoice_lines = []
        for purchase in purchases:
            if not purchase.allow_draft:
                continue
            moves.extend([m for line in purchase.lines for m in line.moves])
            shipments.extend([s for s in purchase.shipments])
            shipment_return.extend([s for s in purchase.shipment_returns])
            invoices.extend([i for i in purchase.invoices])
            invoice_lines.extend([il for line in purchase.lines
                for il in line.invoice_lines if not il.invoice])
        if moves:
            line_recreateds = LineRecreated.search([
                    ('move', 'in', moves),
                    ])
            if line_recreateds:
                LineRecreated.delete(line_recreateds)
            Move.delete(moves)
        if shipments:
            Shipment.delete(shipments)
        if shipment_return:
            ShipmentReturn.delete(shipment_return)
        if invoice_lines:
            InvoiceLine.delete(invoice_lines)
        if invoices:
            Invoice.delete(invoices)

        super().draft(purchases)
