frappe.pages["leave-tool"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Leave Marking Tool",
		single_column: true,
	});

	const employee_field = page.add_field({
		fieldtype: "Link",
		fieldname: "employee",
		options: "Employee",
		label: "Employee",
		reqd: 1,
		change() { clear_table(); },
	});

	const from_date_field = page.add_field({
		fieldtype: "Date",
		fieldname: "from_date",
		label: "From Date",
		reqd: 1,
		change() { clear_table(); },
	});

	const to_date_field = page.add_field({
		fieldtype: "Date",
		fieldname: "to_date",
		label: "To Date",
		reqd: 1,
		change() { clear_table(); },
	});

	const leave_type_field = page.add_field({
		fieldtype: "Link",
		fieldname: "leave_type",
		options: "Leave Type",
		label: "Leave Type",
		reqd: 1,
	});

	page.set_primary_action("Fetch Absent Records", fetch_records, "search");
	page.add_action_icon("check", apply_leave, "Apply Leave for Selected");

	$(`
		<div class="leave-tool-container" style="padding: 20px;">
			<div id="lt-table-wrapper" style="display:none;">
				<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
					<h6 style="margin:0;" id="lt-record-count"></h6>
					<div>
						<button class="btn btn-xs btn-default" id="lt-select-all">Select All</button>
						<button class="btn btn-xs btn-default" id="lt-deselect-all" style="margin-left:5px;">Deselect All</button>
					</div>
				</div>
				<table class="table table-bordered table-hover" id="lt-table">
					<thead>
						<tr style="background:#f5f5f5;">
							<th style="width:40px;"><input type="checkbox" id="lt-check-all"></th>
							<th>Date</th>
							<th>Employee Name</th>
							<th>Current Status</th>
							<th>Action</th>
						</tr>
					</thead>
					<tbody id="lt-tbody"></tbody>
				</table>
				<div style="margin-top:15px; text-align:right;">
					<button class="btn btn-primary" id="lt-apply-btn">
						<i class="fa fa-check"></i> Apply Leave for Selected
					</button>
				</div>
			</div>
			<div id="lt-empty" style="display:none; text-align:center; padding:40px; color:#888;">
				<i class="fa fa-calendar" style="font-size:40px;"></i>
				<p style="margin-top:10px;">No absent records found for this date range.</p>
			</div>
			<div id="lt-result-log" style="margin-top:20px;"></div>
		</div>
	`).appendTo($(wrapper).find(".page-content"));

	function clear_table() {
		$("#lt-table-wrapper").hide();
		$("#lt-empty").hide();
		$("#lt-tbody").empty();
		$("#lt-result-log").empty();
	}

	function fetch_records() {
		const employee = employee_field.get_value();
		const from_date = from_date_field.get_value();
		const to_date = to_date_field.get_value();

		if (!employee || !from_date || !to_date) {
			frappe.msgprint("Please fill Employee, From Date and To Date.");
			return;
		}

		if (from_date > to_date) {
			frappe.msgprint("From Date cannot be greater than To Date.");
			return;
		}

		frappe.call({
			method: "attendance_correction.attendance_correction.page.leave_tool.leave_tool.get_absent_records",
			args: { employee, from_date, to_date },
			freeze: true,
			freeze_message: "Fetching absent records...",
			callback(r) {
				clear_table();
				const records = r.message || [];

				if (!records.length) {
					$("#lt-empty").show();
					return;
				}

				$("#lt-record-count").text(`Found ${records.length} absent record(s)`);

				records.forEach((row) => {
					const formatted_date = frappe.datetime.str_to_user(row.attendance_date);
					$("#lt-tbody").append(`
						<tr data-date="${row.attendance_date}" data-name="${row.name}">
							<td><input type="checkbox" class="lt-row-check" checked></td>
							<td><strong>${formatted_date}</strong></td>
							<td>${row.employee_name || "-"}</td>
							<td><span class="badge badge-danger">Absent</span></td>
							<td><span class="text-muted" style="font-size:11px;">Will be changed to <strong>On Leave</strong></span></td>
						</tr>
					`);
				});

				$("#lt-table-wrapper").show();
			},
		});
	}

	$(document).on("click", "#lt-select-all", () => {
		$(".lt-row-check").prop("checked", true);
	});

	$(document).on("click", "#lt-deselect-all", () => {
		$(".lt-row-check").prop("checked", false);
	});

	$(document).on("change", "#lt-check-all", function () {
		$(".lt-row-check").prop("checked", $(this).prop("checked"));
	});

	function apply_leave() {
		const employee = employee_field.get_value();
		const leave_type = leave_type_field.get_value();

		if (!employee || !leave_type) {
			frappe.msgprint("Please select Employee and Leave Type.");
			return;
		}

		const selected_dates = [];
		$(".lt-row-check:checked").each(function () {
			selected_dates.push($(this).closest("tr").data("date"));
		});

		if (!selected_dates.length) {
			frappe.msgprint("Please select at least one record.");
			return;
		}

		frappe.confirm(
			`Apply leave for <strong>${selected_dates.length}</strong> day(s)? This will update Attendance and create Leave Applications.`,
			() => {
				frappe.call({
					method: "attendance_correction.attendance_correction.page.leave_tool.leave_tool.apply_leave",
					args: {
						employee,
						leave_type,
						dates: JSON.stringify(selected_dates),
					},
					freeze: true,
					freeze_message: "Applying leave, please wait...",
					callback(r) {
						const results = r.message || [];
						render_results(results);
						fetch_records();
					},
				});
			}
		);
	}

	$(document).on("click", "#lt-apply-btn", apply_leave);

	function render_results(results) {
		let html = `<h6>Result Summary</h6>
			<table class="table table-bordered" style="font-size:13px;">
				<thead>
					<tr><th>Date</th><th>Status</th><th>Reason</th></tr>
				</thead>
				<tbody>`;

		results.forEach((r) => {
			const badge =
				r.status === "success"
					? `<span class="badge badge-success">Success</span>`
					: r.status === "skipped"
					? `<span class="badge badge-warning">Skipped</span>`
					: `<span class="badge badge-danger">Error</span>`;

			html += `<tr>
				<td>${frappe.datetime.str_to_user(r.date)}</td>
				<td>${badge}</td>
				<td>${r.reason || "-"}</td>
			</tr>`;
		});

		html += `</tbody></table>`;
		$("#lt-result-log").html(html);
	}
};