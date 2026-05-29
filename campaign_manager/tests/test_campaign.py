import frappe
import unittest


class TestCampaign(unittest.TestCase):
    def setUp(self):
        self._create_test_template()
        self._create_test_audience()

    def _create_test_template(self):
        if frappe.db.exists("Campaign Template", "Test Template"):
            return
        frappe.get_doc({
            "doctype": "Campaign Template",
            "template_name": "Test Template",
            "subject": "Test Subject",
            "body_html": "<p>Hello {{first_name}}</p>",
        }).insert(ignore_permissions=True)

    def _create_test_audience(self):
        if frappe.db.exists("Campaign Audience", "Test Audience"):
            return
        frappe.get_doc({
            "doctype": "Campaign Audience",
            "audience_name": "Test Audience",
            "source": "Manual",
            "members": [
                {"email": "test@example.com", "full_name": "Test User"}
            ]
        }).insert(ignore_permissions=True)

    def test_campaign_creation(self):
        campaign = frappe.get_doc({
            "doctype": "Campaign",
            "campaign_name": "Test Campaign",
            "campaign_type": "Email",
            "email_template": "Test Template",
            "audience": "Test Audience",
        }).insert(ignore_permissions=True)
        self.assertEqual(campaign.status, "Draft")
        campaign.delete()

    def test_campaign_requires_template(self):
        campaign = frappe.get_doc({
            "doctype": "Campaign",
            "campaign_name": "Test Campaign No Template",
            "campaign_type": "Email",
        })
        self.assertRaises(frappe.ValidationError, campaign.insert)

    def test_audience_total_contacts_count(self):
        audience = frappe.get_doc("Campaign Audience", "Test Audience")
        self.assertEqual(audience.total_contacts, 1)

    def test_audience_excludes_unsubscribed(self):
        audience = frappe.get_doc({
            "doctype": "Campaign Audience",
            "audience_name": "Test Audience Unsubscribed",
            "source": "Manual",
            "members": [
                {"email": "active@example.com", "full_name": "Active User", "status": "Subscribed"},
                {"email": "inactive@example.com", "full_name": "Inactive User", "status": "Unsubscribed"},
            ]
        }).insert(ignore_permissions=True)
        self.assertEqual(audience.total_contacts, 1)
        frappe.delete_doc("Campaign Audience", "Test Audience Unsubscribed", ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()
