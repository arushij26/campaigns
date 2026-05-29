import frappe
from frappe.utils import now_datetime
from campaign_manager.services.email_service import EmailService


def send_queued_steps():
    queued_steps = _get_due_steps()
    for step_info in queued_steps:
        _process_step(step_info)


def _get_due_steps():
    return frappe.db.sql("""
        SELECT cs.name, cs.parent, cs.email_template, cs.subject
        FROM `tabCampaign Schedule` cs
        JOIN `tabCampaign` c ON c.name = cs.parent
        WHERE cs.status = 'Queued'
        AND cs.scheduled_at <= %s
        AND c.status = 'Running'
    """, now_datetime(), as_dict=True)


def _process_step(step_info):
    try:
        frappe.enqueue(
            _send_step,
            campaign_name=step_info.parent,
            step_name=step_info.name,
            queue="long"
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Campaign Step Queue Error")


def _send_step(campaign_name, step_name):
    service = EmailService(campaign_name)
    service.send_step(step_name)
