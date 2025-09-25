from odoo import api, fields, models , _

class ProductProduct(models.Model):
    # _name = 'product.product'
    _inherit = 'product.product'

    stored_standard_price = fields.Float(string="Stored Standard Price", compute='_compute_stored_standard_price', store=True)

    @api.depends('standard_price')
    def _compute_stored_standard_price(self):
        for product in self:
            product.stored_standard_price = product.standard_price
