import frappe
from frappe.model.document import Document


class Campaign(Document):
    def validate(self):
        self._validate_email_settings()
        self._validate_schedule()
        self._number_schedule_steps()

    def _validate_email_settings(self):
        if self.campaign_type != "Email":
            return
        has_template = self.email_template or len(self.schedule) > 0
        if not has_template:
            frappe.throw("Please add an Email Template or an Email Sequence")

    def _validate_schedule(self):
        if not self.send_immediately and not self.scheduled_date:
            frappe.throw("Scheduled Date is required when not sending immediately")

    def _number_schedule_steps(self):
        for index, step in enumerate(self.schedule):
            step.step_number = index + 1

    def before_submit(self):
        self.status = "Running"
