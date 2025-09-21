from odoo import models, fields, tools

class RealTimeProductionHealth(models.Model):
    _name = 'real.time.production.health'
    _description = 'Real Time Production Health'
    _auto = False

    machine_name = fields.Char(string="Machine")
    shift_start = fields.Datetime(string="Shift Start")
    shift_end = fields.Datetime(string="Shift End")
    production_scheduled_time = fields.Float(string="Scheduled Time (min)")
    downtime_min = fields.Float(string="Downtime (min)")
    uptime_min = fields.Float(string="Uptime (min)")
    availability_percent = fields.Float(string="Availability %")
    ideal_cycle_count = fields.Integer(string="Ideal Cycle Count")
    good_units = fields.Float(string="Good Units")
    wastages = fields.Float(string="Wastages")
    total_units = fields.Float(string="Total Units")
    performance_percent = fields.Float(string="Performance %")
    quality_percent = fields.Float(string="Quality %")
    oee_percent = fields.Float(string="OEE %")
    quick_view = fields.Char(string="Quick View")
    product_id = fields.Many2one('product.template', string="Product")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'real_time_production_health')
        self._cr.execute("""
            CREATE OR REPLACE VIEW real_time_production_health AS
            SELECT
                mm.id AS id,
                mm.name AS machine_name,
                mp.production_start AS shift_start,
                mp.production_end AS shift_end,
                ROUND((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric,2) AS production_scheduled_time,
                ROUND(COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0),2) AS downtime_min,
                ROUND((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric,2) - ROUND(COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0),2) AS uptime_min,
                CASE 
                    WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0 
                    THEN ROUND(
                        (( (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0) )
                        / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100)::numeric,2
                    )
                    ELSE 0
                END AS availability_percent,
                1 AS ideal_cycle_count,
                COALESCE(mp.actual_qty,0) AS good_units,
                COALESCE(pdo.total_wastage + pdo.total_damages,0) AS wastages,
                (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)) AS total_units,
                CASE 
                    WHEN (ROUND((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric,2) - ROUND(COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0),2)) > 0
                    THEN ROUND(
                        ((1 * (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)))::numeric /
                        ((ROUND((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric,2) - ROUND(COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0),2)) * 60) * 100)::numeric,2
                    )
                    ELSE 0
                END AS performance_percent,
                CASE 
                    WHEN (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)) > 0
                    THEN ROUND((COALESCE(mp.actual_qty,0)::numeric / (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)) * 100)::numeric,2)
                    ELSE 0
                END AS quality_percent,
                ROUND(
                    (
                        (
                            CASE 
                                WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0 
                                THEN (( (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0) ) 
                                / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100)
                                ELSE 0
                            END
                        )
                        *
                        (
                            CASE 
                                WHEN ((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0)) > 0
                                THEN ((1 * (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)))::numeric / 
                                      (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0)) * 60) * 100)
                                ELSE 0
                            END
                        )
                        *
                        (
                            CASE 
                                WHEN (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)) > 0
                                THEN (COALESCE(mp.actual_qty,0)::numeric / (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)) * 100)
                                ELSE 0
                            END
                        )
                    )::numeric / 10000, 2
                ) AS oee_percent,
                CASE
                    WHEN ROUND(
                        (
                            (
                                CASE 
                                    WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0 
                                    THEN (( (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0) ) 
                                    / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100)
                                    ELSE 0
                                END
                            )
                            *
                            (
                                CASE 
                                    WHEN ((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0)) > 0
                                    THEN ((1 * (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)))::numeric / 
                                          (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0)) * 60) * 100)
                                    ELSE 0
                                END
                            )
                            *
                            (
                                CASE 
                                    WHEN (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)) > 0
                                    THEN (COALESCE(mp.actual_qty,0)::numeric / (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)) * 100)
                                    ELSE 0
                                END
                            )
                        )::numeric / 10000, 2
                    ) >= 85 THEN '🟢 Healthy'
                    WHEN ROUND(
                        (
                            (
                                CASE 
                                    WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0 
                                    THEN (( (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0) ) 
                                    / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100)
                                    ELSE 0
                                END
                            )
                            *
                            (
                                CASE 
                                    WHEN ((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0)) > 0
                                    THEN ((1 * (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)))::numeric / 
                                          (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric,0)) * 60) * 100)
                                    ELSE 0
                                END
                            )
                            *
                            (
                                CASE 
                                    WHEN (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)) > 0
                                    THEN (COALESCE(mp.actual_qty,0)::numeric / (COALESCE(mp.actual_qty,0) + COALESCE(pdo.total_wastage + pdo.total_damages,0)) * 100)
                                    ELSE 0
                                END
                            )
                        )::numeric / 10000, 2
                    ) BETWEEN 65 AND 84 THEN '🟠 At Risk'
                    ELSE '🔴 Critical'
                END AS quick_view,
                mp.product_id
            FROM mrp_planning mp
            JOIN production_daily_plan_process_stages pdpps ON pdpps.daily_production_plan_id = mp.id
            JOIN production_daily_operation pdo ON pdo.production_plan_id = mp.id
            JOIN mrp_workcenter mw ON mw.production_stage_id = pdpps.production_stage_id
            JOIN used_location ul ON ul.work_center_id = mw.id
            JOIN machine_master mm ON mm.location_id = ul.id
            LEFT JOIN maintenance_request mr ON mr.machine_id = mm.id 
                AND mr.maintenance_request_type = 'machine' 
                AND mr.maintenance_type = 'corrective' 
                AND DATE(mr.request_date_time) = mp.planning_date;
        """)
