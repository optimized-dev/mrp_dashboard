from odoo import fields, models, tools, api


class StepwiseProductionFlowTracker(models.Model):
    _name = 'stepwise.production.flow.tracker'
    _auto = False
    _description = 'Stepwise Production Flow Tracker'

    production_stage_id = fields.Many2one('production.stage', string="Production Stage")
    total_planned_qty = fields.Float(string="Total Planned Qty")
    total_out = fields.Float(string="Total Out")
    progress = fields.Integer(string="Progress (%)")


    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    pdo.id AS id,
                    pdo.production_stage_id AS production_stage_id,
                    pdo.total_planned_qty AS total_planned_qty,
                    pdo.total_out AS total_out,
    (pdo.total_out / 1000.0) * 100 AS progress
                FROM production_daily_operation pdo
                JOIN production_stage ps 
                  ON pdo.production_stage_id = ps.id
            )
        """ % self._table)
