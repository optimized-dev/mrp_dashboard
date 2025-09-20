from odoo import models, fields, tools

class RealTimeProductionHealth(models.Model):
    _name = 'real.time.production.health'
    _description = 'Real Time Production Health'
    _auto = False  # This is a SQL view
    _order = 'machine_id'

    machine_id = fields.Many2one('machine.master', string='Machine')
    uptime_min = fields.Float(string='Uptime (min)')
    downtime_min = fields.Float(string='Downtime (min)')
    total_produce = fields.Float(string='Total Produced')
    good_units = fields.Float(string='Good Units')
    total_defects = fields.Float(string='Defects')
    shift_planned_working_time = fields.Float(string='Shift Planned Time')
    scheduled_min = fields.Float(string='Scheduled Time (min)')

    availability_percent = fields.Float(string='Availability %')
    ideal_cycle_time = fields.Float(string='Ideal Cycle Time (sec)')
    performance_percent = fields.Float(string='Performance %')
    quality_percent = fields.Float(string='Quality %')
    oee_percent = fields.Float(string='OEE %')
    health_status = fields.Char(string='Health Status')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'real_time_production_health')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW real_time_production_health AS
            WITH base AS (
                SELECT 
                    mm.id AS machine_id,
                    ROUND(
                        (pdpps.machine_rate - COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60, 0))::numeric, 
                        2
                    ) AS uptime_min,
                    ROUND(
                        COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60, 0)::numeric, 
                        2
                    ) AS downtime_min,
                    pdo.total_out + pdo.total_wastage AS total_produce,
                    pdo.total_out AS good_units,
                    pdo.total_wastage AS total_defects,
                    rc.shift_planned_working_time,
                    (rca.hour_to - rca.hour_from) * 60 AS scheduled_min
                FROM mrp_planning mp
                JOIN production_daily_plan_process_stages pdpps 
                    ON pdpps.daily_production_plan_id = mp.id
                JOIN production_daily_operation AS pdo 
                    ON pdo.production_plan_id = mp.id
                JOIN mrp_workcenter mw 
                    ON mw.production_stage_id = pdpps.production_stage_id
                JOIN used_location ul 
                    ON ul.work_center_id = mw.id
                JOIN machine_master mm 
                    ON mm.location_id = ul.id
                JOIN resource_calendar AS rc 
                    ON mw.resource_calendar_id = rc.id
                JOIN resource_calendar_attendance rca 
                    ON rc.id = rca.calendar_id
                    AND rca.dayofweek::int = ((EXTRACT(DOW FROM CURRENT_DATE)::int + 6) % 7)
                LEFT JOIN maintenance_request mr 
                    ON mr.machine_id = mm.id 
                    AND mr.maintenance_request_type = 'machine' 
                    AND mr.maintenance_type = 'corrective' 
                    AND DATE(mr.request_date_time) = mp.planning_date
                WHERE mp.planning_date = CURRENT_DATE
            )
            SELECT 
                   row_number() OVER() AS id,
                   base.*,
                   uptime_min / NULLIF(scheduled_min,0) * 100 AS availability_percent,
                   (uptime_min * 60) / NULLIF(total_produce + total_defects,0) AS ideal_cycle_time,
                   (( (uptime_min * 60) / NULLIF(total_produce + total_defects,0) ) * (total_produce + total_defects)) / NULLIF(uptime_min * 60,0) * 100 AS performance_percent,
                   (good_units::numeric / NULLIF(total_produce,0)) * 100 AS quality_percent,
                   ( (uptime_min / NULLIF(scheduled_min,0) * 100) *
                     ( ((uptime_min * 60) / NULLIF(total_produce + total_defects,0) ) * (total_produce + total_defects)) / NULLIF(uptime_min * 60,0) * 100 ) *
                     (good_units::numeric / NULLIF(total_produce,0)) / 10000 AS oee_percent,
                   CASE
                       WHEN ( (uptime_min / NULLIF(scheduled_min,0) * 100) *
                              ( ((uptime_min * 60) / NULLIF(total_produce + total_defects,0) ) * (total_produce + total_defects)) / NULLIF(uptime_min * 60,0) * 100 ) *
                              (good_units::numeric / NULLIF(total_produce,0)) / 10000 >= 85 THEN '🟢 Healthy'
                       WHEN ( (uptime_min / NULLIF(scheduled_min,0) * 100) *
                              ( ((uptime_min * 60) / NULLIF(total_produce + total_defects,0) ) * (total_produce + total_defects)) / NULLIF(uptime_min * 60,0) * 100 ) *
                              (good_units::numeric / NULLIF(total_produce,0)) / 10000 >= 65 THEN '🟠 At Risk'
                       ELSE '🔴 Critical'
                   END AS health_status
            FROM base;
        """)
