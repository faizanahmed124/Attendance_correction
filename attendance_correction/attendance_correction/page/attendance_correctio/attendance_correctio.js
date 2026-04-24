frappe.pages['attendance_correctio'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Attendance Correction Tool',
        single_column: true
    });

    page.body.html(`
        <div class="form-inline" style="gap:10px; display:flex; flex-wrap:wrap; align-items:center; margin-bottom:10px;">
            <div class="form-group">
                <label style="margin-right:5px;">Employee</label>
                <input type="text" class="form-control" id="employee" style="width:150px;">
            </div>

            <div class="form-group" id="department-wrapper">
                <!-- Department Link field will be injected here -->
            </div>

            <div class="form-group">
                <label style="margin-right:5px;">From Date</label>
                <input type="date" class="form-control" id="from_date" style="width:140px;">
            </div>

            <div class="form-group">
                <label style="margin-right:5px;">To Date</label>
                <input type="date" class="form-control" id="to_date" style="width:140px;">
            </div>

            <button class="btn btn-primary" id="load-data" style="margin-left:5px;">Load Data</button>
        </div>

        <hr>

        <div id="attendance-table"></div>

        <button class="btn btn-success" id="save-changes">Save Changes</button>
    `);

    // Department Link Field
    let department_field = frappe.ui.form.make_control({
        parent: page.body.find("#department-wrapper"),
        df: {
            fieldtype: "Link",
            options: "Department",
            label: "Department :",
            fieldname: "department",
            placeholder: "Select Department"
        },
        render_input: true
    });

    let tableData = [];
    let originalData = {};
    let dirtyRows = new Set();

    function evaluateDirty(rowName, rowIndex) {
        const orig = originalData[rowName];
        const current = tableData[rowIndex];
        const fields = ["status", "custom_duty_hours", "custom_overtime", "in_time", "out_time"];
        const isDirty = fields.some(f => String(current[f] || "") !== String(orig[f] || ""));
        if (isDirty) {
            dirtyRows.add(rowName);
        } else {
            dirtyRows.delete(rowName);
        }
    }

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
                        message: __("Sorry, overtime isn't allowed for this employee."),
                        indicator: "red"
                    });
                    const orig = originalData[row.name];
                    inputEl.val(orig ? orig.custom_overtime || 0 : row.custom_overtime || 0);
                    const i = parseInt(inputEl.data("i"));
                    tableData[i]["custom_overtime"] = orig ? orig.custom_overtime || 0 : row.custom_overtime || 0;
                    evaluateDirty(row.name, i);
                }
            }
        });
    }

    function getStatusClass(status) {
        if (status === "Present")  return "status-present";
        if (status === "Absent")   return "status-absent";
        if (status === "Half Day") return "status-half";
        if (status === "Rest")     return "status-rest";
        if (status === "Holiday")  return "status-holiday";
        return "";
    }

    $("#load-data").click(() => {
        const emp        = $("#employee").val();
        const department = department_field.get_value();
        const shift      = $("#shift").val();
        const from_date  = $("#from_date").val();
        const to_date    = $("#to_date").val();

        frappe.call({
            method: "attendance_correction.attendance_correction.page.attendance_correctio.attendance_correctio.get_attendance_records",
            args: { employee: emp, department: department, shift: shift, from_date: from_date, to_date: to_date },
            callback: function(r) {
                tableData = r.message || [];
                originalData = {};
                dirtyRows.clear();

                tableData.forEach(row => {
                    originalData[row.name] = {
                        status:            row.status            || "",
                        custom_duty_hours: row.custom_duty_hours || 0,
                        custom_overtime:   row.custom_overtime   || 0,
                        in_time:           row.in_time           || "",
                        out_time:          row.out_time          || ""
                    };
                });

                if (tableData.length === 0) {
                    $("#attendance-table").html("<p>No records found.</p>");
                } else {
                    renderTable(tableData);
                }
            }
        });
    });

    function renderTable(data) {
        let total_duty = 0;
        let total_overtime = 0;
        let total_present_days = 0;

        let html = `
            <table class="table table-bordered attendance-col-sized">
                <thead>
                    <tr>
                        <th style="width:90px;">Employee</th>
                        <th style="width:170px;">Name</th>
                        <th style="width:100px;">Date</th>
                        <th style="width:110px;">Status</th>
                        <th style="width:70px;">Duty Hrs</th>
                        <th style="width:70px;">OT Hrs</th>
                        <th style="width:150px;">In Time</th>
                        <th style="width:150px;">Out Time</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.forEach((row, i) => {
            total_duty         += parseFloat(row.custom_duty_hours) || 0;
            total_overtime     += parseFloat(row.custom_overtime)   || 0;

            if (["Present", "Holiday"].includes(row.status)) {
                total_present_days += 1;
            }

            const statusClass = getStatusClass(row.status);

            html += `
                <tr data-name="${row.name}">
                    <td>${row.employee}</td>
                    <td>${row.employee_name}</td>
                    <td>${row.attendance_date}</td>
                    <td>
                        <select data-i="${i}" data-field="status" data-name="${row.name}"
                            class="form-control status-select ${statusClass}">
                            <option value="Present"  ${row.status === "Present"  ? "selected" : ""}>Present</option>
                            <option value="Absent"   ${row.status === "Absent"   ? "selected" : ""}>Absent</option>
                            <option value="Half Day" ${row.status === "Half Day" ? "selected" : ""}>Half Day</option>
                            <option value="Rest"     ${row.status === "Rest"     ? "selected" : ""}>Rest</option>
                            <option value="Holiday"  ${row.status === "Holiday"  ? "selected" : ""}>Holiday</option>
                        </select>
                    </td>
                    <td>
                        <input type="number" data-i="${i}" data-field="custom_duty_hours" data-name="${row.name}"
                            value="${row.custom_duty_hours || 0}" class="form-control duty-ot-input">
                    </td>
                    <td>
                        <input type="number" data-i="${i}" data-field="custom_overtime" data-name="${row.name}"
                            value="${row.custom_overtime || 0}" class="form-control duty-ot-input">
                    </td>
                    <td>
                        <input type="text" data-i="${i}" data-field="in_time" data-name="${row.name}"
                            value="${row.in_time || ''}" class="form-control time-input">
                    </td>
                    <td>
                        <input type="text" data-i="${i}" data-field="out_time" data-name="${row.name}"
                            value="${row.out_time || ''}" class="form-control time-input">
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
                    <th style="text-align:right">Total Duty Hours:</th>
                    <th>${total_duty.toFixed(2)}</th>
                    <th style="text-align:right">Overtime Hours:</th>
                    <th>${total_overtime.toFixed(2)}</th>
                    <th></th>
                </tr>
            </tfoot>
            </table>
        `;

        $("#attendance-table").html(`<div class="attendance-table-wrapper">${html}</div>`);

        $("#attendance-table").on("change", "input, select", function() {
            const i       = parseInt($(this).data("i"));
            const field   = $(this).data("field");
            const rowName = $(this).data("name");
            const inputEl = $(this);
            const newVal  = inputEl.val();

            tableData[i][field] = newVal;

            if (field === "custom_overtime") {
                checkOvertimeAllowed(tableData[i], inputEl);
            }

            evaluateDirty(rowName, i);

            const $row = $(`tr[data-name="${rowName}"]`);
            if (dirtyRows.has(rowName)) {
                $row.addClass("row-dirty");
            } else {
                $row.removeClass("row-dirty");
            }

            let total_duty = 0;
            let total_overtime = 0;
            tableData.forEach(row => {
                total_duty     += parseFloat(row.custom_duty_hours) || 0;
                total_overtime += parseFloat(row.custom_overtime)   || 0;
            });
            $("tfoot tr th:contains('Total Duty Hours')").next().text(total_duty.toFixed(2));
            $("tfoot tr th:contains('Overtime Hours')").next().text(total_overtime.toFixed(2));

            if (field === "status") {
                inputEl
                    .removeClass("status-present status-absent status-half status-rest status-holiday")
                    .addClass(getStatusClass(newVal));
            }
        });
    }

    $("#save-changes").click(() => {
        if (tableData.length === 0) {
            frappe.msgprint("No data loaded.");
            return;
        }

        const changedRows = tableData.filter(row => dirtyRows.has(row.name));

        if (changedRows.length === 0) {
            frappe.msgprint("No changes detected.");
            return;
        }

        frappe.call({
            method: "attendance_correction.attendance_correction.page.attendance_correctio.attendance_correctio.update_attendance",
            args: { data: JSON.stringify(changedRows) },
            callback: function(r) {
                frappe.msgprint(r.message || "Attendance Updated Successfully");

                changedRows.forEach(row => {
                    originalData[row.name] = {
                        status:            row.status            || "",
                        custom_duty_hours: row.custom_duty_hours || 0,
                        custom_overtime:   row.custom_overtime   || 0,
                        in_time:           row.in_time           || "",
                        out_time:          row.out_time          || ""
                    };
                    dirtyRows.delete(row.name);
                    $(`tr[data-name="${row.name}"]`).removeClass("row-dirty");
                });
            }
        });
    });

    // Ctrl+S to save
    $(window).off("keydown.attendance_save").on("keydown.attendance_save", function(e) {
        if (e.ctrlKey && e.key === "s") {
            e.preventDefault();
            e.stopPropagation();
            $("#save-changes").click();
        }
    });
};

$(`<style>
    .page-head-content {
        position: relative !important;
    }

    .page-head-content .page-title {
        position: absolute !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: auto !important;
        max-width: 60% !important;
        text-align: center !important;
    }

    .page-head-content .page-title h3.title-text {
        text-align: center !important;
    }

    .attendance-table-wrapper .table {
        background-color: #ffffff !important;
        color: #000000 !important;
        table-layout: fixed;
        width: 100%;
    }

    .attendance-table-wrapper .table td,
    .attendance-table-wrapper .table th {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-color: #dee2e6 !important;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        text-align: center !important;
        vertical-align: middle !important;
    }

    .attendance-table-wrapper .table tbody tr:nth-child(even) td {
        background-color: #f8f9fa !important;
    }

    /* Dirty row highlight */
    .attendance-table-wrapper .table tbody tr.row-dirty td {
        background-color: #cce5ff !important;
        border-left: 3px solid #0056b3 !important;
    }

    /* Status select colors */
    .attendance-table-wrapper select.status-present {
        background-color: #d4edda !important;
        color: #155724 !important;
        font-weight: bold !important;
        -webkit-appearance: none;
        appearance: none;
        margin: 0 auto !important;
        display: block !important;
        text-align: center !important;
    }

    .attendance-table-wrapper select.status-absent {
        background-color: #f8d7da !important;
        color: #ea0920 !important;
        font-weight: bold !important;
        -webkit-appearance: none;
        appearance: none;
        margin: 0 auto !important;
        display: block !important;
        text-align: center !important;
    }

    .attendance-table-wrapper select.status-half {
        background-color: #fff1c1 !important;
        color: #9a6b00 !important;
        font-weight: bold !important;
        -webkit-appearance: none;
        appearance: none;
        margin: 0 auto !important;
        display: block !important;
        text-align: center !important;
    }

    .attendance-table-wrapper select.status-rest {
        background-color: #e0f0ff !important;
        color: #004b87 !important;
        font-weight: bold !important;
        -webkit-appearance: none;
        appearance: none;
        margin: 0 auto !important;
        display: block !important;
        text-align: center !important;
    }

    .attendance-table-wrapper select.status-holiday {
        background-color: #e8d9ff !important;
        color: #5b2c83 !important;
        font-weight: bold !important;
        -webkit-appearance: none;
        appearance: none;
        margin: 0 auto !important;
        display: block !important;
        text-align: center !important;
    }

    /* Narrow inputs for duty/overtime columns */
    .attendance-table-wrapper input.duty-ot-input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
        width: 60px !important;
        padding: 4px 5px !important;
        margin: 0 auto !important;
        display: block !important;
        text-align: center !important;
    }

    /* Wider inputs for in/out time columns */
    .attendance-table-wrapper input.time-input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
        width: 200px !important;
        padding: 4px 10px !important;
        margin: 0 auto !important;
        display: block !important;
        text-align: center !important;
    }

    .attendance-table-wrapper input.form-control {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #ccc !important;
    }

    .attendance-table-wrapper .table tfoot th {
        background-color: #2a4f8f !important;
        color: #ffffff !important;
    }
</style>`).appendTo("head");