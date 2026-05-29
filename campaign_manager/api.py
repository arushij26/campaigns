import frappe
from campaign_manager.services.email_service import EmailService
from campaign_manager.services.analytics_service import AnalyticsService


@frappe.whitelist()
def send_campaign(campaign_name):
    campaign = frappe.get_doc("Campaign", campaign_name)
    _validate_can_send(campaign)
    campaign.status = "Running"
    campaign.save()
    frappe.enqueue(
        _send_campaign_background,
        campaign_name=campaign_name,
        queue="long"
    )
    return {"message": "Campaign queued for sending"}


def _validate_can_send(campaign):
    if campaign.status not in ["Draft", "Paused"]:
        frappe.throw(f"Cannot send campaign in {campaign.status} status")
    if not campaign.audience:
        frappe.throw("Please select an Audience before sending")
    if not campaign.email_template:
        frappe.throw("Please select an Email Template before sending")


def _send_campaign_background(campaign_name):
    service = EmailService(campaign_name)
    service.send()
    analytics = AnalyticsService(campaign_name)
    analytics.calculate()


@frappe.whitelist()
def get_campaign_analytics(campaign_name):
    analytics = AnalyticsService(campaign_name)
    analytics.calculate()
    campaign = frappe.get_doc("Campaign", campaign_name)
    return {
        "total_recipients": campaign.total_recipients,
        "total_sent": campaign.total_sent,
        "total_opened": campaign.total_opened,
        "total_clicked": campaign.total_clicked,
        "total_failed": campaign.total_failed,
        "open_rate": campaign.open_rate,
        "click_rate": campaign.click_rate,
        "delivery_rate": campaign.delivery_rate,
    }


@frappe.whitelist()
def get_campaigns():
    return frappe.get_all(
        "Campaign",
        fields=[
            "name", "campaign_name", "status",
            "campaign_type", "total_sent",
            "open_rate", "creation", "modified"
        ],
        order_by="modified desc"
    )


@frappe.whitelist()
def pause_campaign(campaign_name):
    campaign = frappe.get_doc("Campaign", campaign_name)
    if campaign.status != "Running":
        frappe.throw(f"Cannot pause a campaign with status {campaign.status}")
    campaign.status = "Paused"
    campaign.save()
    return {"message": "Campaign paused"}


@frappe.whitelist(allow_guest=True)
def track_open(token):
    log = frappe.db.get_value(
        "Campaign Email Log",
        {"token": token},
        ["name", "campaign", "status"],
        as_dict=True
    )
    if log and log.status == "Sent":
        _mark_opened(log)
    return _tracking_pixel()


def _mark_opened(log):
    frappe.db.set_value(
        "Campaign Email Log",
        log.name,
        {
            "status": "Opened",
            "opened_at": frappe.utils.now_datetime()
        }
    )
    _update_campaign_analytics(log.campaign)
    frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def track_click(token, url):
    log = frappe.db.get_value(
        "Campaign Email Log",
        {"token": token},
        ["name", "campaign", "status"],
        as_dict=True
    )
    if log:
        _mark_clicked(log)
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = url


def _mark_clicked(log):
    frappe.db.set_value(
        "Campaign Email Log",
        log.name,
        {
            "status": "Clicked",
            "clicked_at": frappe.utils.now_datetime()
        }
    )
    _update_campaign_analytics(log.campaign)
    frappe.db.commit()


def _tracking_pixel():
    pixel = b'GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;'
    frappe.local.response["type"] = "binary"
    frappe.local.response["filename"] = "t.gif"
    frappe.local.response["filecontent"] = pixel
    frappe.local.response["content_type"] = "image/gif"
    return pixel


def _update_campaign_analytics(campaign_name):
    AnalyticsService(campaign_name).calculate()
