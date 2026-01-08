// Copyright (c) 2026, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Petpooja Settings", {
    enable_petpooja_apis(frm) {
        if (!frm.doc.enable_petpooja_apis) {
            frm.set_value("access_token", "");
        }
    },
});
