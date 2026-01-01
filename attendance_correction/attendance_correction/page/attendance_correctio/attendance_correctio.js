frappe.pages['attendance_correctio'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Attendance Correction',
        single_column: true
    });

    // Inject HTML Template
page.body.html(`
    <div class="form-group">
        <label>Employee</label>
        <input type="text" class="form-control" id="employee">
    </div>

    <div class="form-group">
        <label>Department</label>
        <input type="text" class="form-control" id="department">
    </div>

    <div class="form-group">
        <label>Shift</label>
        <input type="text" class="form-control" id="shift">
    </div>

    <div class="form-group">
        <label>From Date</label>
        <input type="date" class="form-control" id="from_date">
    </div>

    <div class="form-group">
        <label>To Date</label>
        <input type="date" class="form-control" id="to_date">
    </div>

    <button class="btn btn-primary" id="load-data">Load Data</button>

    <hr>

    <div id="attendance-table"></div>

    <button class="btn btn-success" id="save-changes">Save Changes</button>
`);
// 🔹 Department Link Field (Autocomplete)
let department_field = frappe.ui.form.make_control({
    parent: page.body.find(".form-group:contains('Department')"),
    df: {
        fieldtype: "Link",
        options: "Department",
        label: "Department",
        fieldname: "department",
        placeholder: "Select Department"
    },
    render_input: true
});


    let tableData = [];

    // 🔹 Helper: check overtime permission + popup
    function checkOvertimeAllowed(row, inputEl) {
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { name: row.employee },
                fieldname: "custom_allow_overtime"
            },
            callback: function(r) {
                if (r.message && r.message.custom_allow_overtime == 0) {
                    frappe.msgprint({
                        title: __("Overtime Not Allowed"),
                        message: __("Sorry, overtime isn’t allowed for this employee."),
                        indicator: "red"
                    });

                    // revert overtime value
                    inputEl.val(row.custom_overtime || 0);
                }
            }
        });
    }

    // Load Data Button
    $("#load-data").click(() => {
        const emp = $("#employee").val();
        const department = department_field.get_value();
        const shift = $("#shift").val();
        const from_date = $("#from_date").val();
        const to_date = $("#to_date").val();

        frappe.call({
            method: "attendance_correction.attendance_correction.page.attendance_correctio.attendance_correctio.get_attendance_records",
            args: { 
                employee: emp, 
                department: department,
                shift: shift, 
                from_date: from_date, 
                to_date: to_date 
            },
            callback: function(r) {
                tableData = r.message || [];
                if (tableData.length === 0) {
                    $("#attendance-table").html("<p>No records found.</p>");
                } else {
                    renderTable(tableData);
                }
            }
        });
    });

    function renderTable(data) {
        let total_working = 0;
        let total_overtime = 0;
        let total_present_days = 0;


        let html = `
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Employee</th>
                        <th>Name</th>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Working Hours</th>
                        <th>Overtime Hours</th>
                        <th>In Time</th>
                        <th>Out Time</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.forEach((row, i) => {
            total_working += parseFloat(row.working_hours) || 0;
            total_overtime += parseFloat(row.custom_overtime) || 0;

            if (row.status === "Present"){
                total_present_days += 1 // Count Present 
            }

            html += `
                <tr>
                    <td>${row.employee}</td>
                    <td>${row.employee_name}</td>
                    <td>${row.attendance_date}</td>

                  <td>
    <select 
        data-i="${i}" 
        data-field="status" 
        class="form-control status-select ${row.status === 'Present' ? 'status-present' : row.status === 'Absent' ? 'status-absent' : 'status-half'}">
        
        <option value="Present" ${row.status=="Present"?"selected":""}>Present</option>
        <option value="Absent" ${row.status=="Absent"?"selected":""}>Absent</option>
        <option value="Half Day" ${row.status=="Half Day"?"selected":""}>Half Day</option>
    </select>
</td>


                    <td>
                        <input type="number" data-i="${i}" data-field="working_hours"
                            value="${row.working_hours}" class="form-control">
                    </td>

                    <td>
                        <input type="number" data-i="${i}" data-field="custom_overtime"
                            value="${row.custom_overtime || 0}" class="form-control">
                    </td>

                    <td>
                        <input type="text" data-i="${i}" data-field="in_time"
                            value="${row.in_time || ''}" class="form-control">
                    </td>

                    <td>
                        <input type="text" data-i="${i}" data-field="out_time"
                            value="${row.out_time || ''}" class="form-control">
                    </td>
                </tr>
            `;
        });

        html += `
            </tbody>
            <tfoot>
            <tr>
                 <th colspan="2" style="text-align:right">Present Days:</th>
                 <th>${total_present_days}</th>
         
                 <th style="text-align:right">Total Working Hours:</th>
                 <th>${total_working.toFixed(2)}</th>
         
                 <th style="text-align:right">Overtime Hours:</th>
                 <th>${total_overtime.toFixed(2)}</th>
             </tr>
            </tfoot>
        </table>
        `;

        $("#attendance-table").html(html);

        // Update tableData on change
// Update tableData on change
$("input, select").on("change", function() {
    let i = $(this).data("i");
    let field = $(this).data("field");
    let inputEl = $(this);

    // 🚨 overtime popup check
    if (field === "custom_overtime") {
        checkOvertimeAllowed(tableData[i], inputEl);
    }

    tableData[i][field] = inputEl.val();

    // 🔢 recalculate totals
    total_working = 0;
    total_overtime = 0;
    tableData.forEach(row => {
        total_working += parseFloat(row.working_hours) || 0;
        total_overtime += parseFloat(row.custom_overtime) || 0;
    });

    $("tfoot th:eq(0)").next().text(total_working.toFixed(2));
    $("tfoot th:eq(1)").text(total_overtime.toFixed(2));

    // ✅ STATUS COLOR UPDATE (ADDED)
    if (field === "status") {
        inputEl
            .removeClass("status-present status-absent status-half")
            .addClass(
                inputEl.val() === "Present"
                    ? "status-present"
                    : inputEl.val() === "Absent"
                    ? "status-absent"
                    : "status-half"
            );
    }
});

    }

    // Save Changes Button
    $("#save-changes").click(() => {
        if (tableData.length === 0) {
            frappe.msgprint("No data to update.");
            return;
        }
        let overtimeWarningShown = false;

tableData.forEach(row => {
    if (
        !overtimeWarningShown &&
        row.custom_overtime != row._original_overtime
    ) {
        // check from backend if overtime allowed
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { name: row.employee },
                fieldname: "custom_allow_overtime"
            },
            async: false,
            callback: function(r) {
                if (r.message && r.message.custom_allow_overtime == 0) {
                    frappe.msgprint({
                        title: __("Overtime Not Allowed"),
                        message: __(
                            "Sorry, overtime isn’t allowed for employee {0}. Overtime changes will be ignored.",
                            [row.employee]
                        ),
                        indicator: "red"
                    });
                    overtimeWarningShown = true;
                }
            }
        });
    }
});


        frappe.call({
            method: "attendance_correction.attendance_correction.page.attendance_correctio.attendance_correctio.update_attendance",
            args: { data: JSON.stringify(tableData) },
            callback: function(r) {
                frappe.msgprint(r.message || "Attendance Updated Successfully");
                $("#load-data").click();
            }
        });
    });
};


$(`<style>
    .status-present {
        background-color: #d4edda !important;
        color: #155724 !important;
        font-weight: bold;
    }

    .status-absent {
        background-color: #f8d7da !important;
        color: #ea0920ff !important;
        font-weight: bold;
    }

    .status-half {
        background-color: #fff3cd !important;
        color: #856404 !important;
        font-weight: bold;
    }
</style>`).appendTo("head");
