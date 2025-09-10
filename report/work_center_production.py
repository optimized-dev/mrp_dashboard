from odoo import api, fields, models, tools

class WorkCentreProduction(models.Model):
    _name = 'work.centre.production'
    _description = 'Work Centre Production'
    _auto = False

    id = fields.Integer()
    operation_name = fields.Char(string="Operation Name")
    line_id = fields.Many2one('mrp.line', string='Line')
    time_from = fields.Float(string="Time From")
    time_to = fields.Float(string="Time To")
    product_id = fields.Many2one('product.product', string="Product")
    planned_qty = fields.Float(string="Planned Qty")
    out_qty = fields.Float(string="Out Qty")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'work_centre_production')
        self._cr.execute("""
            CREATE OR REPLACE VIEW work_centre_production AS
            SELECT
                ROW_NUMBER() OVER () AS id,
                pdo.name AS operation_name,
                pdoto.line_id,
                tod.time_from,
                tod.time_to,
                tod.product_id,
                tod.planned_qty,
                tod.out_qty
            FROM transfer_out_details tod
            JOIN production_daily_operation_transfer_out pdoto
                ON pdoto.id = tod.production_daily_operation_transfer_out_id
            JOIN production_daily_operation pdo
                ON pdo.id = pdoto.production_daily_operation_id
        """)
