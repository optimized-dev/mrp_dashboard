from odoo import fields, models, tools


class RecoveryRatio(models.Model):
    _name = 'recovery.ratio'
    _auto = False
    _description = 'Recovery Ratio'

    planning_date = fields.Date(string='Planning Date')
    product_uom_qty = fields.Float(string='Planned Qty')
    actual_qty = fields.Float(string='Actual Qty')
    recovery_ratio = fields.Float(string='Recovery Ratio%', digits=(12, 2))

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    mp.id,
                    mp.planning_date,
                    mp.product_uom_qty,
                    mp.actual_qty,
                    CASE 
                        WHEN mp.product_uom_qty > 0 
                        THEN ROUND((mp.actual_qty::numeric / mp.product_uom_qty::numeric) * 100, 2)
                        ELSE 0
                    END AS recovery_ratio
                FROM mrp_planning mp
                GROUP BY mp.id, mp.planning_date, mp.product_uom_qty, mp.actual_qty
            )
        """)

