from odoo import fields, models, tools


class RecoveryRatioHistory(models.Model):
    _name = 'recovery.ratio.history'
    _auto = False
    _description = 'Recovery Ratio History'

    planning_date = fields.Date(string='Date')
    production_stage_id = fields.Many2one('production.stage', string='Production Stage')
    product_id = fields.Many2one('product.template', string='Product')
    planning_id = fields.Many2one('mrp.planning', string='Planning')
    actual_qty = fields.Float(string='Actual Qty')
    raw_material_input_qty = fields.Float(string='Raw Material Input Qty')
    recovery_ratio = fields.Float(string='Recovery Ratio (%)')
    usable_finished_goods = fields.Float(string='Usable Finished Goods')
    standard_yield = fields.Float(string='Standard Yield (%)')
    loss_quantity = fields.Float(string='Loss Quantity')
    loss_percen = fields.Float(string='Loss %')

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    mp.id AS id,
                    pdo.production_stage_id,
                    mp.product_id,
                    mp.id AS planning_id,
                    mp.planning_date AS planning_date,
                    mp.actual_qty,
                    SUM(COALESCE(prlo.quantity, 0)) AS raw_material_input_qty,
                    ROUND( (mp.actual_qty::numeric / NULLIF(SUM(prlo.quantity), 0)::numeric) * 100 , 2) AS recovery_ratio,
                    SUM(COALESCE(prlo.quantity, 0)) - SUM(COALESCE(mpbl.actual_wastage, 0)) AS usable_finished_goods,
                    (SUM(COALESCE(prlo.quantity, 0)) - SUM(COALESCE(mpbl.actual_wastage, 0)))::numeric 
                        / NULLIF(SUM(COALESCE(prlo.quantity, 0)),0) * 100 AS standard_yield,
                    SUM(COALESCE(mpbl.actual_wastage, 0)) AS loss_quantity,
                    SUM(COALESCE(mpbl.product_qty, 0)) 
                        / NULLIF(SUM(COALESCE(mpbl.actual_wastage, 0)),0) * 100 AS loss_percen
                FROM mrp_planning mp
                JOIN mrp_planning_purchase_requisition_optimized_rel rel
                    ON rel.mrp_planning_id = mp.id
                JOIN purchase_requisition_optimized pro
                    ON pro.id = rel.purchase_requisition_optimized_id
                JOIN purchase_requisition_lines_optimized prlo
                    ON prlo.requisition_id = pro.id
                JOIN mrp_planning_bom_line mpbl 
                    ON mpbl.mrp_planning_line_id = mp.id
                left JOIN production_daily_operation pdo 
                    ON pdo.production_plan_id = mp.id  
                WHERE mp.planning_date <= current_date
                GROUP BY mp.id, mp.actual_qty, pdo.production_stage_id
                ORDER BY mp.id
            )
        """ % self._table)
