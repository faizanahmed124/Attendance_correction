frappe.pages['correction-audit-too'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Correction audit tool',
		single_column: true
	});

	const today = frappe.datetime.get_today();
	const fields = {};
	const add = (df) => {
		fields[df.fieldname] = page.add_field(df);
	};

	add({ fieldtype: 'Link', fieldname: 'user', label: 'User', options: 'User' });
	add({ fieldtype: 'Date', fieldname: 'from_date', label: 'From Date', default: frappe.datetime.add_days(today, -7), reqd: 1 });
	add({ fieldtype: 'Date', fieldname: 'to_date', label: 'To Date', default: today, reqd: 1 });

	const $body = $('<div class="mt-3"></div>').appendTo(page.main);
	let rows = [];

	function render() {
		if (!rows.length) {
			$body.html('<div class="text-muted text-center p-5">No corrections found.</div>');
			return;
		}
		const e = frappe.utils.escape_html;
		const tr = rows.map((r) => `<tr>
			<td>${e(r.changed_on)}</td>
			<td>${e(r.user_name)}<br><small class="text-muted">${e(r.user)}</small></td>
			<td><a href="/app/attendance/${encodeURIComponent(r.attendance)}">${e(r.employee)} - ${e(r.employee_name)}</a></td>
			<td>${e(r.department)}</td>
			<td>${e(r.attendance_date)}</td>
			<td>${e(r.field)}</td>
			<td>${e(r.from_value)}</td>
			<td>${e(r.to_value)}</td>
		</tr>`).join('');
		$body.html(`
			<div class="text-muted mb-2">${rows.length} correction(s)</div>
			<div class="table-responsive"><table class="table table-bordered table-sm">
				<thead><tr><th>Changed On</th><th>Changed By</th><th>Employee</th><th>Department</th>
				<th>Attendance Date</th><th>Field</th><th>From</th><th>To</th></tr></thead>
				<tbody>${tr}</tbody>
			</table></div>`);
	}

	function load() {
		const v = {};
		Object.keys(fields).forEach((k) => (v[k] = fields[k].get_value()));
		if (!v.from_date || !v.to_date) {
			frappe.show_alert({ message: 'Select From Date and To Date', indicator: 'orange' });
			return;
		}
		$body.html('<div class="text-muted text-center p-5">Loading…</div>');
		frappe.call({
			method: 'attendance_correction.attendance_correction.page.correction_audit_too.correction_audit_tool.get_audit',
			args: v,
			callback: (r) => {
				rows = r.message || [];
				render();
			},
			error: () => $body.html('<div class="text-danger text-center p-5">Failed to load.</div>')
		});
	}

	page.set_primary_action('Search', load);
	render();
};
