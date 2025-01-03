import datetime
import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart, get_accounts,
    create_fiscalyear)
from trytond.modules.account_invoice.tests.tools import (
    set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):
        activate_modules('purchase_draft')

        # Create company
        _ = create_company()
        company = get_company()

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create customer
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()

        # Create account categories
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        fiscalyear = set_fiscalyear_invoice_sequences(create_fiscalyear(company))
        fiscalyear.click('create_period')


        # Create products
        ProductUom = Model.get('product.uom')
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        template = ProductTemplate()
        template.name = 'Product'
        template.default_uom = unit
        template.type = 'goods'
        template.purchasable = True
        template.account_category = account_category
        template.save()
        product1 = Product()
        product1.template = template
        product1.save()
        product2 = Product()
        product2.template = template
        product2.save()

        # Create purchase to test shipment workflow
        Purchase = Model.get('purchase.purchase')
        purchase = Purchase()
        purchase.party = supplier
        purchase.invoice_method = 'order'
        purchase_line = purchase.lines.new()
        purchase_line.product = product1
        purchase_line.quantity = 2
        purchase_line.unit_price = Decimal('10')
        purchase.save()
        purchase.click('quote')
        self.assertEqual(purchase.state, 'quotation')

        # Ensure purchase can be moved to draft in several states
        purchase.click('draft')
        self.assertEqual(purchase.state, 'draft')

        purchase.click('quote')
        purchase.click('confirm')
        self.assertEqual(purchase.state, 'processing')
        purchase.click('draft')
        self.assertEqual(purchase.state, 'draft')

        def create_shipment(purchase):
            Move = Model.get('stock.move')
            ShipmentIn = Model.get('stock.shipment.in')
            shipment = ShipmentIn()
            shipment.supplier = supplier
            for move in purchase.moves:
                incoming_move = Move(move.id)
                shipment.incoming_moves.append(incoming_move)
            shipment.save()
            return shipment

        shipment = create_shipment(purchase)
        purchase.click('draft')
        self.assertEqual(purchase.state, 'draft')

        purchase.click('quote')
        purchase.click('confirm')
        self.assertEqual(purchase.state, 'processing')
        shipment = create_shipment(purchase)
        shipment.click('receive')
        purchase.click('draft')
        self.assertEqual(purchase.state, 'processing')

        # Create purchase to test invoice workflow
        purchase = Purchase()
        purchase.party = supplier
        purchase.invoice_method = 'order'
        purchase_line = purchase.lines.new()
        purchase_line.product = product1
        purchase_line.quantity = 2
        purchase_line.unit_price = Decimal('10')
        purchase_line = purchase.lines.new()
        purchase_line.product = product2
        purchase_line.quantity = 2
        purchase_line.unit_price = Decimal('10')
        purchase.save()
        purchase.click('quote')
        purchase.click('confirm')
        self.assertEqual(purchase.state, 'processing')
        self.assertEqual(len(purchase.invoices), 1)

        # Ensure purchase does not move to draft if invoices is posted
        invoice, = purchase.invoices
        invoice.invoice_date = datetime.date.today()
        invoice.click('post')
        self.assertEqual(invoice.state, 'posted')
        purchase.reload()
        purchase.click('draft')
        self.assertEqual(purchase.state, 'processing')
