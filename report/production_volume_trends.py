from odoo import models, fields, tools

class ProductionVolumeTrends(models.Model):
    _name = 'production.volume.trends'
    _description = 'Production Volume Trends'
    _auto = False

    date = fields.Date(string='Date')
    product_id = fields.Many2one('product.template', string='Product')
    production_stage_id = fields.Many2one('production.stage', string='Production Stage')
    planned_qty = fields.Float(string='Planned Quantity')
    actual_qty = fields.Float(string='Actual Quantity')
    deviation_units = fields.Float(string='Deviation Units')
    deviation_percentage = fields.Float(string='Deviation %')
    plan_adherence_percentage = fields.Float(string='Plan Adherence %')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'production_volume_trends')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW production_volume_trends AS (
                SELECT 
                    pdo.id AS id,
                    mp.planning_date AS date,
                    pt.id AS product_id,
                    pdo.production_stage_id AS production_stage_id,
                    pdo.total_planned_qty AS planned_qty,
                    pdo.total_out AS actual_qty,
                    (pdo.total_out - pdo.total_planned_qty) AS deviation_units,
                    CASE 
                        WHEN pdo.total_planned_qty > 0 
                        THEN ROUND(((pdo.total_out - pdo.total_planned_qty) * 100.0 / pdo.total_planned_qty)::numeric, 1)
                        ELSE 0
                    END AS deviation_percentage,
                    CASE 
                        WHEN pdo.total_planned_qty > 0 
                        THEN ROUND((pdo.total_out * 100.0 / pdo.total_planned_qty)::numeric, 1)
                        ELSE 0
                    END AS plan_adherence_percentage
                FROM production_daily_operation pdo
                JOIN mrp_planning mp ON pdo.production_plan_id = mp.id
                JOIN product_template pt ON mp.product_id = pt.id
                WHERE mp.planning_date <= CURRENT_DATE
            )
        """)
