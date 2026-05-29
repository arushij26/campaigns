import frappe
from frappe.model.document import Document


class CampaignAudience(Document):
    def before_save(self):
        self._update_total_contacts()

    def _update_total_contacts(self):
        self.total_contacts = len([
            member for member in self.members
            if member.status == "Subscribed"
        ])
