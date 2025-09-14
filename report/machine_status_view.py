from odoo import models, fields, api

class MachineStatusView(models.Model):
    _name = "machine.status.view"
    _description = "Machine Status View"
    _auto = False  # Read-only view, no table auto-created

    machine_id = fields.Many2one('machine.indicators', string="Machine", readonly=True)
    machine_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Ready'),
        ('blocked', 'Not Ready'),
        ('started', 'Started')
    ], string='Kanban State', readonly=True)
    status_emoji = fields.Char(string="Status", readonly=True)

    @api.model
    def init(self):
        # Drop the view if it exists and create it again
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW machine_status_view AS
            SELECT
                mi.id AS id,
                mi.id AS machine_id,
                mi.state AS machine_state,
                CASE mi.state
                    WHEN 'normal' THEN '🟢 Running'
                    WHEN 'done' THEN '✅ Ready'
                    WHEN 'blocked' THEN '🔴 Fault / Not Ready'
                    WHEN 'started' THEN '🟡 Started'
                    ELSE '❓ Unknown'
                END AS status_emoji
            FROM machine_indicators mi
            WHERE mi.inspection_date = CURRENT_DATE
              AND mi.state = 'started';
        """)
