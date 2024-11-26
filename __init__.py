# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import purchase


def register():
    Pool.register(
        purchase.Purchase,
        module='puchase_draft', type_='model')
