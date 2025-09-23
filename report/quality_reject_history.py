from odoo import models, fields, tools

class QualityRejectHistory(models.Model):
    _name = 'quality.reject.history'
    _description = 'Quality Reject History'
    _auto = False
    _order = 'date desc'

    date = fields.Date(string="Planning Date")
    product_id = fields.Many2one('product.template', string="Product")
    total_produce = fields.Float(string="Total Produced")
    rejected_units = fields.Float(string="Rejected Units")
    rejection_percentage = fields.Float(string="Rejection %")
    damage_type_id = fields.Many2one('damage.type', string="Damage Type")
    severity = fields.Selection([
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, help="Indicates the severity of the damage type.")
    fpy = fields.Float(string="First Pass Yield %")
    workcenter_id = fields.Many2one('mrp.workcenter', string="Workcenter")


    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE or REPLACE VIEW {self._table} AS (
                SELECT 
                    row_number() over () as id, 
                    mp.planning_date as date, 
                    pt.id as product_id, 
                    coalesce(mp.actual_qty, 0) as total_produce,
                    sum(coalesce(dd.damage_qty, 0)) as rejected_units,
                    CASE 
                       WHEN coalesce(mp.actual_qty, 0) = 0 THEN 0
                       ELSE sum(coalesce(dd.damage_qty, 0)) * 100.0 / mp.actual_qty
                    END as rejection_percentage,
                    dt.id as damage_type_id,
                    dt.severity,
                    CASE 
                        WHEN coalesce(mp.actual_qty, 0) = 0 THEN 0
                        ELSE round(
                            (
                                (coalesce(mp.actual_qty,0) - sum(coalesce(dd.damage_qty,0)))::numeric 
                                / nullif(mp.actual_qty,0)::numeric
                            ) * 100, 
                            2
                        )
                    END as fpy,
                    mwc.id as workcenter_id
                FROM mrp_planning mp 
                JOIN product_template pt ON pt.id = mp.product_id
                LEFT JOIN production_daily_operation AS pdo 
                    ON pdo.production_plan_id = mp.id
                LEFT JOIN production_daily_operation_damage pdod 
                    ON pdod.production_daily_operation_id = pdo.id
                LEFT JOIN damage_details dd 
                    ON dd.production_daily_operation_damage_id = pdod.id
                LEFT JOIN damage_type dt 
                    ON dt.id = dd.damage_type_id
                LEFT JOIN mrp_workcenter mwc 
                    ON pdo.production_stage_id = mwc.id
                WHERE mp.planning_date BETWEEN current_date - interval '365 Days' AND current_date and pdo.state != 'cancel'
                GROUP BY 
                    mp.planning_date, 
                    pt.id, 
                    mp.actual_qty,
                    dt.id,
                    dt.severity,
                    mwc.id
            )
        """)
