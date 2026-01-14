// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Rista Settings", {
	refresh(frm) {
		handle_custom_button(frm);
	},
});

function handle_custom_button(frm) {
	add_sync_branch_btn(frm);
	add_sync_sales_btn(frm);
}

function add_sync_branch_btn(frm) {
	frm.add_custom_button(__('Branches'), () => {
		frappe.call({
			method: "petpooja_integration.rista_integration.rista_apis.sync_branches",
			freeze: true,
			freeze_message: __("Syncing from Rista..."),
			callback: function (r) {
				if (r && r.message) {
					frappe.msgprint({
						title: __("Success"),
						indicator: "green",
						message: __(r.message)
					});
				}
			}
		});
	}, 'Sync Data');
}

function add_sync_sales_btn(frm) {
	frm.add_custom_button(__('Sales'), () => {
		frappe.call({
			method: "petpooja_integration.rista_integration.rista_apis.sync_sales_data",
			freeze: true,
			freeze_message: __("Syncing from Rista..."),
			callback: function (r) {
				if (!r.exc) {
					frappe.msgprint({
						title: __("Success"),
						indicator: "green",
						message: __("Rista sync completed successfully")
					});
				}
			}
		});
	}, 'Sync Data');
}