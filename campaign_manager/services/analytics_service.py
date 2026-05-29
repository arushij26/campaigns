import frappe


class AnalyticsService:
    def __init__(self, campaign_name):
        self.campaign_name = campaign_name

    def calculate(self):
        counts = self._get_status_counts()
        rates = self._calculate_rates(counts)
        self._update_campaign(counts, rates)

    def _get_status_counts(self):
        logs = frappe.get_all(
            "Campaign Email Log",
            filters={"campaign": self.campaign_name},
            fields=["status"]
        )
        return {
            "total": len(logs),
            "sent": len([log for log in logs if log.status in ["Sent", "Opened", "Clicked"]]),
            "opened": len([log for log in logs if log.status in ["Opened", "Clicked"]]),
            "clicked": len([log for log in logs if log.status == "Clicked"]),
            "failed": len([log for log in logs if log.status == "Failed"]),
        }

    def _calculate_rates(self, counts):
        sent = counts["sent"] or 1
        return {
            "open_rate": round(counts["opened"] / sent * 100, 1),
            "click_rate": round(counts["clicked"] / sent * 100, 1),
            "delivery_rate": round(counts["sent"] / (counts["total"] or 1) * 100, 1),
        }

    def _update_campaign(self, counts, rates):
        frappe.db.set_value("Campaign", self.campaign_name, {
            "total_recipients": counts["total"],
            "total_sent": counts["sent"],
            "total_opened": counts["opened"],
            "total_clicked": counts["clicked"],
            "total_failed": counts["failed"],
            "open_rate": rates["open_rate"],
            "click_rate": rates["click_rate"],
            "delivery_rate": rates["delivery_rate"],
        })
        frappe.db.commit()
