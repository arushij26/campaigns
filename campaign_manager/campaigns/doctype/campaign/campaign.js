frappe.ui.form.on('Campaign', {
    refresh(frm) {
        if (frm.doc.status === 'Draft' || frm.doc.status === 'Paused') {
            frm.add_custom_button('Send Campaign', () => {
                frappe.confirm(
                    `Are you sure you want to send "${frm.doc.campaign_name}" to all recipients?`,
                    () => {
                        frappe.call({
                            method: 'campaign_manager.api.send_campaign',
                            args: { campaign_name: frm.doc.name },
                            freeze: true,
                            freeze_message: 'Sending campaign...',
                            callback(response) {
                                frappe.msgprint({
                                    title: 'Campaign Queued',
                                    message: 'Your campaign has been queued for sending.',
                                    indicator: 'green'
                                });
                                frm.reload_doc();
                            }
                        });
                    }
                );
            }, 'Actions');
        }

        if (frm.doc.status === 'Running') {
            frm.add_custom_button('Pause Campaign', () => {
                frappe.call({
                    method: 'campaign_manager.api.pause_campaign',
                    args: { campaign_name: frm.doc.name },
                    callback() {
                        frm.reload_doc();
                    }
                });
            }, 'Actions');
        }

        if (frm.doc.status === 'Completed') {
            frm.add_custom_button('View Analytics', () => {
                frappe.call({
                    method: 'campaign_manager.api.get_campaign_analytics',
                    args: { campaign_name: frm.doc.name },
                    callback(response) {
                        const data = response.message;
                        frappe.msgprint({
                            title: 'Campaign Analytics',
                            message: `
                                <table class="table table-bordered">
                                    <tr><td>Total Sent</td><td><b>${data.total_sent}</b></td></tr>
                                    <tr><td>Total Opened</td><td><b>${data.total_opened}</b></td></tr>
                                    <tr><td>Total Clicked</td><td><b>${data.total_clicked}</b></td></tr>
                                    <tr><td>Open Rate</td><td><b>${data.open_rate}%</b></td></tr>
                                    <tr><td>Click Rate</td><td><b>${data.click_rate}%</b></td></tr>
                                    <tr><td>Delivery Rate</td><td><b>${data.delivery_rate}%</b></td></tr>
                                </table>
                            `,
                            indicator: 'blue'
                        });
                    }
                });
            }, 'Actions');
        }
    }
});
