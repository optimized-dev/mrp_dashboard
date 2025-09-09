from odoo import fields, models, tools

class CurrentProductionStatus(models.Model):
    _name = 'current.production.status'
    _auto = False
    _description = 'Current Production Status'

    product_id = fields.Many2one('product.template', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    planning_date = fields.Date(string='Planning Date', readonly=True)
    production_start = fields.Datetime(string='Production Start', readonly=True)
    production_end = fields.Datetime(string='Production End', readonly=True)
    product_uom_qty = fields.Float(string='Planned Qty', readonly=True)
    actual_qty = fields.Float(string='Actual Qty', readonly=True)
    progress_percentage = fields.Float(string='Progress %', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
                CREATE OR REPLACE VIEW %s AS
                SELECT
                    row_number() OVER() AS id,
                    pt.id AS product_id,
                    pt.name AS product_name,
                    mp.planning_date,
                    mp.production_start,
                    mp.production_end,
                    mp.product_uom_qty,
                    mp.actual_qty,
                    CASE 
                        WHEN mp.product_uom_qty > 0 
                        THEN ROUND((mp.actual_qty::decimal / mp.product_uom_qty::decimal) * 100, 2)
                        ELSE 0
                    END AS progress_percentage
                FROM
                    mrp_planning mp
                JOIN
                    product_template pt ON pt.id = mp.product_id
                WHERE
                    mp.planning_date = CURRENT_DATE;
            """ % self._table)
