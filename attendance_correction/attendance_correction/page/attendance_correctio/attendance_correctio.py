import frappe

@frappe.whitelist()
def get_attendance_records(employee=None, shift=None, date=None):
    """
    Fetch attendance records from Attendance Doctype
    Filters: employee, shift, date (optional)
    """
    filters = {}
    if employee:
        filters["employee"] = employee
    if shift:
        filters["shift"] = shift
    if date:
        filters["attendance_date"] = date

    records = frappe.get_all(
        "Attendance",
        filters=filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "attendance_date",
            "status",
            "shift",
            "working_hours",
            "in_time",
            "out_time"
        ]
    )
    return records

@frappe.whitelist()
def update_attendance(data):
    """
    Update Attendance records, including submitted records
    Cancel → Update → Submit
    """
    import json
    rows = json.loads(data)

    for row in rows:
        doc = frappe.get_doc("Attendance", row["name"])

        was_submitted = doc.docstatus == 1  # Check if previously submitted

        # Cancel if submitted
        if was_submitted:
            doc.cancel()

        # Update fields
        doc.status = row.get("status")
        doc.working_hours = row.get("working_hours")
        doc.in_time = row.get("in_time")
        doc.out_time = row.get("out_time")
        doc.save(ignore_permissions=True)

        # Re-submit if previously submitted
        if was_submitted:
            doc.submit()

    return "Attendance changes saved successfully!"


