import re
import frappe
from frappe.utils import now_datetime, add_to_date


class EmailService:
    def __init__(self, campaign_name):
        self.campaign = frappe.get_doc("Campaign", campaign_name)
        self.sender = self._resolve_sender()

    def _resolve_sender(self):
        if not self.campaign.sender_email:
            return None
        account = frappe.get_doc("Email Account", self.campaign.sender_email)
        name = self.campaign.sender_name or account.email_account_name
        return f"{name} <{account.email_id}>"

    def send(self):
        if self.campaign.schedule:
            self._send_sequence()
        else:
            self._send_single()

    def _send_single(self):
        template = frappe.get_doc("Campaign Template", self.campaign.email_template)
        recipients = self._get_recipients()
        for recipient in recipients:
            self._deliver(recipient, template, self.campaign.subject or template.subject)
        self._mark_completed()

    def _send_sequence(self):
        first_step = self.campaign.schedule[0]
        template = frappe.get_doc("Campaign Template", first_step.email_template)
        recipients = self._get_recipients()
        for recipient in recipients:
            self._deliver(recipient, template, first_step.subject or template.subject)
        first_step.status = "Sent"
        first_step.sent_at = now_datetime()
        self.campaign.save(ignore_permissions=True)
        self._queue_remaining_steps()

    def _queue_remaining_steps(self):
        for step in self.campaign.schedule[1:]:
            step.scheduled_at = add_to_date(now_datetime(), days=step.delay_days, hours=step.delay_hours)
            step.status = "Queued"
        self.campaign.save(ignore_permissions=True)

    def send_step(self, step_name):
        step = self._get_step(step_name)
        if not step or step.status != "Queued":
            return
        template = frappe.get_doc("Campaign Template", step.email_template)
        recipients = self._get_recipients()
        for recipient in recipients:
            self._deliver(recipient, template, step.subject or template.subject)
        step.status = "Sent"
        step.sent_at = now_datetime()
        self.campaign.save(ignore_permissions=True)
        self._mark_completed()

    def _get_step(self, step_name):
        for step in self.campaign.schedule:
            if step.name == step_name:
                return step
        return None

    def _get_recipients(self):
        audience = frappe.get_doc("Campaign Audience", self.campaign.audience)
        return [member for member in audience.members if member.status == "Subscribed"]

    def _deliver(self, recipient, template, subject):
        token = frappe.generate_hash(length=20)
        try:
            body = self._render_body(template.body_html, recipient, None, token)
            frappe.sendmail(
                recipients=[recipient.email],
                subject=subject,
                message=body,
                sender=self.sender,
                now=True
            )
            self._log_sent_with_token(recipient, token)
        except Exception as error:
            self._log_failed(recipient, str(error))

    def _render_body(self, html, recipient, log_name, token):
        site_url = frappe.utils.get_url()
        html = html.replace("{{first_name}}", recipient.full_name or "")
        html = html.replace("{{email}}", recipient.email)
        pixel_url = f"{site_url}/api/method/campaign_manager.api.track_open?token={token}"
        tracking_pixel = f'<img src="{pixel_url}" width="1" height="1" style="display:none" />'
        html = html + tracking_pixel
        html = _wrap_links_with_tracking(html, token, site_url)
        return html

    def _log_sent_with_token(self, recipient, token):
        frappe.get_doc({
            "doctype": "Campaign Email Log",
            "campaign": self.campaign.name,
            "recipient_email": recipient.email,
            "full_name": recipient.full_name,
            "status": "Sent",
            "sent_at": now_datetime(),
            "token": token
        }).insert(ignore_permissions=True)

    def _log_failed(self, recipient, error):
        frappe.get_doc({
            "doctype": "Campaign Email Log",
            "campaign": self.campaign.name,
            "recipient_email": recipient.email,
            "full_name": recipient.full_name,
            "status": "Failed",
            "error_message": error
        }).insert(ignore_permissions=True)

    def _mark_completed(self):
        if not self.campaign.schedule or all(s.status == "Sent" for s in self.campaign.schedule):
            self.campaign.status = "Completed"
            self.campaign.save(ignore_permissions=True)


def _wrap_links_with_tracking(html, token, site_url):
    def replace_link(match):
        original_url = match.group(1)
        if "track_click" in original_url or "track_open" in original_url:
            return match.group(0)
        tracked_url = f"{site_url}/api/method/campaign_manager.api.track_click?token={token}&url={original_url}"
        return f'href="{tracked_url}"'
    return re.sub(r'href="([^"]+)"', replace_link, html)
