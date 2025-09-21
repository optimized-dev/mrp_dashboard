from odoo import models, fields, tools

class ShiftPerformanceSummary(models.Model):
    _name = 'shift.performance.summary'
    _description = 'Shift Performance Summary'
    _auto = False

    tod_id = fields.Many2one('transfer.out.details', string='Transfer Out Detail')
    shift_type = fields.Char(string='Shift')
    planned_qty = fields.Float(string='Planned Quantity')
    actual_qty = fields.Float(string='Actual Quantity')
    deviation_percent = fields.Float(string='Deviation %')
    shift_start = fields.Char(string='Shift Start')  # AM/PM formatted
    shift_end = fields.Char(string='Shift End')      # AM/PM formatted
    throughput_rate = fields.Float(string='Throughput Rate')
    status = fields.Char(string='Status')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'shift_performance_summary')
        self._cr.execute("""
            CREATE OR REPLACE VIEW shift_performance_summary AS
            SELECT 
                tod.id AS id,
                tod.id AS tod_id,
                CASE 
                    WHEN tod.time_from >= 6 AND tod.time_from < 14 THEN 'Morning'
                    WHEN tod.time_from >= 14 AND tod.time_from < 22 THEN 'Evening'
                    ELSE 'Night'
                END AS shift_type,
                tod.planned_qty AS planned_qty,
                tod.out_qty AS actual_qty,
                ROUND(
                    ((tod.out_qty - tod.planned_qty) / NULLIF(tod.planned_qty,0))::numeric, 2
                ) AS deviation_percent,
                to_char((tod.time_from || ' hour')::interval, 'HH12:MI AM') AS shift_start,
                to_char((tod.time_to || ' hour')::interval, 'HH12:MI AM') AS shift_end,
                ROUND(
                    (tod.out_qty / NULLIF((tod.time_to - tod.time_from),0))::numeric, 2
                ) AS throughput_rate,
                CASE
                    WHEN (tod.out_qty / NULLIF(tod.planned_qty,0) * 100) >= 95 THEN '✅ Excellent'
                    WHEN (tod.out_qty / NULLIF(tod.planned_qty,0) * 100) >= 80 THEN '⚠️ Moderate'
                    ELSE '❌ Poor'
                END AS status
            FROM mrp_planning mp
            JOIN production_daily_operation pdo 
                ON pdo.production_plan_id = mp.id
            JOIN production_daily_operation_transfer_out pdoto 
                ON pdoto.production_daily_operation_id = pdo.id
            JOIN transfer_out_details tod 
                ON tod.production_daily_operation_transfer_out_id = pdoto.id
            WHERE mp.planning_date = CURRENT_DATE
            ORDER BY tod.time_from
        """)
