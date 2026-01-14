// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Rista Sales Log", {
	refresh(frm) {
		frm.disable_save();
		frm.disable_form();
		handle_custom_buttons(frm);
	},
});

function handle_custom_buttons(frm) {
	// if (!frm.is_new() && !frm.doc.sales_invoice_reference) {
	if (!frm.is_new()) {
		frm.add_custom_button(__('Sync Sales'), () => {
			frappe.call({
				method: "petpooja_integration.rista_integration.rista_apis.sync_sales_invoice",
				args: {
					invoice_id: frm.doc.invoice_number
				},
				freeze: true,
				freeze_message: __("Syncing from Rista..."),
				callback: function (r) {
					if (!r.exc) {
						frappe.msgprint({
							title: __("Success"),
							indicator: "green",
							message: __("Rista sync completed successfully")
						});
						frm.reload_doc();
					}
				}
			});
		});
	}
}
