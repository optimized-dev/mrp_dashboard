from odoo import fields, models, tools


class WastagePlan(models.Model):
    _name = 'wastage.plan'
    _description = 'Wastage Plan'
    _auto = False

    planning_date = fields.Date(string='Planning Date')
    standard_qty = fields.Float(string='Standard Qty')
    actual_qty = fields.Float(string='Actual Qty')
    wastage_percent = fields.Float(string='Wastage %')

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW wastage_plan AS
            SELECT 
                mp.id as id,
                mp.planning_date,
                SUM(mpbl.product_qty) AS standard_qty,
                SUM(prlo.quantity) AS actual_qty,
                CASE 
                    WHEN SUM(mpbl.product_qty) = 0 THEN 0
                    ELSE ROUND(
                        ((SUM(prlo.quantity) - SUM(mpbl.product_qty))::numeric 
                          / SUM(mpbl.product_qty)) * 100, 2
                    )
                END AS wastage_percent
            FROM mrp_planning mp
            JOIN mrp_planning_bom_line mpbl 
                ON mpbl.mrp_planning_line_id = mp.id
            JOIN mrp_planning_purchase_requisition_optimized_rel rel
                ON rel.mrp_planning_id = mp.id
            JOIN purchase_requisition_optimized pro
                ON pro.id = rel.purchase_requisition_optimized_id
            JOIN purchase_requisition_lines_optimized prlo 
                ON prlo.requisition_id = pro.id
            WHERE mp.planning_date < CURRENT_DATE
            GROUP BY mp.id, mp.planning_date
            ORDER BY mp.planning_date
        """)
