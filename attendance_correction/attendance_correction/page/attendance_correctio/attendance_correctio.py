import frappe
import json
from frappe.model.document import Document
from frappe.utils import flt, formatdate, format_datetime
from datetime import datetime

# -----------------------------
# Helper Function
# -----------------------------
def convert_to_mysql_datetime(dt_str):
    """
    Convert 'DD-MM-YYYY HH:mm' or 'DD-MM-YYYY' to MySQL DATETIME 'YYYY-MM-DD HH:MM:SS'
    If input is None or empty, return None
    """
    if not dt_str:
        return None
    try:
        if len(dt_str.strip()) > 10:
            dt_obj = datetime.strptime(dt_str, "%d-%m-%Y %H:%M")
        else:
            dt_obj = datetime.strptime(dt_str, "%d-%m-%Y")
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        frappe.log_error(f"Date conversion failed for '{dt_str}': {e}", "Attendance Date Conversion")
        return None

# -----------------------------
# Get Attendance Records
# -----------------------------
@frappe.whitelist()
def get_attendance_records(employee=None, department=None, shift=None, from_date=None, to_date=None):
    filters = {}

    if employee:
        filters["employee"] = employee
    if department:
        filters["department"] = department
    if shift:
        filters["shift"] = shift
    if from_date and to_date:
        filters["attendance_date"] = ["between", [from_date, to_date]]

    attendance_records = frappe.get_all(
        "Attendance",
        filters=filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "attendance_date",
            "status",
            "custom_duty_hours",
            "custom_overtime",
            "custom_less_duty_hour",   # ← LDH ADDED
            "in_time",
            "out_time",
            "docstatus"
        ],
        order_by="attendance_date ASC"
    )

    for row in attendance_records:
        if row.get("attendance_date"):
            row["attendance_date"] = formatdate(row["attendance_date"], "dd-MM-yyyy")
        if row.get("in_time"):
            row["in_time"] = format_datetime(row["in_time"], "dd-MM-yyyy HH:mm")
        if row.get("out_time"):
            row["out_time"] = format_datetime(row["out_time"], "dd-MM-yyyy HH:mm")

    return attendance_records

# -----------------------------
# Update Attendance Records (Optimized)
# -----------------------------
@frappe.whitelist()
def update_attendance(data):
    data = json.loads(data)
    if not data:
        return "No records to update"

    docnames = [row["name"] for row in data if row.get("name")]
    if not docnames:
        return "No valid records"

    # ✅ 1. Fetch ALL attendance records in ONE query
    placeholders = ", ".join(["%s"] * len(docnames))
    records = frappe.db.sql(f"""
        SELECT name, status, custom_duty_hours, custom_overtime, custom_less_duty_hour, in_time, out_time, employee
        FROM `tabAttendance`
        WHERE name IN ({placeholders})
    """, docnames, as_dict=True)

    existing = {rec["name"]: rec for rec in records}

    # ✅ 2. Fetch ALL employee overtime settings in ONE query
    employees = list(set(rec["employee"] for rec in records))
    emp_placeholders = ", ".join(["%s"] * len(employees))
    ot_records = frappe.db.sql(f"""
        SELECT name, custom_allow_overtime
        FROM `tabEmployee`
        WHERE name IN ({emp_placeholders})
    """, employees, as_dict=True)

    ot_map = {emp["name"]: emp["custom_allow_overtime"] for emp in ot_records}

    # ✅ 3. Unlink ALL checkins in ONE query
    frappe.db.sql(f"""
        UPDATE `tabEmployee Checkin`
        SET attendance = NULL
        WHERE attendance IN ({placeholders})
    """, docnames)

    # ✅ 4. Cancel ALL attendance in ONE query
    frappe.db.sql(f"""
        UPDATE `tabAttendance`
        SET docstatus = 2
        WHERE name IN ({placeholders})
    """, docnames)

    # ✅ 5. Update each row with direct SQL
    updated = 0
    logs_to_add = []

    for row in data:
        if not row.get("name"):
            continue

        docname = row["name"]
        old = existing.get(docname)
        if not old:
            continue

        employee = old["employee"]
        allow_overtime = ot_map.get(employee, 0)
        incoming_overtime = flt(row.get("custom_overtime") or 0)
        incoming_status = row.get("status")

        # Half Day: force 0.5 duty hours, zero overtime
        if incoming_status == "Half Day":
            final_duty_hours = 0.5
            final_overtime = 0
        else:
            final_duty_hours = flt(row.get("custom_duty_hours", 0))
            final_overtime = incoming_overtime if allow_overtime else flt(old["custom_overtime"] or 0)

        # ✅ LDH CALCULATE
        standard_hours = 8.0
        if 0 < final_duty_hours < standard_hours:
            final_less_duty = round(standard_hours - final_duty_hours, 2)
        else:
            final_less_duty = 0.0

        in_time_mysql  = convert_to_mysql_datetime(row.get("in_time"))
        out_time_mysql = convert_to_mysql_datetime(row.get("out_time"))

        # Direct SQL update
        frappe.db.sql("""
            UPDATE `tabAttendance`
            SET status = %s,
                custom_duty_hours = %s,
                custom_overtime = %s,
                custom_less_duty_hour = %s,
                in_time = %s,
                out_time = %s,
                docstatus = 1
            WHERE name = %s
        """, (incoming_status, final_duty_hours, final_overtime, final_less_duty, in_time_mysql, out_time_mysql, docname))

        # Build change logs
        logs = []
        if old["status"] != incoming_status:
            logs.append(f"Status changed from <b>{old['status']}</b> → <b>{incoming_status}</b>")
        if flt(old["custom_duty_hours"] or 0) != flt(final_duty_hours):
            logs.append(f"Duty Hours changed from <b>{flt(old['custom_duty_hours'] or 0)}</b> → <b>{final_duty_hours}</b>")
        if flt(old["custom_overtime"] or 0) != flt(final_overtime):
            logs.append(f"Overtime changed from <b>{flt(old['custom_overtime'] or 0)}</b> → <b>{final_overtime}</b>")
        if flt(old["custom_less_duty_hour"] or 0) != flt(final_less_duty):
            logs.append(f"Less Duty Hours changed from <b>{flt(old['custom_less_duty_hour'] or 0)}</b> → <b>{final_less_duty}</b>")
        if str(old["in_time"] or "") != str(in_time_mysql or ""):
            logs.append(f"In Time changed from <b>{old['in_time'] or '-'}</b> → <b>{in_time_mysql or '-'}</b>")
        if str(old["out_time"] or "") != str(out_time_mysql or ""):
            logs.append(f"Out Time changed from <b>{old['out_time'] or '-'}</b> → <b>{out_time_mysql or '-'}</b>")

        if logs:
            logs_to_add.append((docname, "<br>".join(logs)))

        updated += 1

    # ✅ 6. Single commit
    frappe.db.commit()

    # ✅ 7. Add comments after commit
    for docname, log_msg in logs_to_add:
        frappe.get_doc("Attendance", docname).add_comment("Info", log_msg)

    return f"{updated} Attendance record(s) corrected successfully"