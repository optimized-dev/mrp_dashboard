from odoo import fields, models, tools

class DemandForecast(models.Model):
    _name = 'demand.forecast'
    _auto = False
    _description = 'Demand Forecast'

    month = fields.Char(string="Month")
    mrp_date = fields.Date(string="MRP Date")
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    product_name = fields.Char(string='Product Name')
    sales_qty = fields.Float(string='Sales Qty')
    mrp_planned_qty = fields.Float(string='MRP Planned Qty')

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    mp.id AS id,
                    TO_CHAR(DATE_TRUNC('month', mp.planning_date), 'YYYY-Month') AS month,
                    mp.planning_date AS mrp_date,
                    pt.id AS product_tmpl_id,
                    pt.name AS product_name,
                    COALESCE(SUM(sol.product_uom_qty), 0) AS sales_qty,
                    mp.product_uom_qty AS mrp_planned_qty
                FROM mrp_planning mp
                JOIN product_template pt
                    ON pt.id = mp.product_id
                LEFT JOIN product_product pp
                    ON pp.product_tmpl_id = pt.id
                LEFT JOIN sale_order_line sol
                    ON sol.product_id = pp.id
                LEFT JOIN sale_order so
                    ON so.id = sol.order_id
                   AND DATE(so.date_order) = DATE(mp.planning_date)
                WHERE mp.planning_date >= CURRENT_DATE
                GROUP BY
                    mp.id, mp.planning_date, pt.id, pt.name, mp.product_uom_qty
                ORDER BY
                    mp.planning_date, pt.name
            )
        """)
