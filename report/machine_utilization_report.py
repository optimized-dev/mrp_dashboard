from odoo import models, fields, tools

class MachineUtilizationReport(models.Model):
    _name = 'machine.utilization.report'
    _description = 'Machine Utilization Report'
    _auto = False
    _order = 'machine_id'

    machine_id = fields.Many2one('machine.master', string='Machine')
    machine_name = fields.Char(string='Machine Name')
    shift_start = fields.Datetime(string='Shift Start')
    shift_end = fields.Datetime(string='Shift End')
    planning_date = fields.Date(string='Date')
    production_scheduled_min = fields.Float(string='Scheduled Time (min)')
    downtime_min = fields.Float(string='Downtime (min)')
    downtime_percent = fields.Float(string='Downtime%')
    uptime_min = fields.Float(string='Uptime (min)')
    good_units = fields.Float(string='Good Units')
    wastage_units = fields.Float(string='Wastage Units')
    total_units = fields.Float(string='Total Units')
    availability_percent = fields.Float(string='Availability')
    performance_percent = fields.Float(string='Performance')
    quality_percent = fields.Float(string='Quality')
    oee_percent = fields.Float(string='OEE')
    oee_moving_avg = fields.Float(string='OEE Moving Avg')
    mtbf_min = fields.Float(string='MTBF (min)')
    mttr_min = fields.Float(string='MTTR (min)')
    quick_view = fields.Char(string='Quick View')
    product_id = fields.Many2one('product.template', string='Product')

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH base AS (
                    SELECT
                        row_number() OVER() AS id,
                        mm.id AS machine_id,
                        mm.name AS machine_name,
                        mp.production_start AS shift_start,
                        mp.production_end AS shift_end,
                        mp.planning_date,
                        ROUND((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric, 2) AS production_scheduled_min,
                        ROUND(COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0), 2) AS downtime_min,
                        ROUND(((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)), 2) AS uptime_min,
                        COALESCE(mp.actual_qty, 0) AS good_units,
                        COALESCE(pdo.total_wastage + pdo.total_damages, 0) AS wastage_units,
                        (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)) AS total_units,
                        CASE 
                            WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0
                            THEN ROUND((((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100), 2)
                            ELSE 0
                        END AS availability_percent,
                        CASE 
                            WHEN ((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60 > 0
                            THEN ROUND(((1 * (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)))::numeric / (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60) * 100), 2)
                            ELSE 0
                        END AS performance_percent,
                        CASE
                            WHEN (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)) > 0
                            THEN ROUND((COALESCE(mp.actual_qty, 0)::numeric / (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0))::numeric * 100), 2)
                            ELSE 0
                        END AS quality_percent,
                        ROUND(
                            CASE
                                WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0
                                THEN (COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)
                                      / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100)
                                ELSE 0
                            END, 2
                        ) AS downtime_percent,
                        ROUND(
                            (
                                (CASE 
                                    WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0 
                                    THEN (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100)
                                    ELSE 0
                                END)
                                *
                                (CASE 
                                    WHEN ((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60 > 0
                                    THEN ((1 * (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)))::numeric / (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60) * 100)
                                    ELSE 0
                                END)
                                *
                                (CASE
                                    WHEN (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)) > 0
                                    THEN (COALESCE(mp.actual_qty, 0)::numeric / (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0))::numeric * 100)
                                    ELSE 0
                                END)
                            )::numeric / 10000, 2
                        ) AS oee_percent,
                        -- OEE moving average for last 3 periods
                        ROUND(
                            AVG(ROUND(
                                (
                                    (CASE 
                                        WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0
                                        THEN (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100)
                                        ELSE 0
                                    END)
                                    *
                                    (CASE 
                                        WHEN ((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60 > 0
                                        THEN ((1 * (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)))::numeric / (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60) * 100)
                                        ELSE 0
                                    END)
                                    *
                                    (CASE
                                        WHEN (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)) > 0
                                        THEN (COALESCE(mp.actual_qty, 0)::numeric / (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0))::numeric * 100)
                                        ELSE 0
                                    END)
                                )::numeric / 10000, 2
                            ) ) OVER (PARTITION BY mm.id ORDER BY mp.planning_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2
                        ) AS oee_moving_avg,
                        CASE
                            WHEN COUNT(mr.id) OVER(PARTITION BY mm.id) > 0
                            THEN ROUND(
                                (
                                    ((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric
                                    - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0))
                                    / (COUNT(mr.id) OVER(PARTITION BY mm.id))::numeric
                                ), 2
                            )
                            ELSE NULL
                        END AS mtbf_min,
                        CASE
                            WHEN COUNT(mr.id) OVER(PARTITION BY mm.id) > 0
                            THEN ROUND(
                                SUM(COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) 
                                OVER(PARTITION BY mm.id) 
                                / COUNT(mr.id) OVER(PARTITION BY mm.id), 2
                            )
                            ELSE NULL
                        END AS mttr_min,
                        CASE
                            WHEN ROUND(
                                (
                                    (CASE 
                                        WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0
                                        THEN (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100)
                                        ELSE 0
                                    END)
                                    *
                                    (CASE
                                        WHEN ((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60 > 0
                                        THEN ((1 * (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)))::numeric / (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60) * 100)
                                        ELSE 0
                                    END)
                                    *
                                    (CASE
                                        WHEN (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)) > 0
                                        THEN (COALESCE(mp.actual_qty, 0)::numeric / (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0))::numeric * 100)
                                        ELSE 0
                                    END)
                                )::numeric / 10000, 2
                            ) >= 85 THEN '🟢 Healthy'
                            WHEN ROUND(
                                (
                                    (CASE 
                                        WHEN (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60) > 0
                                        THEN (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) / (EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric * 100)
                                        ELSE 0
                                    END)
                                    *
                                    (CASE
                                        WHEN ((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60 > 0
                                        THEN ((1 * (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)))::numeric / (((EXTRACT(EPOCH FROM (mp.production_end - mp.production_start)) / 60)::numeric - COALESCE((EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 60)::numeric, 0)) * 60) * 100)
                                        ELSE 0
                                    END)
                                    *
                                    (CASE
                                        WHEN (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0)) > 0
                                        THEN (COALESCE(mp.actual_qty, 0)::numeric / (COALESCE(mp.actual_qty, 0) + COALESCE(pdo.total_wastage + pdo.total_damages, 0))::numeric * 100)
                                        ELSE 0
                                    END)
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
                    LEFT JOIN maintenance_request mr 
                        ON mr.machine_id = mm.id 
                        AND mr.maintenance_request_type = 'machine'
                        AND mr.maintenance_type = 'corrective'
                        AND DATE(mr.request_date_time) = mp.planning_date
                )
                SELECT * FROM base
            )
        """ % self._table)
