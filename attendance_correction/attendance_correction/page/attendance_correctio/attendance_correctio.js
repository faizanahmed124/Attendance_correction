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
            <label>Shift</label>
            <input type="text" class="form-control" id="shift">
        </div>

        <div class="form-group">
            <label>Date</label>
            <input type="date" class="form-control" id="date">
        </div>

        <button class="btn btn-primary" id="load-data">Load Data</button>

        <hr>

        <div id="attendance-table"></div>

        <button class="btn btn-success" id="save-changes">Save Changes</button>
    `);

    let tableData = [];

    // Load Data Button
    $("#load-data").click(() => {
        const emp = $("#employee").val();
        const shift = $("#shift").val();
        const date = $("#date").val();

        frappe.call({
            method: "attendance_correction.attendance_correction.page.attendance_correctio.attendance_correctio.get_attendance_records",
            args: { employee: emp, shift: shift, date: date },
            callback: function(r) {
                tableData = r.message;
                if (tableData.length === 0) {
                    $("#attendance-table").html("<p>No records found.</p>");
                } else {
                    renderTable(tableData);
                }
            }
        });
    });

    function renderTable(data) {
        let html = `
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Employee</th>
                        <th>Name</th>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Working Hours</th>
                        <th>In Time</th>
                        <th>Out Time</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.forEach((row, i) => {
            html += `
                <tr>
                    <td>${row.employee}</td>
                    <td>${row.employee_name}</td>
                    <td>${row.attendance_date}</td>

                    <td>
                        <select data-i="${i}" data-field="status" class="form-control">
                            <option value="Present" ${row.status=="Present"?"selected":""}>Present</option>
                            <option value="Absent" ${row.status=="Absent"?"selected":""}>Absent</option>
                            <option value="Half Day" ${row.status=="Half Day"?"selected":""}>Half Day</option>
                        </select>
                    </td>

                    <td><input type="number" data-i="${i}" data-field="working_hours" value="${row.working_hours}" class="form-control"></td>
                    <td><input type="text" data-i="${i}" data-field="in_time" value="${row.in_time || ''}" class="form-control"></td>
                    <td><input type="text" data-i="${i}" data-field="out_time" value="${row.out_time || ''}" class="form-control"></td>
                </tr>
            `;
        });

        html += "</tbody></table>";
        $("#attendance-table").html(html);

        // Update tableData on input/select change
        $("input, select").on("change", function() {
            let i = $(this).data("i");
            let field = $(this).data("field");
            tableData[i][field] = $(this).val();
        });
    }

    // Save Changes Button
    $("#save-changes").click(() => {
        if(tableData.length === 0){
            frappe.msgprint("No data to update.");
            return;
        }

        frappe.call({
            method: "attendance_correction.attendance_correction.page.attendance_correctio.attendance_correctio.update_attendance",
            args: { data: JSON.stringify(tableData) },
            callback: function(r) {
                frappe.msgprint(r.message || "Attendance Updated Successfully");
                $("#load-data").click(); // Reload table after update
            }
        });
    });
};
