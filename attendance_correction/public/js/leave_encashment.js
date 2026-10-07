// Leave Balance, Actual Encashable Days and Encashment Days are fetched from the employee's
// Leave Allocation and must not be edited by hand (the server enforces this as well).
frappe.ui.form.on("Leave Encashment", {
	refresh(frm) {
		["leave_balance", "actual_encashable_days", "encashment_days"].forEach((field) =>
			frm.set_df_property(field, "read_only", 1)
		);
		// the name may be corrected by hand; picking another employee re-fetches it
		frm.set_df_property("employee_name", "read_only", frm.doc.docstatus === 0 ? 0 : 1);
	},
});
